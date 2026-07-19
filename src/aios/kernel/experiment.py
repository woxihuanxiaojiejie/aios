from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import ExperimentStatus


class Experiment(KernelModel):
    id_field: ClassVar[str] = "experiment_id"

    experiment_id: str = Field(default_factory=lambda: new_id("ex_"))
    name: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    agent_config_version: str = Field(min_length=1)
    dataset_snapshot: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.CREATED
    started_at: datetime
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("started_at", "finished_at", "created_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_finish_time(self) -> Experiment:
        if self.finished_at is not None and self.finished_at < self.started_at:
            msg = "finished_at must not be earlier than started_at"
            raise ValueError(msg)
        return self
