from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from tests.market_helpers import market_bar

from aios.application.market_evidence import MarketEvidenceImportService
from aios.kernel.evidence import Evidence
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


class FakeMarketDataAdapter:
    def __init__(self, bars: list[object]) -> None:
        self.bars = bars
        self.calls = 0

    def fetch_daily_bars(self, *args: object, **kwargs: object) -> list[object]:
        self.calls += 1
        return self.bars


def service_for(
    bars: list[object],
    storage: InMemoryStorage | None = None,
) -> tuple[MarketEvidenceImportService, InMemoryStorage]:
    actual_storage = storage or InMemoryStorage()
    service = MarketEvidenceImportService(
        adapter=FakeMarketDataAdapter(bars),
        lifecycle=DecisionLifecycleService(actual_storage),
    )
    return service, actual_storage


def test_import_creates_evidence() -> None:
    service, storage = service_for([market_bar()])

    result = service.import_daily_bars(
        "000001.SZ",
        date(2026, 7, 1),
        date(2026, 7, 1),
        "qfq",
    )

    assert result.requested == 1
    assert result.created == 1
    assert result.existing == 0
    assert storage.get(Evidence, result.evidence_ids[0]).metadata["market_bar"]


def test_repeated_import_is_idempotent() -> None:
    service, storage = service_for([market_bar()])

    first = service.import_daily_bars(
        "000001.SZ", date(2026, 7, 1), date(2026, 7, 1), "qfq"
    )
    second = service.import_daily_bars(
        "000001.SZ", date(2026, 7, 1), date(2026, 7, 1), "qfq"
    )

    assert first.evidence_ids == second.evidence_ids
    assert second.created == 0
    assert second.existing == 1
    assert len(storage.list(Evidence)) == 1


def test_revised_data_creates_new_evidence() -> None:
    service, storage = service_for([market_bar(close=Decimal("10.50"))])
    first = service.import_daily_bars(
        "000001.SZ", date(2026, 7, 1), date(2026, 7, 1), "qfq"
    )

    revised_service, _storage = service_for(
        [market_bar(close=Decimal("10.51"))],
        storage,
    )
    revised = revised_service.import_daily_bars(
        "000001.SZ",
        date(2026, 7, 1),
        date(2026, 7, 1),
        "qfq",
    )

    assert revised.evidence_ids != first.evidence_ids
    assert revised.created == 1
    assert len(storage.list(Evidence)) == 2
    assert (
        storage.get(Evidence, revised.evidence_ids[0]).metadata["possible_revision"]
        is True
    )


def test_preview_does_not_write_storage() -> None:
    service, storage = service_for([market_bar()])

    preview = service.preview_daily_bars(
        "000001.SZ", date(2026, 7, 1), date(2026, 7, 1), "qfq"
    )

    assert len(preview) == 1
    assert storage.list(Evidence) == []


def test_available_at_must_not_precede_published_at() -> None:
    before_close = datetime(2026, 7, 1, 6, 0, tzinfo=UTC)
    service, _storage = service_for([market_bar(fetched_at=before_close)])

    with pytest.raises(ValueError, match="not yet available"):
        service.import_daily_bars(
            "000001.SZ", date(2026, 7, 1), date(2026, 7, 1), "qfq"
        )


def test_future_market_bar_is_not_imported() -> None:
    service, _storage = service_for([market_bar(trade_date=date(2999, 1, 1))])

    with pytest.raises(ValueError, match="future"):
        service.import_daily_bars(
            "000001.SZ", date(2999, 1, 1), date(2999, 1, 1), "qfq"
        )
