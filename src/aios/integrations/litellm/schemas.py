from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aios.kernel.enums import Action


class DecisionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Action
    confidence: float = Field(ge=0, le=1)
    expected_return: float
    max_expected_loss: float = Field(ge=0)
    horizon: str = Field(min_length=1)
    reasoning_summary: str = Field(min_length=1, max_length=1200)
    supporting_evidence_ids: tuple[str, ...] = Field(min_length=1)
    risk_factors: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()

    @field_validator("supporting_evidence_ids")
    @classmethod
    def validate_unique_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            msg = "supporting_evidence_ids must not contain duplicates"
            raise ValueError(msg)
        return value
