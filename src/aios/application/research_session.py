from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import ValidationError

from aios.adapters.storage import Storage
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.kernel.base import ensure_utc
from aios.kernel.enums import ResearchSessionStatus, WatchlistStatus
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
    MissingEntityError,
    ReferenceIntegrityError,
)
from aios.kernel.evidence import Evidence
from aios.kernel.research import (
    ALLOWED_RESEARCH_HORIZONS,
    ResearchScope,
    ResearchSession,
)
from aios.kernel.watchlist import WatchlistItem


class ResearchSessionService:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def create_session(
        self,
        *,
        watchlist_item_id: str,
        horizon_days: int,
        as_of: datetime,
        evidence_ids: list[str] | tuple[str, ...] = (),
    ) -> ResearchSession:
        if horizon_days not in ALLOWED_RESEARCH_HORIZONS:
            msg = "horizon_days must be one of 1, 3, or 7"
            raise ValueError(msg)
        normalized_as_of = ensure_utc(as_of)
        watchlist_item = self._storage.get(WatchlistItem, watchlist_item_id)
        if watchlist_item.status is not WatchlistStatus.ACTIVE:
            msg = f"WatchlistItem {watchlist_item_id} is not active"
            raise InvalidStateTransitionError(msg)
        existing = self._storage.find_active_research_session(
            watchlist_item_id,
            normalized_as_of,
            horizon_days,
        )
        if existing is not None:
            msg = (
                "active ResearchSession already exists for "
                f"{watchlist_item_id} at {normalized_as_of.isoformat()} "
                f"with horizon {horizon_days}"
            )
            raise DuplicateEntityError(msg)
        scope = ResearchScope(
            watchlist_item_id=watchlist_item.watchlist_item_id,
            symbol=watchlist_item.symbol,
            market=watchlist_item.market,
            watchlist_note_snapshot=watchlist_item.note,
            horizon_days=horizon_days,
            as_of=normalized_as_of,
            valid_until=normalized_as_of + timedelta(days=horizon_days),
        )
        unique_evidence_ids = tuple(evidence_ids)
        self._validate_evidence_ids(unique_evidence_ids, scope)
        session = ResearchSession(
            scope=scope,
            evidence_ids=unique_evidence_ids,
            experiment_id=None,
        )
        try:
            self._storage.save(session)
        except ValidationError:
            raise
        if unique_evidence_ids:
            return ResearchLifecycleService(self._storage).transition(
                session,
                ResearchSessionStatus.EVIDENCE_READY,
                reason="initial evidence attached",
            )
        return session

    def get_session(self, session_id: str) -> ResearchSession:
        return self._storage.get(ResearchSession, session_id)

    def list_sessions(
        self,
        *,
        watchlist_item_id: str | None = None,
        symbol: str | None = None,
        market: str | None = None,
        status: ResearchSessionStatus | None = None,
        horizon_days: int | None = None,
    ) -> list[ResearchSession]:
        normalized_symbol = symbol.strip().upper() if symbol is not None else None
        normalized_market = market.strip().upper() if market is not None else None
        return self._storage.list_research_sessions(
            watchlist_item_id=watchlist_item_id,
            symbol=normalized_symbol,
            market=normalized_market,
            status=status,
            horizon_days=horizon_days,
        )

    def cancel_session(self, session_id: str) -> ResearchSession:
        try:
            session = self._storage.get(ResearchSession, session_id)
        except MissingEntityError:
            raise
        if session.status is ResearchSessionStatus.CANCELLED:
            msg = f"ResearchSession {session_id} is already cancelled"
            raise InvalidStateTransitionError(msg)
        return ResearchLifecycleService(self._storage).transition(
            session,
            ResearchSessionStatus.CANCELLED,
            reason="manual cancellation",
        )

    def _validate_evidence_ids(
        self,
        evidence_ids: tuple[str, ...],
        scope: ResearchScope,
    ) -> None:
        if len(evidence_ids) != len(set(evidence_ids)):
            msg = "duplicate Evidence IDs are not allowed"
            raise ValueError(msg)
        for evidence_id in evidence_ids:
            try:
                evidence = self._storage.get(Evidence, evidence_id)
            except MissingEntityError as exc:
                msg = f"Evidence {evidence_id} does not exist"
                raise ReferenceIntegrityError(msg) from exc
            if scope.symbol not in {
                symbol.strip().upper() for symbol in evidence.symbols
            }:
                msg = (
                    f"Evidence {evidence_id} does not match "
                    f"{scope.market}:{scope.symbol}"
                )
                raise ReferenceIntegrityError(msg)
            if (
                evidence.published_at > scope.as_of
                or evidence.available_at > scope.as_of
            ):
                msg = f"Evidence {evidence_id} is later than as_of"
                raise ReferenceIntegrityError(msg)
