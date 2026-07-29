from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import Action, DecisionDirection, DecisionStatus

STABLE_UNAVAILABLE_FIELDS = frozenset(
    {
        "target_range",
        "entry_conditions",
        "invalidation_conditions",
        "stop_loss",
        "position_suggestion",
        "expected_return",
        "max_expected_loss",
        "supporting_skill_ids",
        "risk_factors",
        "planned_settlement_at",
    }
)
TRADEABLE_ACTIONS = frozenset({Action.BUY, Action.SELL})


class Decision(KernelModel):
    id_field: ClassVar[str] = "decision_id"

    decision_id: str = Field(default_factory=lambda: new_id("dc_"))
    experiment_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    action: Action
    horizon: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    expected_return: float | None
    max_expected_loss: float | None
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    reasoning_summary: str = Field(min_length=1)
    status: DecisionStatus = DecisionStatus.PROPOSED
    created_at: datetime = Field(default_factory=utc_now)
    valid_until: datetime
    research_session_id: str | None = Field(default=None, min_length=1)
    decision_result_id: str | None = Field(default=None, min_length=1)
    risk_review_id: str | None = Field(default=None, min_length=1)
    direction: DecisionDirection | None = None
    original_direction: DecisionDirection | None = None
    target_range: tuple[float, float] | None = None
    entry_conditions: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    stop_loss: float | None = None
    position_suggestion: float | None = Field(default=None, ge=0, le=1)
    risk_factors: tuple[str, ...] = ()
    supporting_skill_ids: tuple[str, ...] = ()
    dissenting_opinions: tuple[str, ...] = ()
    market_regime: str | None = None
    generated_at: datetime | None = None
    planned_settlement_at: datetime | None = None
    unavailable_fields: tuple[str, ...] = ()
    downgrade_reasons: tuple[str, ...] = ()

    @field_validator(
        "created_at",
        "valid_until",
        "generated_at",
        "planned_settlement_at",
    )
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @field_validator(
        "entry_conditions",
        "invalidation_conditions",
        "risk_factors",
        "supporting_skill_ids",
        "dissenting_opinions",
        "unavailable_fields",
        "downgrade_reasons",
    )
    @classmethod
    def validate_unique_text(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            msg = "Decision tuple values must not be empty"
            raise ValueError(msg)
        if len(normalized) != len(set(normalized)):
            msg = "duplicate Decision tuple values are not allowed"
            raise ValueError(msg)
        return normalized

    @field_validator("unavailable_fields")
    @classmethod
    def validate_unavailable_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = set(value) - STABLE_UNAVAILABLE_FIELDS
        if unknown:
            msg = "unavailable_fields must contain stable field names"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_valid_until(self) -> Decision:
        if self.valid_until <= self.created_at:
            msg = "valid_until must be later than created_at"
            raise ValueError(msg)
        if (
            self.target_range is not None
            and self.target_range[0] > self.target_range[1]
        ):
            msg = "target_range lower bound must not exceed upper bound"
            raise ValueError(msg)
        if self.decision_result_id is not None:
            self._validate_brain_decision()
        return self

    def _validate_brain_decision(self) -> None:
        if self.generated_at is None:
            msg = "BRAIN Decision requires generated_at"
            raise ValueError(msg)
        if self.action not in TRADEABLE_ACTIONS:
            return
        missing = []
        if not self.entry_conditions:
            missing.append("entry_conditions")
        if self.target_range is None:
            missing.append("target_range")
        if self.stop_loss is None and not self.invalidation_conditions:
            missing.append("stop_loss")
        if self.position_suggestion is None:
            missing.append("position_suggestion")
        if not self.supporting_skill_ids:
            missing.append("supporting_skill_ids")
        if not self.risk_factors:
            missing.append("risk_factors")
        if self.planned_settlement_at is None:
            missing.append("planned_settlement_at")
        if self.expected_return is None:
            missing.append("expected_return")
        if self.max_expected_loss is None:
            missing.append("max_expected_loss")
        if missing:
            msg = f"tradeable BRAIN Decision missing fields: {', '.join(missing)}"
            raise ValueError(msg)
