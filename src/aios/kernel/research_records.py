from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import AgentReportStatus, AgentRole, HypothesisStatus


class AgentReport(KernelModel):
    id_field: ClassVar[str] = "report_id"

    report_id: str = Field(default_factory=lambda: new_id("ar_"))
    research_session_id: str = Field(min_length=1)
    role: AgentRole
    summary: str = Field(min_length=1)
    stance: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: tuple[str, ...] = ()
    source: str = Field(min_length=1)
    raw_reference: str | None = Field(default=None, max_length=500)
    status: AgentReportStatus = AgentReportStatus.ACTIVE
    archived_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("summary", "stance", "source")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "value must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("raw_reference")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "duplicate Evidence IDs are not allowed"
            raise ValueError(msg)
        return value

    @field_validator("archived_at", "created_at", "updated_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_archive_state(self) -> AgentReport:
        if self.status is AgentReportStatus.ACTIVE and self.archived_at is not None:
            msg = "active AgentReport must not have archived_at"
            raise ValueError(msg)
        if self.status is AgentReportStatus.ARCHIVED and self.archived_at is None:
            msg = "archived AgentReport must have archived_at"
            raise ValueError(msg)
        if self.updated_at < self.created_at:
            msg = "updated_at must not be earlier than created_at"
            raise ValueError(msg)
        return self


class Hypothesis(KernelModel):
    id_field: ClassVar[str] = "hypothesis_id"

    hypothesis_id: str = Field(default_factory=lambda: new_id("hp_"))
    research_session_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    horizon_days: int
    confidence: float = Field(ge=0, le=1)
    supporting_report_ids: tuple[str, ...] = Field(min_length=1)
    supporting_evidence_ids: tuple[str, ...] = ()
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("statement", "rationale", "direction")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "value must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("supporting_report_ids", "supporting_evidence_ids")
    @classmethod
    def validate_unique_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "duplicate IDs are not allowed"
            raise ValueError(msg)
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_creation_state(self) -> Hypothesis:
        if self.updated_at < self.created_at:
            msg = "updated_at must not be earlier than created_at"
            raise ValueError(msg)
        return self
