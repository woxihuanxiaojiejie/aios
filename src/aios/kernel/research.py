from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import ResearchSessionStatus

ALLOWED_RESEARCH_HORIZONS = frozenset({1, 3, 7})


class ResearchScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    watchlist_item_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1, max_length=64)
    market: str = Field(min_length=1, max_length=64)
    watchlist_note_snapshot: str | None = Field(default=None, max_length=500)
    horizon_days: int
    as_of: datetime
    valid_until: datetime

    @field_validator("symbol", "market")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            msg = "value must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("watchlist_note_snapshot")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("horizon_days")
    @classmethod
    def validate_horizon(cls, value: int) -> int:
        if value not in ALLOWED_RESEARCH_HORIZONS:
            msg = "horizon_days must be one of 1, 3, or 7"
            raise ValueError(msg)
        return value

    @field_validator("as_of", "valid_until")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_window(self) -> ResearchScope:
        if self.valid_until <= self.as_of:
            msg = "valid_until must be later than as_of"
            raise ValueError(msg)
        return self


class ResearchTransitionEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    from_state: ResearchSessionStatus
    to_state: ResearchSessionStatus
    transition_time: datetime
    transition_reason: str = Field(min_length=1)

    @field_validator("transition_time")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator("transition_reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "transition_reason must not be empty"
            raise ValueError(msg)
        return normalized


class ResearchSession(KernelModel):
    id_field: ClassVar[str] = "research_session_id"

    research_session_id: str = Field(default_factory=lambda: new_id("rs_"))
    scope: ResearchScope
    status: ResearchSessionStatus = ResearchSessionStatus.CREATED
    evidence_ids: tuple[str, ...] = ()
    experiment_id: str | None = None
    cancelled_at: datetime | None = None
    failure_stage: str | None = None
    failure_error: str | None = None
    retry_count: int = Field(default=0, ge=0)
    transition_log: tuple[ResearchTransitionEvent, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "duplicate Evidence IDs are not allowed"
            raise ValueError(msg)
        return value

    @field_validator("cancelled_at", "created_at", "updated_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_status(self) -> ResearchSession:
        if (
            self.status is ResearchSessionStatus.EVIDENCE_READY
            and not self.evidence_ids
        ):
            msg = "evidence_ready ResearchSession must have Evidence IDs"
            raise ValueError(msg)
        if self.status is ResearchSessionStatus.FAILED:
            if not self.failure_stage or not self.failure_error:
                msg = "failed ResearchSession must have failure_stage and failure_error"
                raise ValueError(msg)
        elif self.failure_stage is not None or self.failure_error is not None:
            msg = "failure details are only allowed for failed ResearchSession"
            raise ValueError(msg)
        if self.status is ResearchSessionStatus.CANCELLED:
            if self.cancelled_at is None:
                msg = "cancelled ResearchSession must have cancelled_at"
                raise ValueError(msg)
        elif self.cancelled_at is not None:
            msg = "cancelled_at is only allowed for cancelled ResearchSession"
            raise ValueError(msg)
        if self.updated_at < self.created_at:
            msg = "updated_at must not be earlier than created_at"
            raise ValueError(msg)
        return self
