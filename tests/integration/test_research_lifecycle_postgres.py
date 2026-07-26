from __future__ import annotations

from tests.factories import fixed_now

from aios.application.research_lifecycle import ResearchLifecycleService
from aios.application.research_session import ResearchSessionService
from aios.application.watchlist import WatchlistService
from aios.kernel.enums import ResearchSessionStatus
from aios.kernel.research import ResearchSession
from aios.storage.postgres.storage import PostgresStorage


def test_postgres_round_trips_research_lifecycle_state_and_context(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    item = WatchlistService(storage).add_item(symbol="600519", market="CN")
    session = ResearchSessionService(storage).create_session(
        watchlist_item_id=item.watchlist_item_id,
        horizon_days=3,
        as_of=fixed_now(),
    )

    failed = ResearchLifecycleService(storage).transition(
        session.research_session_id,
        ResearchSessionStatus.FAILED,
        reason="evidence collection failed",
        failure_stage="collecting_evidence",
        failure_error="provider unavailable",
        increment_retry=True,
    )

    persisted = storage.get(ResearchSession, session.research_session_id)
    assert persisted == failed
    assert persisted.failure_stage == "collecting_evidence"
    assert persisted.failure_error == "provider unavailable"
    assert persisted.retry_count == 1
    assert persisted.transition_log[-1].transition_reason == (
        "evidence collection failed"
    )
