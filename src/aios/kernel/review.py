from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import ClassVar

from pydantic import Field, field_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import Outcome


class Review(KernelModel):
    id_field: ClassVar[str] = "review_id"

    review_id: str = Field(default_factory=lambda: new_id("rv_"))
    decision_id: str = Field(min_length=1)
    actual_return: Decimal | None = None
    direction_correct: bool | None = None
    risk_limit_breached: bool | None = None
    outcome: Outcome
    cause_tags: tuple[str, ...] = Field(default_factory=tuple)
    review_summary: str = Field(min_length=1)
    success_reasons: tuple[str, ...] = Field(default_factory=tuple)
    failure_reasons: tuple[str, ...] = Field(default_factory=tuple)
    effective_evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    effective_skill_ids: tuple[str, ...] = Field(default_factory=tuple)
    mistaken_judgement_ids: tuple[str, ...] = Field(default_factory=tuple)
    reference_ids: dict[str, list[str]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator("actual_return", mode="before")
    @classmethod
    def validate_decimal(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    @field_validator("cause_tags")
    @classmethod
    def dedupe_cause_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for tag in value:
            clean = tag.strip()
            if clean:
                seen.add(clean)
        return tuple(sorted(seen))
