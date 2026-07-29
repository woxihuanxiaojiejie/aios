from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from aios.api.schemas.common import ApiSchema
from aios.kernel.brain002 import (
    AnalysisTask,
    SkillDefinition,
    SkillExecution,
    SkillResult,
    TokenUsage,
)
from aios.kernel.enums import SkillDirection, SkillExecutionStatus, SkillStatus


class AnalysisTaskCreateRequest(ApiSchema):
    symbol: str = Field(min_length=1)
    market: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)
    horizon: str = Field(min_length=1)
    as_of: datetime
    evidence_ids: tuple[str, ...] = ()
    user_constraints: dict[str, Any] = Field(default_factory=dict)
    requested_skill_ids: tuple[str, ...] = ()


class AnalysisTaskResponse(ApiSchema):
    task_id: str
    symbol: str
    market: str
    asset_type: str
    horizon: str
    as_of: datetime
    evidence_ids: tuple[str, ...]
    user_constraints: dict[str, Any]
    requested_skill_ids: tuple[str, ...]
    created_at: datetime


class SkillDefinitionResponse(ApiSchema):
    definition_id: str
    skill_id: str
    name: str
    version: str
    description: str
    supported_markets: tuple[str, ...]
    supported_asset_types: tuple[str, ...]
    supported_horizons: tuple[str, ...]
    required_evidence_types: tuple[str, ...]
    trigger_conditions: dict[str, Any]
    dependencies: tuple[str, ...]
    conflicts: tuple[str, ...]
    status: SkillStatus
    created_at: datetime
    updated_at: datetime


class SkillDefinitionListResponse(ApiSchema):
    items: list[SkillDefinitionResponse]


class SkillExecutionResponse(ApiSchema):
    execution_id: str
    task_id: str
    skill_id: str
    skill_version: str
    started_at: datetime
    finished_at: datetime | None
    status: SkillExecutionStatus
    provider: str | None
    model: str | None
    prompt_version: str | None
    token_usage: TokenUsage
    latency_ms: int | None
    retry_count: int
    error: str | None


class SkillResultResponse(ApiSchema):
    result_id: str
    execution_id: str
    skill_id: str
    skill_version: str
    conclusion: str
    direction: SkillDirection
    confidence: float
    supporting_evidence_ids: tuple[str, ...]
    contradicting_evidence_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    risk_factors: tuple[str, ...]
    invalid_conditions: tuple[str, ...]
    missing_information: tuple[str, ...]
    reasoning_summary: str
    raw_output: dict[str, Any]
    created_at: datetime


class SkillResultListResponse(ApiSchema):
    items: list[SkillResultResponse]


class SkillExecutionListResponse(ApiSchema):
    items: list[SkillExecutionResponse]


class AnalysisExecutionRequest(ApiSchema):
    model: str = Field(min_length=1)
    timeout_seconds: float = Field(default=30, gt=0)
    max_attempts: int = Field(default=2, ge=1)
    market_context: dict[str, Any] = Field(default_factory=dict)


class AnalysisExecutionResponse(ApiSchema):
    executions: list[SkillExecutionResponse]
    results: list[SkillResultResponse]


def analysis_task_response(task: AnalysisTask) -> AnalysisTaskResponse:
    return AnalysisTaskResponse(**task.model_dump())


def skill_definition_response(
    definition: SkillDefinition,
) -> SkillDefinitionResponse:
    return SkillDefinitionResponse(
        definition_id=definition.definition_id,
        skill_id=definition.skill_id,
        name=definition.name,
        version=definition.version,
        description=definition.description,
        supported_markets=definition.supported_markets,
        supported_asset_types=definition.supported_asset_types,
        supported_horizons=definition.supported_horizons,
        required_evidence_types=definition.required_evidence_types,
        trigger_conditions=definition.trigger_conditions,
        dependencies=definition.dependencies,
        conflicts=definition.conflicts,
        status=definition.status,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
    )


def skill_execution_response(
    execution: SkillExecution,
) -> SkillExecutionResponse:
    return SkillExecutionResponse(**execution.model_dump())


def skill_result_response(result: SkillResult) -> SkillResultResponse:
    return SkillResultResponse(**result.model_dump())
