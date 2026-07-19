from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from aios.api.schemas.common import ApiSchema, require_timezone
from aios.kernel.decision import Decision
from aios.kernel.enums import Action, DecisionStatus


class DecisionCreateRequest(ApiSchema):
    experiment_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    action: Action
    horizon: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    expected_return: float
    max_expected_loss: float
    evidence_ids: list[str] = Field(min_length=1)
    reasoning_summary: str = Field(min_length=1)
    valid_until: datetime

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, value: datetime) -> datetime:
        return require_timezone(value)


class DecisionResponse(ApiSchema):
    decision_id: str
    experiment_id: str
    symbol: str
    action: Action
    horizon: str
    confidence: float
    expected_return: float
    max_expected_loss: float
    evidence_ids: tuple[str, ...]
    reasoning_summary: str
    status: DecisionStatus
    created_at: datetime
    valid_until: datetime


def decision_response(decision: Decision) -> DecisionResponse:
    return DecisionResponse.model_validate(decision.model_dump())
