from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from aios.api.schemas.common import ApiSchema, require_timezone
from aios.kernel.decision import Decision
from aios.kernel.enums import Action, DecisionDirection, DecisionStatus


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
    expected_return: float | None
    max_expected_loss: float | None
    evidence_ids: tuple[str, ...]
    reasoning_summary: str
    status: DecisionStatus
    created_at: datetime
    valid_until: datetime
    research_session_id: str | None
    decision_result_id: str | None
    risk_review_id: str | None
    direction: DecisionDirection | None
    original_direction: DecisionDirection | None
    target_range: tuple[float, float] | None
    entry_conditions: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    stop_loss: float | None
    position_suggestion: float | None
    risk_factors: tuple[str, ...]
    supporting_skill_ids: tuple[str, ...]
    dissenting_opinions: tuple[str, ...]
    market_regime: str | None
    generated_at: datetime | None
    planned_settlement_at: datetime | None
    unavailable_fields: tuple[str, ...]
    downgrade_reasons: tuple[str, ...]


def decision_response(decision: Decision) -> DecisionResponse:
    return DecisionResponse.model_validate(decision.model_dump())
