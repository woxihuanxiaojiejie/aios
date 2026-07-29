from __future__ import annotations

from datetime import datetime
from typing import Any

from aios.api.schemas.common import ApiSchema
from aios.kernel.brain002 import TokenUsage
from aios.kernel.brain004 import DecisionExecution, DecisionResult
from aios.kernel.enums import Action, DecisionDirection, SkillExecutionStatus


class DecisionExecutionResponse(ApiSchema):
    decision_execution_id: str
    task_id: str
    discussion_result_id: str
    skill_result_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    started_at: datetime
    finished_at: datetime | None
    status: SkillExecutionStatus
    provider: str | None
    model: str | None
    prompt_version: str | None
    token_usage: TokenUsage
    latency_ms: int | None
    retry_count: int
    raw_response: str | None
    parsed_response: dict[str, Any] | None
    error: str | None
    created_at: datetime


class DecisionResultResponse(ApiSchema):
    decision_result_id: str
    decision_execution_id: str
    task_id: str
    discussion_result_id: str
    skill_result_ids: tuple[str, ...]
    direction: DecisionDirection
    confidence: float
    action: Action
    reasoning: tuple[Any, ...]
    supporting_skills: tuple[str, ...]
    opposing_skills: tuple[str, ...]
    discussion_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    risks: tuple[Any, ...]
    rejected_directions: tuple[Any, ...]
    decision_summary: str
    created_at: datetime


def decision_execution_response(
    execution: DecisionExecution,
) -> DecisionExecutionResponse:
    return DecisionExecutionResponse.model_validate(execution.model_dump())


def decision_result_response(result: DecisionResult) -> DecisionResultResponse:
    return DecisionResultResponse.model_validate(result.model_dump())
