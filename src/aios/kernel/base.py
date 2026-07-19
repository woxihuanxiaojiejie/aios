from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict


def new_id(prefix: str) -> str:
    return f"{prefix}{uuid4()}"


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "datetime values must be timezone-aware"
        raise ValueError(msg)
    return value.astimezone(UTC)


class KernelModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id_field: ClassVar[str]

    @property
    def entity_id(self) -> str:
        return str(getattr(self, self.id_field))
