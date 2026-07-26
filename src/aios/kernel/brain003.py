from __future__ import annotations

import re
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.brain002 import TokenUsage
from aios.kernel.enums import SkillExecutionStatus

DECISION_LANGUAGE_RE = re.compile(
    r"\b(buy|sell|hold|no[_ -]?trade|position|sizing|stop[_ -]?loss|"
    r"take[_ -]?profit|order|entry|exit)\b",
    re.IGNORECASE,
)
WEIGHT_MUTATION_RE = re.compile(
    r"\b(update|modify|change|write|persist|learning|settlement)\b.*\bweight\b|"
    r"\bweight\b.*\b(update|modify|change|write|persist|learning|settlement)\b",
    re.IGNORECASE,
)


class ConflictReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_ids: tuple[str, ...] = Field(min_length=2)
    conflict_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()

    @field_validator("skill_ids", "evidence_ids", mode="before")
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("skill_ids", "evidence_ids")
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator("conflict_type", "description", "reason")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _review_text(value)


class EvidenceReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str = Field(min_length=1)
    sufficiency: str = Field(min_length=1)
    challenge: str = Field(min_length=1)
    referenced_evidence_ids: tuple[str, ...] = ()
    missing_evidence_categories: tuple[str, ...] = ()

    @field_validator(
        "referenced_evidence_ids",
        "missing_evidence_categories",
        mode="before",
    )
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("referenced_evidence_ids", "missing_evidence_categories")
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator("skill_id", "sufficiency", "challenge")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _review_text(value)


class CounterArgument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str = Field(min_length=1)
    argument: str = Field(min_length=1)
    failure_mode: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()

    @field_validator("evidence_ids", mode="before")
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("evidence_ids")
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator("skill_id", "argument", "failure_mode")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _review_text(value)


class RevisionSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str = Field(min_length=1)
    original_confidence: float = Field(ge=0, le=1)
    suggested_confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1)

    @field_validator("original_confidence", "suggested_confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        if isinstance(value, str):
            return float(value.strip())
        return value

    @field_validator("skill_id", "reason")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _review_text(value)


class DiscussionResultPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    conflicts: tuple[ConflictReview, ...] = ()
    evidence_reviews: tuple[EvidenceReview, ...] = ()
    counter_arguments: tuple[CounterArgument, ...] = ()
    revision_suggestions: tuple[RevisionSuggestion, ...] = ()
    discussion_summary: str = Field(min_length=1)
    discussion_confidence: float = Field(ge=0, le=1)

    @field_validator(
        "conflicts",
        "evidence_reviews",
        "counter_arguments",
        "revision_suggestions",
        mode="before",
    )
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("discussion_confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        if isinstance(value, str):
            return float(value.strip())
        return value

    @field_validator("discussion_summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return _review_text(value)


class DiscussionExecution(KernelModel):
    id_field: ClassVar[str] = "discussion_execution_id"

    discussion_execution_id: str = Field(default_factory=lambda: new_id("dx_"))
    task_id: str = Field(min_length=1)
    skill_result_ids: tuple[str, ...] = Field(min_length=1)
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
        "discussion_execution_id",
        "task_id",
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
        normalized = value.strip()
        if not normalized:
            msg = "value must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("skill_result_ids", mode="before")
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("skill_result_ids")
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
    def validate_finished_at(self) -> DiscussionExecution:
        if self.finished_at is not None and self.finished_at < self.started_at:
            msg = "finished_at must not be earlier than started_at"
            raise ValueError(msg)
        return self


class DiscussionResult(KernelModel):
    id_field: ClassVar[str] = "discussion_result_id"

    discussion_result_id: str = Field(default_factory=lambda: new_id("dr_"))
    discussion_execution_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    skill_result_ids: tuple[str, ...] = Field(min_length=1)
    conflicts: tuple[ConflictReview, ...] = ()
    evidence_reviews: tuple[EvidenceReview, ...] = ()
    counter_arguments: tuple[CounterArgument, ...] = ()
    revision_suggestions: tuple[RevisionSuggestion, ...] = ()
    discussion_summary: str = Field(min_length=1)
    discussion_confidence: float = Field(ge=0, le=1)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("skill_result_ids", mode="before")
    @classmethod
    def normalize_tuple_input(cls, value: Any) -> Any:
        return _tuple_input(value)

    @field_validator("skill_result_ids")
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text_tuple(value)

    @field_validator(
        "discussion_result_id",
        "discussion_execution_id",
        "task_id",
        "discussion_summary",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return _review_text(value)

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)


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


def _review_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        msg = "value must not be empty"
        raise ValueError(msg)
    if DECISION_LANGUAGE_RE.search(normalized):
        msg = "discussion output must not contain decision language"
        raise ValueError(msg)
    if WEIGHT_MUTATION_RE.search(normalized):
        msg = "discussion output must not request weight mutation"
        raise ValueError(msg)
    return normalized
