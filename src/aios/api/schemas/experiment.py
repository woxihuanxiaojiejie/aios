from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from aios.api.schemas.common import ApiSchema, JsonObject, require_timezone
from aios.kernel.enums import ExperimentStatus
from aios.kernel.experiment import Experiment


class ExperimentCreateRequest(ApiSchema):
    name: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    agent_config_version: str = Field(min_length=1)
    dataset_snapshot: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    parameters: JsonObject = Field(default_factory=dict)
    started_at: datetime

    @field_validator("started_at")
    @classmethod
    def validate_started_at(cls, value: datetime) -> datetime:
        return require_timezone(value)


class ExperimentResponse(ApiSchema):
    experiment_id: str
    name: str
    model: str
    prompt_version: str
    agent_config_version: str
    dataset_snapshot: str
    evidence_ids: tuple[str, ...]
    parameters: JsonObject
    status: ExperimentStatus
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime


def experiment_response(experiment: Experiment) -> ExperimentResponse:
    return ExperimentResponse.model_validate(experiment.model_dump())
