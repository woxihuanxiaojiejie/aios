from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from aios.adapters.market_data import Adjustment, MarketBar
from aios.api.app import create_app
from aios.storage.memory import InMemoryStorage
from aios.vibe_trading.output_mapper import VibeTradingRawResult

AS_OF = datetime.now(UTC).replace(
    hour=8,
    minute=0,
    second=0,
    microsecond=0,
) - timedelta(days=1)


def test_research_run_api_creates_gets_and_resumes_completed_run() -> None:
    api = TestClient(
        create_app(
            storage=InMemoryStorage(),
            market_data_adapter=FakeMarketDataAdapter(),
            vibe_trading_adapter=FakeVibeTradingAdapter(),
        )
    )
    watchlist = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN"},
    ).json()

    created = api.post(
        "/api/v1/research/runs",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": AS_OF.isoformat(),
            "workflow": "investment_committee",
            "provider": "fake",
            "model": "fake-model",
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "completed"
    assert body["current_stage"] == "completed"
    fetched = api.get(f"/api/v1/research/runs/{body['run_id']}")
    resumed = api.post(f"/api/v1/research/runs/{body['run_id']}/resume")
    replay = api.post(
        "/api/v1/research/runs",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": AS_OF.isoformat(),
            "workflow": "investment_committee",
            "provider": "fake",
            "model": "fake-model",
        },
    )

    assert fetched.json()["run_id"] == body["run_id"]
    assert resumed.json()["run_id"] == body["run_id"]
    assert replay.json()["run_id"] == body["run_id"]


class FakeMarketDataAdapter:
    def fetch_daily_bars(
        self,
        symbol: str,
        start_date,
        end_date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        return [
            MarketBar(
                symbol=symbol,
                market="CN_A",
                trade_date=end_date,
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("95"),
                close=Decimal("108"),
                volume=Decimal("10000"),
                amount=Decimal("1080000"),
                adjustment=adjustment,
                source="fixture",
                fetched_at=AS_OF,
            )
        ]


class FakeVibeTradingAdapter:
    def analyze(self, **kwargs) -> VibeTradingRawResult:
        return VibeTradingRawResult(
            symbol=kwargs["symbol"],
            market=kwargs["market"],
            as_of=kwargs["as_of"],
            vibe_run_id="vibe_fixture_1",
            workflow=kwargs["workflow"],
            raw_output_reference="fixture://vibe/vibe_fixture_1.json",
            analyst_reports={"market": "技术面趋势向上。"},
            investment_debate={"judge_decision": "支持谨慎买入。"},
            trader_plan="结构化计划建议 buy。",
            risk_assessment={"risk_judge_decision": "风险可接受。"},
            final_decision={"signal": "buy", "confidence": 0.6},
            model_provider=kwargs["provider"],
            model_name=kwargs["model"],
            started_at=AS_OF,
            completed_at=AS_OF,
        )
