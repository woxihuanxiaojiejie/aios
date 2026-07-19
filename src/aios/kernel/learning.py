from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import ApprovalStatus, LearningType


class Learning(KernelModel):
    id_field: ClassVar[str] = "learning_id"

    learning_id: str = Field(default_factory=lambda: new_id("lr_"))
    review_id: str = Field(min_length=1)
    learning_type: LearningType
    target: str = Field(min_length=1)
    before: Any
    after: Any
    reason: str = Field(min_length=1)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_change_and_approval(self) -> Learning:
        if self.before == self.after:
            msg = "before and after must not be identical"
            raise ValueError(msg)
        return self
