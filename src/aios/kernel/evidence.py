from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now


class Evidence(KernelModel):
    id_field: ClassVar[str] = "evidence_id"

    evidence_id: str = Field(default_factory=lambda: new_id("ev_"))
    evidence_type: str
    source: str
    symbols: tuple[str, ...] = Field(min_length=1)
    published_at: datetime
    available_at: datetime
    summary: str = Field(min_length=1)
    reliability: float = Field(ge=0, le=1)
    content_hash: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    title: str | None = None
    raw_content: str | None = None
    raw_response: dict[str, Any] | None = None
    source_type: str | None = None
    source_identifier: str | None = None
    source_url: str | None = None
    collected_at: datetime | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str | None = None
    credibility: float | None = Field(default=None, ge=0, le=1)
    freshness: str | None = None
    processing_status: str = Field(default="parsed", min_length=1)
    parse_error: str | None = None
    legacy_brain_evidence_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("published_at", "available_at", "collected_at", "created_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(symbol.strip() == "" for symbol in value):
            msg = "symbols must not contain empty strings"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_availability(self) -> Evidence:
        if self.available_at < self.published_at:
            msg = "available_at must not be earlier than published_at"
            raise ValueError(msg)
        return self
