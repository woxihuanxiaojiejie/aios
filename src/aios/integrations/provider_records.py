from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderIntakeRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    source: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_url: str | None = None
    source_identifier: str | None = None
    published_at: datetime | None = None
    collected_at: datetime
    raw_artifact_path: Path
    title: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    fingerprint: str = Field(min_length=64, max_length=64)

    @field_validator("published_at", "collected_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "provider intake datetimes must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)


class RSSIntakeRecord(ProviderIntakeRecord):
    source_type: Literal["rss"] = "rss"
    source_url: str = Field(min_length=1)


class WebpageIntakeRecord(ProviderIntakeRecord):
    source_type: Literal["webpage"] = "webpage"
    source_url: str = Field(min_length=1)


class AnnouncementIntakeRecord(ProviderIntakeRecord):
    source_type: Literal["announcement"] = "announcement"
    source_identifier: str = Field(min_length=1)
