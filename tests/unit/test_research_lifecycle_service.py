from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from tests.factories import fixed_now, make_evidence

from aios.application.research_lifecycle import ResearchLifecycleService
from aios.application.research_session import ResearchSessionService
from aios.application.watchlist import WatchlistService
from aios.kernel.enums import ResearchSessionStatus
from aios.kernel.errors import InvalidStateTransitionError
from aios.kernel.research import ResearchSession
from aios.storage.memory import InMemoryStorage


def test_lifecycle_transitions_record_context_and_are_idempotent() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(symbol="600519", market="CN")
    session = ResearchSessionService(storage).create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=3,
        as_of=fixed_now(),
    )
    service = ResearchLifecycleService(storage)

    collecting = service.transition(
        session.research_session_id,
        ResearchSessionStatus.COLLECTING_EVIDENCE,
        reason="manual evidence collection",
    )
    replay = service.transition(
        session.research_session_id,
        ResearchSessionStatus.COLLECTING_EVIDENCE,
        reason="manual evidence collection",
    )

    assert replay == collecting
    assert collecting.status is ResearchSessionStatus.COLLECTING_EVIDENCE
    assert len(collecting.transition_log) == 1
    event = collecting.transition_log[0]
    assert event.from_state is ResearchSessionStatus.CREATED
    assert event.to_state is ResearchSessionStatus.COLLECTING_EVIDENCE
    assert event.transition_reason == "manual evidence collection"
    assert event.transition_time.tzinfo is not None


def test_lifecycle_rejects_invalid_and_disabled_future_transitions() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(symbol="600519", market="CN")
    session = ResearchSessionService(storage).create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=3,
        as_of=fixed_now(),
    )
    service = ResearchLifecycleService(storage)

    with pytest.raises(InvalidStateTransitionError, match="invalid transition"):
        service.transition(
            session.research_session_id,
            ResearchSessionStatus.SKILLS_RUNNING,
            reason="skip evidence and hypotheses",
        )

    with pytest.raises(InvalidStateTransitionError, match="not enabled"):
        service.transition(
            session.research_session_id,
            ResearchSessionStatus.TRADE_PLAN_READY,
            reason="trade plan is Milestone 6",
        )


def test_lifecycle_failed_state_records_stage_error_and_retry_count() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(symbol="600519", market="CN")
    session = ResearchSessionService(storage).create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=3,
        as_of=fixed_now(),
    )

    failed = ResearchLifecycleService(storage).transition(
        session.research_session_id,
        ResearchSessionStatus.FAILED,
        reason="skill execution failed",
        failure_stage="skills_running",
        failure_error="LLM timeout",
        increment_retry=True,
    )

    assert failed.status is ResearchSessionStatus.FAILED
    assert failed.failure_stage == "skills_running"
    assert failed.failure_error == "LLM timeout"
    assert failed.retry_count == 1
    assert failed.transition_log[-1].from_state is ResearchSessionStatus.CREATED
    assert failed.transition_log[-1].to_state is ResearchSessionStatus.FAILED


def test_research_session_service_uses_lifecycle_for_ready_and_cancel() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(symbol="600519", market="CN")
    evidence = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000003001",
    ).model_copy(update={"symbols": ("600519",)})
    storage.save(evidence)

    session = ResearchSessionService(storage).create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=3,
        as_of=fixed_now() + timedelta(hours=1),
        evidence_ids=[evidence.evidence_id],
    )
    cancelled = ResearchSessionService(storage).cancel_session(
        session.research_session_id
    )

    assert session.status is ResearchSessionStatus.EVIDENCE_READY
    assert session.transition_log[-1].from_state is ResearchSessionStatus.CREATED
    assert session.transition_log[-1].to_state is ResearchSessionStatus.EVIDENCE_READY
    assert cancelled.status is ResearchSessionStatus.CANCELLED
    assert cancelled.cancelled_at is not None
    assert cancelled.transition_log[-1].to_state is ResearchSessionStatus.CANCELLED


def test_only_research_lifecycle_service_updates_research_session_status() -> None:
    forbidden = '"status": ResearchSessionStatus'
    allowed = Path("src/aios/application/research_lifecycle.py")
    offenders: list[str] = []
    for path in Path("src/aios").rglob("*.py"):
        if path == allowed:
            continue
        if forbidden in path.read_text():
            offenders.append(str(path))

    assert offenders == []


def test_research_session_model_no_longer_auto_transitions_with_evidence() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(symbol="600519", market="CN")
    session = ResearchSessionService(storage).create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=3,
        as_of=fixed_now(),
    )
    raw = ResearchSession(
        scope=session.scope,
        evidence_ids=("ev_1",),
    )

    assert raw.status is ResearchSessionStatus.CREATED
