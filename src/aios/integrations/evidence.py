from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aios.integrations.provider_records import (
    AnnouncementIntakeRecord,
    ProviderIntakeRecord,
    RSSIntakeRecord,
    WebpageIntakeRecord,
)


class Evidence(BaseModel):
    """Unified, traceable evidence produced from a validated provider record."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    id_field: ClassVar[str] = "evidence_id"

    evidence_id: UUID = Field(default_factory=uuid4)
    source: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_identifier: str | None = None
    source_url: str | None = None
    title: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    published_at: datetime | None = None
    collected_at: datetime
    available_at: datetime
    fingerprint: str = Field(min_length=64, max_length=64)
    raw_artifact_path: Path
    provider_record: ProviderIntakeRecord
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("published_at", "collected_at", "available_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "evidence datetimes must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_point_in_time(self) -> Evidence:
        if self.available_at < self.collected_at:
            msg = "available_at must not be earlier than collected_at"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_metadata_extensions(self) -> Evidence:
        core_fields = {
            "evidence_id",
            "source",
            "source_type",
            "source_identifier",
            "source_url",
            "title",
            "summary",
            "content",
            "published_at",
            "collected_at",
            "available_at",
            "fingerprint",
            "raw_artifact_path",
            "provider_record",
        }
        overlap = core_fields.intersection(self.metadata)
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ValueError(f"metadata may only contain extension fields: {names}")
        return self

    @classmethod
    def from_provider_record(
        cls,
        record: ProviderIntakeRecord,
        *,
        available_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Evidence:
        return cls(
            source=record.source,
            source_type=record.source_type,
            source_identifier=record.source_identifier or record.source_url,
            source_url=record.source_url,
            title=record.title,
            summary=record.summary,
            content=record.content,
            published_at=record.published_at,
            collected_at=record.collected_at,
            available_at=available_at or record.collected_at,
            fingerprint=record.fingerprint,
            raw_artifact_path=record.raw_artifact_path,
            provider_record=record,
            metadata=metadata or {},
        )


def evidence_from_rss(
    record: RSSIntakeRecord,
    *,
    available_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Evidence:
    return Evidence.from_provider_record(
        record, available_at=available_at, metadata=metadata
    )


def evidence_from_webpage(
    record: WebpageIntakeRecord,
    *,
    available_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Evidence:
    return Evidence.from_provider_record(
        record, available_at=available_at, metadata=metadata
    )


def evidence_from_announcement(
    record: AnnouncementIntakeRecord,
    *,
    available_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Evidence:
    return Evidence.from_provider_record(
        record, available_at=available_at, metadata=metadata
    )
