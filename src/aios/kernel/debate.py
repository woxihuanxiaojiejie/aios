from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import Field, field_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import (
    DebateStance,
    DebateStatus,
    ResearchConclusion,
    RiskVerdict,
)


class DebateRecord(KernelModel):
    id_field: ClassVar[str] = "debate_id"

    debate_id: str = Field(default_factory=lambda: new_id("db_"))
    research_session_id: str = Field(min_length=1)
    report_ids: tuple[str, ...] = Field(min_length=1)
    hypothesis_ids: tuple[str, ...] = Field(min_length=1)
    status: DebateStatus = DebateStatus.OPEN
    final_decision_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("report_ids", "hypothesis_ids")
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


class DebateStatement(KernelModel):
    id_field: ClassVar[str] = "statement_id"

    statement_id: str = Field(default_factory=lambda: new_id("ds_"))
    debate_id: str = Field(min_length=1)
    agent_report_id: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    stance: DebateStance
    reasoning: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    confidence_before: float = Field(ge=0, le=1)
    confidence_after: float = Field(ge=0, le=1)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("reasoning")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "reasoning must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("evidence_ids")
    @classmethod
    def validate_unique_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "duplicate Evidence IDs are not allowed"
            raise ValueError(msg)
        return value

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class DecisionProposal(KernelModel):
    id_field: ClassVar[str] = "proposal_id"

    proposal_id: str = Field(default_factory=lambda: new_id("dp_"))
    debate_id: str = Field(min_length=1)
    conclusion: ResearchConclusion
    confidence: float = Field(ge=0, le=1)
    thesis: str = Field(min_length=1)
    supporting_hypothesis_ids: tuple[str, ...] = ()
    rejected_hypothesis_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    risk_notes: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("thesis")
    @classmethod
    def normalize_thesis(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "thesis must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator(
        "supporting_hypothesis_ids",
        "rejected_hypothesis_ids",
        "evidence_ids",
        "risk_notes",
    )
    @classmethod
    def validate_unique_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "duplicate values are not allowed"
            raise ValueError(msg)
        return value

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class RiskReview(KernelModel):
    id_field: ClassVar[str] = "risk_review_id"

    risk_review_id: str = Field(default_factory=lambda: new_id("rr_"))
    proposal_id: str = Field(min_length=1)
    verdict: RiskVerdict
    final_conclusion: ResearchConclusion
    final_confidence: float = Field(ge=0, le=1)
    reasons: tuple[str, ...] = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(reason.strip() for reason in value if reason.strip())
        if not normalized:
            msg = "RiskReview reasons must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class DecisionAssemblyRecord(KernelModel):
    id_field: ClassVar[str] = "assembly_id"

    assembly_id: str = Field(default_factory=lambda: new_id("da_"))
    research_session_id: str = Field(min_length=1)
    debate_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    risk_review_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    conclusion: ResearchConclusion
    report_ids: tuple[str, ...]
    hypothesis_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)
