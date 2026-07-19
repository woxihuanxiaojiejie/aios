from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from tests.market_helpers import market_bar

from aios.adapters.market_data import Adjustment
from aios.api.app import create_app
from aios.kernel.evidence import Evidence
from aios.storage.postgres import PostgresStorage


class FakeMarketDataAdapter:
    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[object]:
        return [market_bar()]


def test_postgres_market_data_import_is_persistent_and_idempotent(
    migrated_postgres_url: str,
) -> None:
    api = TestClient(
        create_app(
            storage=PostgresStorage(migrated_postgres_url),
            market_data_adapter=FakeMarketDataAdapter(),
        )
    )
    payload = {
        "symbol": "000001.SZ",
        "start_date": "2026-07-01",
        "end_date": "2026-07-01",
        "adjustment": "qfq",
    }

    first = api.post("/api/v1/market-data/akshare/daily-bars/import", json=payload)
    assert first.status_code == 201
    first_body = first.json()
    evidence_id = first_body["evidence_ids"][0]

    fresh_storage = PostgresStorage(migrated_postgres_url)
    assert (
        fresh_storage.get(Evidence, evidence_id).metadata["market_bar"]["close"]
        == "10.50"
    )

    second = api.post("/api/v1/market-data/akshare/daily-bars/import", json=payload)
    assert second.status_code == 201
    assert second.json()["created"] == 0
    assert second.json()["existing"] == 1
    assert second.json()["evidence_ids"] == [evidence_id]
