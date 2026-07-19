from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from tests.market_helpers import FakeBaoStockClient, market_bar

from aios.adapters.market_data import Adjustment, MarketBar
from aios.api.app import create_app
from aios.integrations.baostock.adapter import BaoStockMarketDataAdapter
from aios.integrations.baostock.errors import (
    EmptyMarketDataError,
    UpstreamMarketDataError,
)
from aios.storage.memory import InMemoryStorage


class FakeMarketDataAdapter:
    def __init__(
        self,
        bars: list[MarketBar] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.bars = bars or [
            market_bar(
                source="baostock.query_history_k_data_plus",
                adjustment=Adjustment.NONE,
            )
        ]
        self.error = error

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        if self.error is not None:
            raise self.error
        return self.bars


def client(adapter: FakeMarketDataAdapter | None = None) -> TestClient:
    return TestClient(
        create_app(
            storage=InMemoryStorage(),
            baostock_market_data_adapter=adapter or FakeMarketDataAdapter(),
        )
    )


def payload(**overrides: str) -> dict[str, str]:
    body = {
        "symbol": "000001.SZ",
        "start_date": "2026-07-01",
        "end_date": "2026-07-01",
        "adjustment": "none",
    }
    body.update(overrides)
    return body


def test_baostock_preview_succeeds() -> None:
    response = client().post(
        "/api/v1/market-data/baostock/daily-bars/preview",
        json=payload(),
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["items"][0]["source"] == "baostock.query_history_k_data_plus"


def test_baostock_import_is_idempotent() -> None:
    api = client()

    first = api.post("/api/v1/market-data/baostock/daily-bars/import", json=payload())
    second = api.post("/api/v1/market-data/baostock/daily-bars/import", json=payload())

    assert first.status_code == 201
    assert first.json()["created"] == 1
    assert second.status_code == 201
    assert second.json()["created"] == 0
    assert second.json()["existing"] == 1
    assert second.json()["evidence_ids"] == first.json()["evidence_ids"]


def test_baostock_import_creates_revision_for_changed_same_day_data() -> None:
    api = client(
        FakeMarketDataAdapter(
            [
                market_bar(
                    source="baostock.query_history_k_data_plus",
                    adjustment=Adjustment.NONE,
                )
            ]
        )
    )
    assert (
        api.post(
            "/api/v1/market-data/baostock/daily-bars/import", json=payload()
        ).status_code
        == 201
    )

    api.app.state.baostock_market_data_adapter = FakeMarketDataAdapter(
        [
            market_bar(
                source="baostock.query_history_k_data_plus",
                adjustment=Adjustment.NONE,
                close=Decimal("10.60"),
            )
        ]
    )
    second = api.post("/api/v1/market-data/baostock/daily-bars/import", json=payload())

    assert second.status_code == 201
    assert second.json()["created"] == 1


def test_baostock_unsupported_code_returns_400() -> None:
    api = TestClient(
        create_app(
            storage=InMemoryStorage(),
            baostock_market_data_adapter=BaoStockMarketDataAdapter(
                FakeBaoStockClient()
            ),
        )
    )

    response = api.post(
        "/api/v1/market-data/baostock/daily-bars/import",
        json=payload(symbol="00700.HK"),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "market_data_unsupported_symbol"


def test_baostock_empty_data_returns_404() -> None:
    response = client(FakeMarketDataAdapter(error=EmptyMarketDataError("empty"))).post(
        "/api/v1/market-data/baostock/daily-bars/import",
        json=payload(),
    )

    assert response.status_code == 404


def test_baostock_upstream_error_returns_502_without_leak() -> None:
    response = client(
        FakeMarketDataAdapter(error=UpstreamMarketDataError("socket secret details"))
    ).post("/api/v1/market-data/baostock/daily-bars/import", json=payload())

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "market_data_upstream_error"
    assert "socket secret details" not in body["error"]["message"]
