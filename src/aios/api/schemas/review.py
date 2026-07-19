from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from aios.api.schemas.common import ApiSchema
from aios.kernel.enums import Outcome
from aios.kernel.review import Review


class ReviewCreateRequest(ApiSchema):
    decision_id: str = Field(min_length=1)
    actual_return: Decimal | None = None
    direction_correct: bool | None = None
    risk_limit_breached: bool | None = None
    outcome: Outcome
    cause_tags: list[str] = Field(default_factory=list)
    review_summary: str = Field(min_length=1)


class ReviewResponse(ApiSchema):
    review_id: str
    decision_id: str
    actual_return: Decimal | None
    direction_correct: bool | None
    risk_limit_breached: bool | None
    outcome: Outcome
    cause_tags: tuple[str, ...]
    review_summary: str
    created_at: datetime


def review_response(review: Review) -> ReviewResponse:
    return ReviewResponse.model_validate(review.model_dump())
