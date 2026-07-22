from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from aios.api.schemas.common import ApiSchema, require_timezone
from aios.kernel.enums import ResearchSessionStatus
from aios.kernel.research import ResearchScope, ResearchSession


class ResearchSessionCreateRequest(ApiSchema):
    watchlist_item_id: str = Field(min_length=1, max_length=64)
    horizon_days: int
    as_of: datetime
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("as_of")
    @classmethod
    def validate_as_of(cls, value: datetime) -> datetime:
        return require_timezone(value)


class ResearchScopeResponse(ApiSchema):
    watchlist_item_id: str
    symbol: str
    market: str
    watchlist_note_snapshot: str | None
    horizon_days: int
    as_of: datetime
    valid_until: datetime


class ResearchSessionResponse(ApiSchema):
    research_session_id: str
    scope: ResearchScopeResponse
    status: ResearchSessionStatus
    evidence_ids: list[str]
    experiment_id: str | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


def research_scope_response(scope: ResearchScope) -> ResearchScopeResponse:
    return ResearchScopeResponse.model_validate(scope.model_dump())


def research_session_response(session: ResearchSession) -> ResearchSessionResponse:
    return ResearchSessionResponse(
        research_session_id=session.research_session_id,
        scope=research_scope_response(session.scope),
        status=session.status,
        evidence_ids=list(session.evidence_ids),
        experiment_id=session.experiment_id,
        cancelled_at=session.cancelled_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
