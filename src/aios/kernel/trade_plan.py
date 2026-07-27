from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import DecisionDirection, TradePlanStatus

TRADE_PLAN_UNAVAILABLE_FIELDS = frozenset(
    {
        "research_session_id",
        "direction",
        "entry_conditions",
        "target_range",
        "stop_loss",
        "invalidation_conditions",
        "position_suggestion",
        "planned_settlement_at",
        "expected_return",
        "max_expected_loss",
        "supporting_skill_ids",
        "risk_factors",
    }
)


class TradePlan(KernelModel):
    id_field: ClassVar[str] = "trade_plan_id"

    trade_plan_id: str = Field(default_factory=lambda: new_id("tp_"))
    decision_id: str = Field(min_length=1)
    research_session_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    direction: DecisionDirection
    status: TradePlanStatus
    planned_entry: tuple[str, ...] = ()
    entry_conditions: tuple[str, ...] = ()
    target: tuple[float, float] | None = None
    stop_loss: float | None = None
    invalidation_conditions: tuple[str, ...] = ()
    planned_position: float | None = Field(default=None, ge=0, le=1)
    horizon: str = Field(min_length=1)
    expiry: datetime
    fee_model: dict[str, Any] = Field(default_factory=dict)
    slippage_model: dict[str, Any] = Field(default_factory=dict)
    unavailable_fields: tuple[str, ...] = ()
    no_trade_reasons: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("expiry", "created_at", "updated_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator(
        "planned_entry",
        "entry_conditions",
        "invalidation_conditions",
        "unavailable_fields",
        "no_trade_reasons",
    )
    @classmethod
    def validate_unique_text(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            msg = "TradePlan tuple values must not be empty"
            raise ValueError(msg)
        if len(normalized) != len(set(normalized)):
            msg = "duplicate TradePlan tuple values are not allowed"
            raise ValueError(msg)
        return normalized

    @field_validator("unavailable_fields")
    @classmethod
    def validate_unavailable_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = set(value) - TRADE_PLAN_UNAVAILABLE_FIELDS
        if unknown:
            msg = "unavailable_fields must contain stable TradePlan field names"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_status_payload(self) -> TradePlan:
        if self.updated_at < self.created_at:
            msg = "updated_at must not be earlier than created_at"
            raise ValueError(msg)
        if self.target is not None and self.target[0] > self.target[1]:
            msg = "target lower bound must not exceed upper bound"
            raise ValueError(msg)
        if self.status is TradePlanStatus.READY:
            missing = []
            if not self.planned_entry:
                missing.append("planned_entry")
            if self.target is None:
                missing.append("target")
            if self.stop_loss is None:
                missing.append("stop_loss")
            if not self.invalidation_conditions:
                missing.append("invalidation_conditions")
            if self.planned_position is None:
                missing.append("planned_position")
            if missing:
                msg = f"ready TradePlan missing fields: {', '.join(missing)}"
                raise ValueError(msg)
        if self.status is TradePlanStatus.NO_TRADE and any(
            (
                self.planned_entry,
                self.target is not None,
                self.stop_loss is not None,
                self.planned_position is not None,
            )
        ):
            msg = "no_trade TradePlan must not contain trade execution fields"
            raise ValueError(msg)
        return self
