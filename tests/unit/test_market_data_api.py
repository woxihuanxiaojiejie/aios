from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from tests.market_helpers import market_bar

from aios.adapters.market_data import Adjustment
from aios.api.app import create_app
from aios.integrations.akshare.errors import (
    EmptyMarketDataError,
    UnsupportedMarketSymbolError,
    UpstreamMarketDataError,
)
from aios.storage.memory import InMemoryStorage


class FakeMarketDataAdapter:
    def __init__(
        self, bars: list[object] | None = None, error: Exception | None = None
    ) -> None:
        self.bars = bars or [market_bar()]
        self.error = error

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[object]:
        if self.error is not None:
            raise self.error
        return self.bars


def client(adapter: FakeMarketDataAdapter | None = None) -> TestClient:
    return TestClient(
        create_app(
            storage=InMemoryStorage(),
            market_data_adapter=adapter or FakeMarketDataAdapter(),
        )
    )


def payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "symbol": "000001.SZ",
        "start_date": "2026-07-01",
        "end_date": "2026-07-01",
        "adjustment": "qfq",
    }
    data.update(overrides)
    return data


def test_market_data_import_success() -> None:
    api = client()

    response = api.post(
        "/api/v1/market-data/akshare/daily-bars/import",
        json=payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["symbol"] == "000001.SZ"
    assert body["requested"] == 1
    assert body["created"] == 1
    assert body["existing"] == 0
    assert body["evidence_ids"][0].startswith("ev_")


def test_market_data_preview_success_does_not_create_evidence() -> None:
    api = client()

    response = api.post(
        "/api/v1/market-data/akshare/daily-bars/preview",
        json=payload(),
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["close"] == "10.50"
    assert api.get("/api/v1/evidence").json()["count"] == 0


def test_market_data_api_rejects_bad_dates() -> None:
    response = client().post(
        "/api/v1/market-data/akshare/daily-bars/import",
        json=payload(start_date="2026-07-02", end_date="2026-07-01"),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "market_data_date_range_error"


def test_market_data_api_unsupported_market() -> None:
    response = client(
        FakeMarketDataAdapter(error=UnsupportedMarketSymbolError("unsupported symbol"))
    ).post(
        "/api/v1/market-data/akshare/daily-bars/import", json=payload(symbol="00700.HK")
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "market_data_unsupported_symbol"


def test_market_data_api_empty_data() -> None:
    response = client(
        FakeMarketDataAdapter(error=EmptyMarketDataError("no data"))
    ).post(
        "/api/v1/market-data/akshare/daily-bars/import",
        json=payload(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "market_data_empty"


def test_market_data_api_upstream_failure_is_sanitized() -> None:
    response = client(
        FakeMarketDataAdapter(
            error=UpstreamMarketDataError("internal socket traceback")
        )
    ).post("/api/v1/market-data/akshare/daily-bars/import", json=payload())

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "market_data_upstream_error"
    assert "traceback" not in str(body).lower()
