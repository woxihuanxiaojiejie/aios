from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now

SchedulerJobStatus = Literal["succeeded", "failed"]


class SchedulerRuntime(KernelModel):
    id_field: ClassVar[str] = "scheduler_instance_id"

    scheduler_instance_id: str = Field(default_factory=lambda: new_id("sch_"))
    started_at: datetime = Field(default_factory=utc_now)
    last_heartbeat_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("started_at", "last_heartbeat_at", "updated_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_times(self) -> SchedulerRuntime:
        if self.last_heartbeat_at < self.started_at:
            msg = "last_heartbeat_at must not be earlier than started_at"
            raise ValueError(msg)
        if self.updated_at < self.started_at:
            msg = "updated_at must not be earlier than started_at"
            raise ValueError(msg)
        return self


class SchedulerJobRun(KernelModel):
    id_field: ClassVar[str] = "job_run_id"

    job_run_id: str = Field(default_factory=lambda: new_id("sjr_"))
    job_id: str = Field(min_length=1, max_length=128)
    status: SchedulerJobStatus
    started_at: datetime
    completed_at: datetime
    processed_count: int | None = Field(default=None, ge=0)
    success_count: int | None = Field(default=None, ge=0)
    failure_count: int | None = Field(default=None, ge=0)
    result_message: str | None = Field(default=None, max_length=500)
    error_type: str | None = Field(default=None, max_length=128)
    error_message: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("started_at", "completed_at", "created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_job_run(self) -> SchedulerJobRun:
        if self.completed_at < self.started_at:
            msg = "completed_at must not be earlier than started_at"
            raise ValueError(msg)
        if self.status == "failed" and not self.error_message:
            msg = "failed job run must have error_message"
            raise ValueError(msg)
        return self
