from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now

ResearchRunStage = Literal[
    "session",
    "evidence",
    "vibe_research",
    "agent_reports",
    "hypotheses",
    "debate",
    "proposal",
    "risk_review",
    "decision",
    "completed",
    "failed",
]

ResearchRunStatus = Literal["running", "completed", "failed"]


class ResearchRun(KernelModel):
    id_field: ClassVar[str] = "run_id"

    run_id: str = Field(default_factory=lambda: new_id("run_"))
    research_session_id: str | None = None
    watchlist_item_id: str = Field(min_length=1)
    symbol: str | None = None
    research_window_key: str | None = None
    current_stage: ResearchRunStage = "session"
    status: ResearchRunStatus = "running"
    vibe_run_id: str | None = None
    workflow: str = Field(min_length=1)
    input_params: dict[str, Any] = Field(default_factory=dict)
    raw_output_reference: str | None = None
    failed_stage: str | None = None
    error_type: str | None = None
    error: str | None = None
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at", "updated_at", "finished_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @field_validator(
        "error",
        "research_session_id",
        "vibe_run_id",
        "symbol",
        "research_window_key",
        "failed_stage",
        "error_type",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_status_stage(self) -> ResearchRun:
        if self.status == "completed" and self.current_stage != "completed":
            msg = "completed ResearchRun must have completed stage"
            raise ValueError(msg)
        if self.status == "failed" and self.current_stage != "failed":
            msg = "failed ResearchRun must have failed stage"
            raise ValueError(msg)
        if self.updated_at < self.created_at:
            msg = "updated_at must not be earlier than created_at"
            raise ValueError(msg)
        if self.finished_at is not None and self.finished_at < self.created_at:
            msg = "finished_at must not be earlier than created_at"
            raise ValueError(msg)
        if self.status == "failed" and (
            not self.failed_stage or not self.error_type or not self.error
        ):
            msg = "failed ResearchRun must have failed_stage, error_type, and error"
            raise ValueError(msg)
        return self
