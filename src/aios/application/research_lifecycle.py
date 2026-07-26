from __future__ import annotations

from aios.adapters.storage import Storage
from aios.kernel.base import utc_now
from aios.kernel.enums import ResearchSessionStatus
from aios.kernel.errors import InvalidStateTransitionError
from aios.kernel.research import ResearchSession, ResearchTransitionEvent

_ACTIVE_TRANSITIONS: dict[ResearchSessionStatus, frozenset[ResearchSessionStatus]] = {
    ResearchSessionStatus.CREATED: frozenset(
        {
            ResearchSessionStatus.COLLECTING_EVIDENCE,
            ResearchSessionStatus.EVIDENCE_READY,
            ResearchSessionStatus.CANCELLED,
            ResearchSessionStatus.FAILED,
        }
    ),
    ResearchSessionStatus.COLLECTING_EVIDENCE: frozenset(
        {
            ResearchSessionStatus.EVIDENCE_READY,
            ResearchSessionStatus.HYPOTHESIS_READY,
            ResearchSessionStatus.CANCELLED,
            ResearchSessionStatus.FAILED,
        }
    ),
    ResearchSessionStatus.EVIDENCE_READY: frozenset(
        {
            ResearchSessionStatus.COLLECTING_EVIDENCE,
            ResearchSessionStatus.HYPOTHESIS_READY,
            ResearchSessionStatus.CANCELLED,
            ResearchSessionStatus.FAILED,
        }
    ),
    ResearchSessionStatus.HYPOTHESIS_READY: frozenset(
        {
            ResearchSessionStatus.SKILLS_RUNNING,
            ResearchSessionStatus.CANCELLED,
            ResearchSessionStatus.FAILED,
        }
    ),
    ResearchSessionStatus.SKILLS_RUNNING: frozenset(
        {
            ResearchSessionStatus.DISCUSSION_READY,
            ResearchSessionStatus.CANCELLED,
            ResearchSessionStatus.FAILED,
        }
    ),
    ResearchSessionStatus.DISCUSSION_READY: frozenset(
        {
            ResearchSessionStatus.RISK_REVIEW,
            ResearchSessionStatus.CANCELLED,
            ResearchSessionStatus.FAILED,
        }
    ),
    ResearchSessionStatus.RISK_REVIEW: frozenset(
        {
            ResearchSessionStatus.DECISION_READY,
            ResearchSessionStatus.CANCELLED,
            ResearchSessionStatus.FAILED,
        }
    ),
    ResearchSessionStatus.DECISION_READY: frozenset(
        {
            ResearchSessionStatus.CANCELLED,
            ResearchSessionStatus.FAILED,
        }
    ),
    ResearchSessionStatus.FAILED: frozenset({ResearchSessionStatus.FAILED}),
    ResearchSessionStatus.CANCELLED: frozenset(),
}
_DISABLED_FUTURE_STATES = frozenset(
    {
        ResearchSessionStatus.TRADE_PLAN_READY,
        ResearchSessionStatus.WAITING_EXECUTION,
        ResearchSessionStatus.WAITING_SETTLEMENT,
        ResearchSessionStatus.SETTLED,
        ResearchSessionStatus.REVIEWED,
        ResearchSessionStatus.LEARNING_PROPOSED,
        ResearchSessionStatus.COMPLETED,
    }
)


class ResearchLifecycleService:
    """Single entry point for ResearchSession status changes and transition logs."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def transition(
        self,
        session_or_id: ResearchSession | str,
        to_state: ResearchSessionStatus,
        *,
        reason: str,
        failure_stage: str | None = None,
        failure_error: str | None = None,
        increment_retry: bool = False,
        allow_future_state: bool = False,
    ) -> ResearchSession:
        session = self._session(session_or_id)
        normalized_reason = reason.strip()
        if not normalized_reason:
            msg = "transition reason must not be empty"
            raise ValueError(msg)
        if to_state in _DISABLED_FUTURE_STATES and not allow_future_state:
            msg = f"ResearchSession transition to {to_state.value} is not enabled yet"
            raise InvalidStateTransitionError(msg)
        if session.status is to_state and to_state is not ResearchSessionStatus.FAILED:
            return session
        self._validate_transition(session.status, to_state)

        now = utc_now()
        update: dict[str, object] = {
            "status": to_state,
            "updated_at": now,
            "transition_log": (
                *session.transition_log,
                ResearchTransitionEvent(
                    from_state=session.status,
                    to_state=to_state,
                    transition_time=now,
                    transition_reason=normalized_reason,
                ),
            ),
        }
        if to_state is ResearchSessionStatus.CANCELLED:
            update["cancelled_at"] = now
        if to_state is ResearchSessionStatus.FAILED:
            if not failure_stage or not failure_error:
                msg = "failed transition requires failure_stage and failure_error"
                raise ValueError(msg)
            update["failure_stage"] = failure_stage.strip()
            update["failure_error"] = failure_error.strip()
            update["retry_count"] = session.retry_count + (1 if increment_retry else 0)

        transitioned = session.model_copy(update=update)
        self._storage.replace(transitioned)
        return transitioned

    def _session(self, session_or_id: ResearchSession | str) -> ResearchSession:
        if isinstance(session_or_id, ResearchSession):
            return session_or_id
        return self._storage.get(ResearchSession, session_or_id)

    def _validate_transition(
        self,
        from_state: ResearchSessionStatus,
        to_state: ResearchSessionStatus,
    ) -> None:
        allowed = _ACTIVE_TRANSITIONS.get(from_state, frozenset())
        if to_state not in allowed:
            msg = f"invalid transition from {from_state.value} to {to_state.value}"
            raise InvalidStateTransitionError(msg)
