from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from aios.api.schemas.common import ApiSchema, require_timezone
from aios.kernel.research_run import ResearchRun, ResearchRunStage, ResearchRunStatus


class ResearchRunCreateRequest(ApiSchema):
    watchlist_item_id: str = Field(min_length=1)
    horizon_days: int = Field(default=3)
    as_of: datetime
    workflow: str = Field(default="investment_committee", min_length=1)
    provider: str = Field(default="deepseek", min_length=1)
    model: str = Field(default="deepseek/deepseek-chat", min_length=1)

    @field_validator("as_of")
    @classmethod
    def validate_as_of(cls, value: datetime) -> datetime:
        return require_timezone(value)


class ResearchRunResponse(ApiSchema):
    run_id: str
    research_session_id: str | None
    watchlist_item_id: str
    current_stage: ResearchRunStage
    status: ResearchRunStatus
    vibe_run_id: str | None
    workflow: str
    input_params: dict[str, Any]
    raw_output_reference: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


def research_run_response(run: ResearchRun) -> ResearchRunResponse:
    return ResearchRunResponse.model_validate(run.model_dump())
