from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import Field, field_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import Outcome


class Review(KernelModel):
    id_field: ClassVar[str] = "review_id"

    review_id: str = Field(default_factory=lambda: new_id("rv_"))
    decision_id: str = Field(min_length=1)
    actual_return: float
    direction_correct: bool
    risk_limit_breached: bool
    outcome: Outcome
    cause_tags: tuple[str, ...] = Field(default_factory=tuple)
    review_summary: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator("cause_tags")
    @classmethod
    def dedupe_cause_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        deduped: list[str] = []
        for tag in value:
            clean = tag.strip()
            if clean and clean not in seen:
                seen.add(clean)
                deduped.append(clean)
        return tuple(deduped)
