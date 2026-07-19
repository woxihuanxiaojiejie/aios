from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import Action, DecisionStatus


class Decision(KernelModel):
    id_field: ClassVar[str] = "decision_id"

    decision_id: str = Field(default_factory=lambda: new_id("dc_"))
    experiment_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    action: Action
    horizon: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    expected_return: float
    max_expected_loss: float
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    reasoning_summary: str = Field(min_length=1)
    status: DecisionStatus = DecisionStatus.PROPOSED
    created_at: datetime = Field(default_factory=utc_now)
    valid_until: datetime

    @field_validator("created_at", "valid_until")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_valid_until(self) -> Decision:
        if self.valid_until <= self.created_at:
            msg = "valid_until must be later than created_at"
            raise ValueError(msg)
        return self
