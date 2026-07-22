from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from tests.factories import fixed_now, make_evidence, make_watchlist_item

from aios.application.research_session import ResearchSessionService
from aios.application.watchlist import WatchlistService
from aios.kernel.enums import ResearchSessionStatus, WatchlistStatus
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
    MissingEntityError,
    ReferenceIntegrityError,
)
from aios.kernel.evidence import Evidence
from aios.kernel.research import ResearchScope, ResearchSession
from aios.storage.memory import InMemoryStorage


def test_research_session_model_validates_scope_and_status() -> None:
    as_of = datetime(2026, 7, 22, 6, 0, tzinfo=UTC)
    scope = ResearchScope(
        watchlist_item_id="wl_1",
        symbol=" 600519 ",
        market=" cn ",
        watchlist_note_snapshot=" note ",
        horizon_days=3,
        as_of=as_of,
        valid_until=as_of + timedelta(days=3),
    )

    session = ResearchSession(scope=scope, evidence_ids=())

    assert session.research_session_id.startswith("rs_")
    assert session.scope.symbol == "600519"
    assert session.scope.market == "CN"
    assert session.scope.watchlist_note_snapshot == "note"
    assert session.status is ResearchSessionStatus.CREATED
    assert session.evidence_ids == ()
    assert session.cancelled_at is None


def test_research_scope_rejects_invalid_horizon_and_naive_datetimes() -> None:
    as_of = datetime(2026, 7, 22, 6, 0, tzinfo=UTC)

    with pytest.raises(ValidationError):
        ResearchScope(
            watchlist_item_id="wl_1",
            symbol="600519",
            market="CN",
            horizon_days=5,
            as_of=as_of,
            valid_until=as_of + timedelta(days=5),
        )

    with pytest.raises(ValidationError):
        ResearchScope(
            watchlist_item_id="wl_1",
            symbol="600519",
            market="CN",
            horizon_days=3,
            as_of=datetime(2026, 7, 22, 6, 0),
            valid_until=as_of + timedelta(days=3),
        )


def test_research_session_status_semantics_and_unique_evidence() -> None:
    as_of = datetime(2026, 7, 22, 6, 0, tzinfo=UTC)
    scope = ResearchScope(
        watchlist_item_id="wl_1",
        symbol="600519",
        market="CN",
        horizon_days=3,
        as_of=as_of,
        valid_until=as_of + timedelta(days=3),
    )

    ready = ResearchSession(scope=scope, evidence_ids=("ev_1",))
    assert ready.status is ResearchSessionStatus.EVIDENCE_READY

    with pytest.raises(ValidationError, match="duplicate Evidence"):
        ResearchSession(scope=scope, evidence_ids=("ev_1", "ev_1"))

    with pytest.raises(ValidationError, match="cancelled_at"):
        ResearchSession(
            scope=scope,
            status=ResearchSessionStatus.CANCELLED,
            evidence_ids=("ev_1",),
        )


def test_research_session_service_creates_from_active_watchlist() -> None:
    storage = InMemoryStorage()
    watchlist = WatchlistService(storage)
    item = watchlist.add_item(symbol=" 600519 ", market=" cn ", note="  first ")
    as_of = fixed_now() + timedelta(hours=1)

    session = ResearchSessionService(storage).create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=3,
        as_of=as_of,
    )

    assert session.scope.watchlist_item_id == item.watchlist_item_id
    assert session.scope.symbol == "600519"
    assert session.scope.market == "CN"
    assert session.scope.watchlist_note_snapshot == "first"
    assert session.scope.valid_until == as_of + timedelta(days=3)
    assert session.status is ResearchSessionStatus.CREATED
    assert session.evidence_ids == ()
    assert session.experiment_id is None


def test_research_session_service_rejects_archived_watchlist() -> None:
    storage = InMemoryStorage()
    item = make_watchlist_item(status=WatchlistStatus.ARCHIVED)
    storage.save(item)

    with pytest.raises(InvalidStateTransitionError):
        ResearchSessionService(storage).create_session(
            watchlist_item_id=item.watchlist_item_id,
            horizon_days=3,
            as_of=fixed_now(),
        )


def test_research_session_service_validates_evidence() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(symbol="600519", market="CN")
    as_of = fixed_now() + timedelta(hours=1)
    evidence = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000101",
        summary="maotai report",
    ).model_copy(update={"symbols": ("600519",)})
    storage.save(evidence)

    created = ResearchSessionService(storage).create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=1,
        as_of=as_of,
        evidence_ids=[evidence.evidence_id],
    )
    assert created.status is ResearchSessionStatus.EVIDENCE_READY
    assert created.evidence_ids == (evidence.evidence_id,)

    with pytest.raises(ReferenceIntegrityError):
        ResearchSessionService(storage).create_session(
            watchlist_item_id=item.watchlist_item_id,
            horizon_days=3,
            as_of=as_of + timedelta(minutes=1),
            evidence_ids=["ev_missing"],
        )


def test_research_session_service_rejects_mismatched_or_future_evidence() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(symbol="600519", market="CN")
    as_of = fixed_now() + timedelta(hours=1)
    mismatch = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000102",
    )
    future = Evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000103",
        evidence_type="filing",
        source="company-report",
        symbols=("600519",),
        published_at=as_of + timedelta(minutes=1),
        available_at=as_of + timedelta(minutes=2),
        summary="future",
        reliability=0.8,
        content_hash="future",
    )
    storage.save(mismatch)
    storage.save(future)

    service = ResearchSessionService(storage)
    with pytest.raises(ReferenceIntegrityError, match="does not match"):
        service.create_session(
            watchlist_item_id=item.watchlist_item_id,
            horizon_days=3,
            as_of=as_of,
            evidence_ids=[mismatch.evidence_id],
        )

    with pytest.raises(ReferenceIntegrityError, match="later than as_of"):
        service.create_session(
            watchlist_item_id=item.watchlist_item_id,
            horizon_days=7,
            as_of=as_of,
            evidence_ids=[future.evidence_id],
        )


def test_research_session_duplicate_cancel_and_snapshot_rules() -> None:
    storage = InMemoryStorage()
    watchlist = WatchlistService(storage)
    item = watchlist.add_item(symbol="600519", market="CN", note="original")
    as_of = fixed_now() + timedelta(hours=1)
    service = ResearchSessionService(storage)

    first = service.create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=3,
        as_of=as_of,
    )
    watchlist.update_note(item.watchlist_item_id, note="changed")
    assert service.get_session(
        first.research_session_id
    ).scope.watchlist_note_snapshot == ("original")
    with pytest.raises(DuplicateEntityError):
        service.create_session(
            watchlist_item_id=item.watchlist_item_id,
            horizon_days=3,
            as_of=as_of,
        )

    watchlist.archive_item(item.watchlist_item_id)
    assert service.get_session(
        first.research_session_id
    ).scope.watchlist_note_snapshot == ("original")

    cancelled = service.cancel_session(first.research_session_id)
    assert cancelled.status is ResearchSessionStatus.CANCELLED
    assert cancelled.cancelled_at is not None
    assert service.get_session(first.research_session_id) == cancelled

    with pytest.raises(InvalidStateTransitionError):
        service.cancel_session(first.research_session_id)

    restored_item = watchlist.restore_item(item.watchlist_item_id)
    second = service.create_session(
        watchlist_item_id=restored_item.watchlist_item_id,
        horizon_days=3,
        as_of=as_of,
    )
    assert second.research_session_id != first.research_session_id


def test_research_session_storage_filters() -> None:
    storage = InMemoryStorage()
    active = make_watchlist_item()
    hk = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000002",
        symbol="0700",
        market="HK",
    )
    storage.save(active)
    storage.save(hk)
    service = ResearchSessionService(storage)

    first = service.create_session(
        watchlist_item_id=active.watchlist_item_id,
        horizon_days=1,
        as_of=fixed_now(),
    )
    second = service.create_session(
        watchlist_item_id=hk.watchlist_item_id,
        horizon_days=7,
        as_of=fixed_now(),
    )
    cancelled = service.cancel_session(first.research_session_id)

    assert storage.get(ResearchSession, first.research_session_id) == cancelled
    assert (
        storage.find_active_research_session(
            active.watchlist_item_id,
            fixed_now(),
            1,
        )
        is None
    )
    assert (
        storage.find_active_research_session(
            hk.watchlist_item_id,
            fixed_now(),
            7,
        )
        == second
    )
    assert storage.list_research_sessions(status=ResearchSessionStatus.CANCELLED) == [
        cancelled
    ]
    assert storage.list_research_sessions(market="HK") == [second]
    assert storage.list_research_sessions(symbol="0700") == [second]
    assert storage.list_research_sessions(horizon_days=7) == [second]


def test_research_session_missing_get_and_update_fail() -> None:
    service = ResearchSessionService(InMemoryStorage())

    with pytest.raises(MissingEntityError):
        service.get_session("rs_missing")

    with pytest.raises(MissingEntityError):
        service.cancel_session("rs_missing")
