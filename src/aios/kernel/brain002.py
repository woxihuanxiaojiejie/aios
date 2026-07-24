from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import SkillDirection, SkillExecutionStatus, SkillStatus


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> TokenUsage:
        if (
            self.prompt_tokens is not None
            and self.completion_tokens is not None
            and self.total_tokens is not None
            and self.total_tokens < self.prompt_tokens + self.completion_tokens
        ):
            msg = "total_tokens must not be smaller than prompt plus completion tokens"
            raise ValueError(msg)
        return self


class SkillDefinition(KernelModel):
    id_field: ClassVar[str] = "skill_id"

    skill_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    supported_markets: tuple[str, ...] = Field(min_length=1)
    supported_asset_types: tuple[str, ...] = Field(min_length=1)
    supported_horizons: tuple[str, ...] = Field(min_length=1)
    required_evidence_types: tuple[str, ...] = Field(min_length=1)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    trigger_conditions: dict[str, Any] = Field(default_factory=dict)
    dependencies: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    status: SkillStatus = SkillStatus.ENABLED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("skill_id", "name", "version", "description")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "value must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator(
        "supported_markets",
        "supported_asset_types",
        "supported_horizons",
        "required_evidence_types",
        "dependencies",
        "conflicts",
    )
    @classmethod
    def normalize_unique_text_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            msg = "values must not be empty"
            raise ValueError(msg)
        if len(normalized) != len(set(normalized)):
            msg = "duplicate values are not allowed"
            raise ValueError(msg)
        return normalized

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_timestamps_and_relationships(self) -> SkillDefinition:
        if self.updated_at < self.created_at:
            msg = "updated_at must not be earlier than created_at"
            raise ValueError(msg)
        if self.skill_id in self.dependencies:
            msg = "SkillDefinition cannot depend on itself"
            raise ValueError(msg)
        if self.skill_id in self.conflicts:
            msg = "SkillDefinition cannot conflict with itself"
            raise ValueError(msg)
        return self


class AnalysisTask(KernelModel):
    id_field: ClassVar[str] = "task_id"

    task_id: str = Field(default_factory=lambda: new_id("at_"))
    symbol: str = Field(min_length=1)
    market: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)
    horizon: str = Field(min_length=1)
    as_of: datetime
    evidence_ids: tuple[str, ...] = ()
    user_constraints: dict[str, Any] = Field(default_factory=dict)
    requested_skill_ids: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("task_id", "symbol", "market", "asset_type", "horizon")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "value must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("evidence_ids", "requested_skill_ids")
    @classmethod
    def validate_unique_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            msg = "IDs must not be empty"
            raise ValueError(msg)
        if len(normalized) != len(set(normalized)):
            msg = "duplicate IDs are not allowed"
            raise ValueError(msg)
        return normalized

    @field_validator("as_of", "created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class SkillExecution(KernelModel):
    id_field: ClassVar[str] = "execution_id"

    execution_id: str = Field(default_factory=lambda: new_id("sx_"))
    task_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    skill_version: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime | None = None
    status: SkillExecutionStatus = SkillExecutionStatus.PENDING
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int | None = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
    error: str | None = None

    @field_validator(
        "execution_id",
        "task_id",
        "skill_id",
        "skill_version",
        "provider",
        "model",
        "prompt_version",
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

    @field_validator("started_at", "finished_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_finished_at(self) -> SkillExecution:
        if self.finished_at is not None and self.finished_at < self.started_at:
            msg = "finished_at must not be earlier than started_at"
            raise ValueError(msg)
        return self


class SkillResult(KernelModel):
    id_field: ClassVar[str] = "result_id"

    result_id: str = Field(default_factory=lambda: new_id("sr_"))
    execution_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    skill_version: str = Field(min_length=1)
    conclusion: str = Field(min_length=1)
    direction: SkillDirection
    confidence: float = Field(ge=0, le=1)
    supporting_evidence_ids: tuple[str, ...] = ()
    contradicting_evidence_ids: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = Field(min_length=1)
    invalid_conditions: tuple[str, ...] = Field(min_length=1)
    missing_information: tuple[str, ...] = Field(min_length=1)
    reasoning_summary: str = Field(min_length=1)
    raw_output: dict[str, Any]
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "result_id",
        "execution_id",
        "skill_id",
        "skill_version",
        "conclusion",
        "reasoning_summary",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "value must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator(
        "supporting_evidence_ids",
        "contradicting_evidence_ids",
        "assumptions",
        "risk_factors",
        "invalid_conditions",
        "missing_information",
    )
    @classmethod
    def normalize_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            msg = "values must not be empty"
            raise ValueError(msg)
        if len(normalized) != len(set(normalized)):
            msg = "duplicate values are not allowed"
            raise ValueError(msg)
        return normalized

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_evidence_contract(self) -> SkillResult:
        if (
            self.direction is not SkillDirection.UNCERTAIN
            and not self.supporting_evidence_ids
        ):
            msg = "non-uncertain SkillResult requires supporting_evidence_ids"
            raise ValueError(msg)
        overlap = set(self.supporting_evidence_ids) & set(
            self.contradicting_evidence_ids
        )
        if overlap:
            msg = "supporting and contradicting evidence IDs must not overlap"
            raise ValueError(msg)
        return self
