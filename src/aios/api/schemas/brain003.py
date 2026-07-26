from __future__ import annotations

from datetime import datetime
from typing import Any

from aios.api.schemas.common import ApiSchema
from aios.kernel.brain002 import TokenUsage
from aios.kernel.brain003 import (
    ConflictReview,
    CounterArgument,
    DiscussionExecution,
    DiscussionResult,
    EvidenceReview,
    RevisionSuggestion,
)
from aios.kernel.enums import SkillExecutionStatus


class DiscussionSchema(ApiSchema):
    conflicts: tuple[ConflictReview, ...]
    evidence_reviews: tuple[EvidenceReview, ...]
    counter_arguments: tuple[CounterArgument, ...]
    revision_suggestions: tuple[RevisionSuggestion, ...]
    discussion_summary: str
    discussion_confidence: float


class DiscussionExecutionResponse(ApiSchema):
    discussion_execution_id: str
    task_id: str
    skill_result_ids: tuple[str, ...]
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


class DiscussionResultResponse(ApiSchema):
    discussion_result_id: str
    discussion_execution_id: str
    task_id: str
    skill_result_ids: tuple[str, ...]
    conflicts: tuple[ConflictReview, ...]
    evidence_reviews: tuple[EvidenceReview, ...]
    counter_arguments: tuple[CounterArgument, ...]
    revision_suggestions: tuple[RevisionSuggestion, ...]
    discussion_summary: str
    discussion_confidence: float
    created_at: datetime


class DiscussionRunResponse(ApiSchema):
    execution: DiscussionExecutionResponse
    result: DiscussionResultResponse | None


def discussion_execution_response(
    execution: DiscussionExecution,
) -> DiscussionExecutionResponse:
    return DiscussionExecutionResponse(**execution.model_dump())


def discussion_result_response(result: DiscussionResult) -> DiscussionResultResponse:
    return DiscussionResultResponse(**result.model_dump())
