from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import (
    DirectionalResult,
    EvaluationFinalResult,
    OutcomeStatus,
    ReturnResult,
    RiskResult,
)


class DecisionOutcome(KernelModel):
    id_field: ClassVar[str] = "outcome_id"

    outcome_id: str = Field(default_factory=lambda: new_id("oc_"))
    decision_id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    horizon: str = Field(min_length=1)
    horizon_semantics: str = Field(min_length=1)
    observation_started_at: datetime
    observation_ended_at: datetime
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    realized_return: Decimal | None = None
    maximum_adverse_excursion: Decimal | None = None
    maximum_favorable_excursion: Decimal | None = None
    market_data_source: str = Field(min_length=1)
    market_data_snapshot: dict[str, Any] = Field(default_factory=dict)
    settled_at: datetime = Field(default_factory=utc_now)
    status: OutcomeStatus
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "observation_started_at",
        "observation_ended_at",
        "settled_at",
        "created_at",
    )
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator(
        "entry_price",
        "exit_price",
        "realized_return",
        "maximum_adverse_excursion",
        "maximum_favorable_excursion",
        mode="before",
    )
    @classmethod
    def validate_decimal(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    @model_validator(mode="after")
    def validate_settled_values(self) -> DecisionOutcome:
        if self.observation_ended_at <= self.observation_started_at:
            msg = "observation_ended_at must be later than observation_started_at"
            raise ValueError(msg)
        if self.status is not OutcomeStatus.SETTLED:
            return self
        required = {
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "realized_return": self.realized_return,
            "maximum_adverse_excursion": self.maximum_adverse_excursion,
            "maximum_favorable_excursion": self.maximum_favorable_excursion,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            msg = f"settled outcomes require: {', '.join(missing)}"
            raise ValueError(msg)
        if self.entry_price is not None and self.entry_price <= 0:
            msg = "entry_price must be positive when settled"
            raise ValueError(msg)
        if self.exit_price is not None and self.exit_price <= 0:
            msg = "exit_price must be positive when settled"
            raise ValueError(msg)
        return self


class DecisionEvaluation(KernelModel):
    id_field: ClassVar[str] = "evaluation_id"

    evaluation_id: str = Field(default_factory=lambda: new_id("de_"))
    decision_id: str = Field(min_length=1)
    outcome_id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    directional_result: DirectionalResult
    return_result: ReturnResult
    risk_result: RiskResult
    final_result: EvaluationFinalResult
    evaluation_rules_version: str = Field(min_length=1)
    evaluated_at: datetime = Field(default_factory=utc_now)
    explanation: str = Field(min_length=1, max_length=1200)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("evaluated_at", "created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class ResearchSettlementRecord(KernelModel):
    id_field: ClassVar[str] = "research_settlement_id"

    research_settlement_id: str = Field(default_factory=lambda: new_id("sr_"))
    assembly_id: str = Field(min_length=1)
    research_session_id: str = Field(min_length=1)
    debate_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    risk_review_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    outcome_id: str = Field(min_length=1)
    evaluation_id: str = Field(min_length=1)
    review_id: str = Field(min_length=1)
    learning_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...]
    report_ids: tuple[str, ...]
    hypothesis_ids: tuple[str, ...]
    settled_at: datetime
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("learning_ids", "evidence_ids", "report_ids", "hypothesis_ids")
    @classmethod
    def validate_unique_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "duplicate IDs are not allowed"
            raise ValueError(msg)
        return value

    @field_validator("settled_at", "created_at")
    @classmethod
    def validate_record_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)
