from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from tests.market_helpers import market_bar

from aios.adapters.market_data import Adjustment, MarketBar
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
    ) -> list[MarketBar]:
        return [
            market_bar(
                source="baostock.query_history_k_data_plus",
                adjustment=adjustment,
            )
        ]


def test_postgres_baostock_import_is_persistent_and_idempotent(
    migrated_postgres_url: str,
) -> None:
    api = TestClient(
        create_app(
            storage=PostgresStorage(migrated_postgres_url),
            baostock_market_data_adapter=FakeMarketDataAdapter(),
        )
    )
    payload = {
        "symbol": "000001.SZ",
        "start_date": "2026-07-01",
        "end_date": "2026-07-01",
        "adjustment": "none",
    }

    first = api.post("/api/v1/market-data/baostock/daily-bars/import", json=payload)
    assert first.status_code == 201
    evidence_id = first.json()["evidence_ids"][0]

    fresh_storage = PostgresStorage(migrated_postgres_url)
    evidence = fresh_storage.get(Evidence, evidence_id)
    assert evidence.source == "baostock.query_history_k_data_plus"
    assert evidence.metadata["provider"] == "baostock"

    second = api.post("/api/v1/market-data/baostock/daily-bars/import", json=payload)
    assert second.status_code == 201
    assert second.json()["created"] == 0
    assert second.json()["existing"] == 1
    assert second.json()["evidence_ids"] == [evidence_id]
