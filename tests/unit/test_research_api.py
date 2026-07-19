from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from pydantic import BaseModel

from aios.adapters.llm import LLMStructuredResult
from aios.adapters.market_data import Adjustment, MarketBar
from aios.api.app import create_app
from aios.integrations.litellm.errors import LLMAuthenticationError
from aios.integrations.litellm.schemas import DecisionDraft
from aios.storage.memory import InMemoryStorage


@dataclass
class DeterministicMarketDataAdapter:
    bars: list[MarketBar]

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        if symbol == "AAPL":
            msg = "Only .SZ and .SH A-share symbols are supported: AAPL"
            from aios.adapters.market_errors import UnsupportedMarketSymbolError

            raise UnsupportedMarketSymbolError(msg)
        return [
            bar
            for bar in self.bars
            if bar.symbol == symbol
            and start_date <= bar.trade_date <= end_date
            and bar.adjustment is adjustment
        ]


class DeterministicLLMAdapter:
    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        evidence_id = json.loads(user_prompt)["evidence"][0]["evidence_id"]
        return LLMStructuredResult(
            parsed=DecisionDraft(
                action="buy",
                confidence=0.7,
                expected_return=0.02,
                max_expected_loss=0.05,
                horizon="1d",
                reasoning_summary="real evidence supports a bounded long decision",
                supporting_evidence_ids=(evidence_id,),
                risk_factors=("market reversal",),
                invalidation_conditions=("close below entry",),
            ),
            provider="deepseek",
            model=model,
            request_id="req_real_metadata",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=1,
            raw_finish_reason="stop",
        )


class AuthFailingLLMAdapter:
    def generate_structured(self, **_kwargs: object) -> LLMStructuredResult:
        raise LLMAuthenticationError("LLM authentication failed")


def bar(trade_date: date, close: str) -> MarketBar:
    value = Decimal(close)
    return MarketBar(
        symbol="000001.SZ",
        market="CN_A",
        trade_date=trade_date,
        open=value,
        high=value + Decimal("0.10"),
        low=value - Decimal("0.10"),
        close=value,
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        adjustment=Adjustment.NONE,
        source="deterministic-market",
        fetched_at=datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
    )


def client(llm_adapter: object | None = None) -> TestClient:
    bars = [
        bar(date(2026, 7, 18), "10.00"),
        bar(date(2026, 7, 19), "10.30"),
        bar(date(2026, 7, 20), "10.60"),
    ]
    return TestClient(
        create_app(
            storage=InMemoryStorage(),
            baostock_market_data_adapter=DeterministicMarketDataAdapter(bars),
            llm_adapter=llm_adapter or DeterministicLLMAdapter(),
        )
    )


def test_research_market_preview_and_evidence_import() -> None:
    api = client()

    preview = api.get("/api/v1/research/market", params={"symbol": "000001.SZ"})

    assert preview.status_code == 200
    body = preview.json()
    assert body["symbol"] == "000001.SZ"
    assert body["market"] == "CN_A"
    assert body["source"] == "deterministic-market"
    assert body["latest"]["close"] == "10.30"
    assert body["change"] == "0.30"
    assert body["change_percent"] == "0.03"

    evidence = api.post("/api/v1/research/evidence", json={"symbol": "000001.SZ"})

    assert evidence.status_code == 201
    assert evidence.json()["created"] == 2
    assert evidence.json()["latest_evidence"]["evidence_id"].startswith("ev_")


def test_research_decision_settlement_review_and_history() -> None:
    api = client()
    imported = api.post("/api/v1/research/evidence", json={"symbol": "000001.SZ"})
    evidence_ids = imported.json()["evidence_ids"]
    experiment = api.post(
        "/api/v1/research/experiments",
        json={
            "symbol": "000001.SZ",
            "evidence_ids": evidence_ids,
            "model": "deepseek/deepseek-chat",
        },
    )
    decision = api.post(
        "/api/v1/research/decisions",
        json={
            "experiment_id": experiment.json()["experiment_id"],
            "symbol": "000001.SZ",
            "horizon": "1d",
        },
    )

    assert experiment.status_code == 201
    assert decision.status_code == 201
    assert decision.json()["generation"]["provider"] == "deepseek"
    assert decision.json()["generation"]["request_id"] == "req_real_metadata"

    settlement = api.post(
        f"/api/v1/research/settlements/{decision.json()['decision']['decision_id']}",
        json={"as_of": "2026-07-21T00:00:00+00:00"},
    )

    assert settlement.status_code == 201
    assert Decimal(settlement.json()["outcome"]["realized_return"]) > 0
    assert settlement.json()["evaluation"]["directional_result"] == "correct"
    assert settlement.json()["review"]["outcome"] == "profit"

    history = api.get("/api/v1/research/history", params={"symbol": "000001.SZ"})

    assert history.status_code == 200
    assert history.json()["latest_review"]["outcome"] == "profit"
    assert history.json()["rows"][0]["review_outcome"] == "profit"


def test_research_unsupported_symbol_returns_real_error() -> None:
    response = client().get("/api/v1/research/market", params={"symbol": "AAPL"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "market_data_unsupported_symbol"


def test_research_decision_surfaces_deepseek_authentication_error() -> None:
    api = client(llm_adapter=AuthFailingLLMAdapter())
    imported = api.post("/api/v1/research/evidence", json={"symbol": "000001.SZ"})
    experiment = api.post(
        "/api/v1/research/experiments",
        json={
            "symbol": "000001.SZ",
            "evidence_ids": imported.json()["evidence_ids"],
            "model": "deepseek/deepseek-chat",
        },
    )

    response = api.post(
        "/api/v1/research/decisions",
        json={
            "experiment_id": experiment.json()["experiment_id"],
            "symbol": "000001.SZ",
            "horizon": "1d",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_unavailable"


def test_research_settlement_not_ready_returns_state_error() -> None:
    api = client()
    imported = api.post("/api/v1/research/evidence", json={"symbol": "000001.SZ"})
    experiment = api.post(
        "/api/v1/research/experiments",
        json={
            "symbol": "000001.SZ",
            "evidence_ids": imported.json()["evidence_ids"],
            "model": "deepseek/deepseek-chat",
        },
    )
    decision = api.post(
        "/api/v1/research/decisions",
        json={
            "experiment_id": experiment.json()["experiment_id"],
            "symbol": "000001.SZ",
            "horizon": "1d",
        },
    )

    response = api.post(
        f"/api/v1/research/settlements/{decision.json()['decision']['decision_id']}",
        json={"as_of": "2026-07-01T10:00:00+00:00"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state_transition"
