from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ApiSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListResponse[ItemT](BaseModel):
    items: list[ItemT]
    limit: int
    offset: int
    count: int


class CompleteExperimentRequest(ApiSchema):
    finished_at: datetime

    @field_validator("finished_at")
    @classmethod
    def validate_finished_at(cls, value: datetime) -> datetime:
        return require_timezone(value)


def require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "datetime must include timezone"
        raise ValueError(msg)
    return value


def page[ItemT](items: list[ItemT], limit: int, offset: int) -> ListResponse[ItemT]:
    return ListResponse(
        items=items[offset : offset + limit],
        limit=limit,
        offset=offset,
        count=len(items[offset : offset + limit]),
    )


JsonObject = dict[str, Any]
