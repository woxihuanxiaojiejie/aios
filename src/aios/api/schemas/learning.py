from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from aios.api.schemas.common import ApiSchema
from aios.kernel.enums import ApprovalStatus, LearningType
from aios.kernel.learning import Learning


class LearningCreateRequest(ApiSchema):
    review_id: str = Field(min_length=1)
    learning_type: LearningType
    target: str = Field(min_length=1)
    before: Any
    after: Any
    reason: str = Field(min_length=1)


class LearningResponse(ApiSchema):
    learning_id: str
    review_id: str
    learning_type: LearningType
    target: str
    before: Any
    after: Any
    reason: str
    approval_status: ApprovalStatus
    created_at: datetime


def learning_response(learning: Learning) -> LearningResponse:
    return LearningResponse.model_validate(learning.model_dump())
