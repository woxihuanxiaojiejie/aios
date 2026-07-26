from __future__ import annotations

import re
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.brain002 import TokenUsage
from aios.kernel.enums import Action, DecisionDirection, SkillExecutionStatus

FORBIDDEN_OPERATIONAL_RE = re.compile(
    r"\b(call|invoke|run|execute)\b.*\bskill\b|"
    r"\b(browse|internet|fetch|download|scrape|news|行情|联网)\b|"
    r"\b(weight|weights)\b.*\b(update|modify|change|write|persist)\b|"
    r"\b(learning|settlement|broker|order|auto[_ -]?trade|"
    r"position sizing|stop[_ -]?loss|take[_ -]?profit)\b",
    re.IGNORECASE,
)


class ReferencedReason(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(min_length=1)
    skill_ids: tuple[str, ...] = ()
    discussion_refs: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    @field_validator("skill_ids", "discussion_refs", "evidence_ids", mode="before")
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("skill_ids", "discussion_refs", "evidence_ids")
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator("reason")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _decision_text(value)

    @model_validator(mode="after")
    def validate_traceability(self) -> ReferencedReason:
        if not (self.skill_ids or self.discussion_refs or self.evidence_ids):
            msg = "reasoning must reference skill_ids, discussion_refs, or evidence_ids"
            raise ValueError(msg)
        return self


class RiskNote(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    risk: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)
    invalid_condition: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()

    @field_validator("evidence_ids", mode="before")
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("evidence_ids")
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator("risk", "uncertainty", "invalid_condition")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _decision_text(value)


class DirectionRejection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    direction: DecisionDirection
    reason: str = Field(min_length=1)
    skill_ids: tuple[str, ...] = ()
    discussion_refs: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    @field_validator("skill_ids", "discussion_refs", "evidence_ids", mode="before")
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("skill_ids", "discussion_refs", "evidence_ids")
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator("reason")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _decision_text(value)

    @model_validator(mode="after")
    def validate_traceability(self) -> DirectionRejection:
        if not (self.skill_ids or self.discussion_refs or self.evidence_ids):
            msg = "rejected direction reason must be traceable"
            raise ValueError(msg)
        return self


class DecisionResultPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    direction: DecisionDirection
    confidence: float = Field(ge=0, le=1)
    action: Action
    reasoning: tuple[ReferencedReason, ...] = Field(min_length=1)
    supporting_skills: tuple[str, ...] = ()
    opposing_skills: tuple[str, ...] = ()
    discussion_refs: tuple[str, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    risks: tuple[RiskNote, ...] = Field(min_length=1)
    rejected_directions: tuple[DirectionRejection, ...] = Field(min_length=1)
    decision_summary: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def normalize_common_llm_shapes(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        rejected_directions = value.get("rejected_directions")
        if isinstance(rejected_directions, dict):
            value = dict(value)
            value["rejected_directions"] = [
                {
                    "direction": direction,
                    "reason": reason,
                    "skill_ids": [],
                    "discussion_refs": ["discussion_summary"],
                    "evidence_ids": [],
                }
                for direction, reason in rejected_directions.items()
            ]
        return value

    @field_validator(
        "reasoning",
        "risks",
        "rejected_directions",
        "supporting_skills",
        "opposing_skills",
        "discussion_refs",
        "evidence_refs",
        mode="before",
    )
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator(
        "supporting_skills",
        "opposing_skills",
        "discussion_refs",
        "evidence_refs",
    )
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        if isinstance(value, str):
            return float(value.strip())
        return value

    @field_validator("decision_summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return _decision_text(value)

    @model_validator(mode="after")
    def validate_decision_contract(self) -> DecisionResultPayload:
        rejected = {item.direction for item in self.rejected_directions}
        if self.direction in rejected:
            msg = "rejected_directions must not include selected direction"
            raise ValueError(msg)
        if not (self.supporting_skills or self.opposing_skills):
            msg = "DecisionResultPayload requires supporting or opposing skills"
            raise ValueError(msg)
        return self


class DecisionExecution(KernelModel):
    id_field: ClassVar[str] = "decision_execution_id"

    decision_execution_id: str = Field(default_factory=lambda: new_id("de_"))
    task_id: str = Field(min_length=1)
    discussion_result_id: str = Field(min_length=1)
    skill_result_ids: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    started_at: datetime
    finished_at: datetime | None = None
    status: SkillExecutionStatus = SkillExecutionStatus.PENDING
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int | None = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
    raw_response: str | None = None
    parsed_response: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "decision_execution_id",
        "task_id",
        "discussion_result_id",
        "provider",
        "model",
        "prompt_version",
        "raw_response",
        "error",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _decision_text(value, allow_operational_terms=True)

    @field_validator("skill_result_ids", "evidence_ids", mode="before")
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("skill_result_ids", "evidence_ids")
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator("started_at", "finished_at", "created_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_finished_at(self) -> DecisionExecution:
        if self.finished_at is not None and self.finished_at < self.started_at:
            msg = "finished_at must not be earlier than started_at"
            raise ValueError(msg)
        return self


class DecisionResult(KernelModel):
    id_field: ClassVar[str] = "decision_result_id"

    decision_result_id: str = Field(default_factory=lambda: new_id("ds_"))
    decision_execution_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    discussion_result_id: str = Field(min_length=1)
    skill_result_ids: tuple[str, ...] = Field(min_length=1)
    direction: DecisionDirection
    confidence: float = Field(ge=0, le=1)
    action: Action
    reasoning: tuple[ReferencedReason, ...] = Field(min_length=1)
    supporting_skills: tuple[str, ...] = ()
    opposing_skills: tuple[str, ...] = ()
    discussion_refs: tuple[str, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    risks: tuple[RiskNote, ...] = Field(min_length=1)
    rejected_directions: tuple[DirectionRejection, ...] = Field(min_length=1)
    decision_summary: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "skill_result_ids",
        "reasoning",
        "risks",
        "rejected_directions",
        "supporting_skills",
        "opposing_skills",
        "discussion_refs",
        "evidence_refs",
        mode="before",
    )
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator(
        "skill_result_ids",
        "supporting_skills",
        "opposing_skills",
        "discussion_refs",
        "evidence_refs",
    )
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator(
        "decision_result_id",
        "decision_execution_id",
        "task_id",
        "discussion_result_id",
        "decision_summary",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return _decision_text(value)

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_payload_contract(self) -> DecisionResult:
        DecisionResultPayload.model_validate(
            {
                "direction": self.direction,
                "confidence": self.confidence,
                "action": self.action,
                "reasoning": self.reasoning,
                "supporting_skills": self.supporting_skills,
                "opposing_skills": self.opposing_skills,
                "discussion_refs": self.discussion_refs,
                "evidence_refs": self.evidence_refs,
                "risks": self.risks,
                "rejected_directions": self.rejected_directions,
                "decision_summary": self.decision_summary,
            }
        )
        return self


def _tuple_input(value: Any) -> Any:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return value


def _unique_text_tuple(value: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(item.strip() for item in value)
    if any(not item for item in normalized):
        msg = "values must not be empty"
        raise ValueError(msg)
    if len(normalized) != len(set(normalized)):
        msg = "duplicate values are not allowed"
        raise ValueError(msg)
    return normalized


def _decision_text(value: str, *, allow_operational_terms: bool = False) -> str:
    normalized = value.strip()
    if not normalized:
        msg = "value must not be empty"
        raise ValueError(msg)
    if not allow_operational_terms and FORBIDDEN_OPERATIONAL_RE.search(normalized):
        msg = "decision output must not contain prohibited operational actions"
        raise ValueError(msg)
    return normalized
