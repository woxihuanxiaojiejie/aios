from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from aios.api.schemas.common import ApiSchema, JsonObject, require_timezone
from aios.kernel.evidence import Evidence


class EvidenceCreateRequest(ApiSchema):
    evidence_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    symbols: list[str] = Field(min_length=1)
    published_at: datetime
    available_at: datetime
    summary: str = Field(min_length=1)
    reliability: float = Field(ge=0, le=1)
    content_hash: str = Field(min_length=1)
    metadata: JsonObject = Field(default_factory=dict)
    title: str | None = None
    raw_content: str | None = None
    raw_response: JsonObject | None = None
    source_type: str | None = None
    source_identifier: str | None = None
    source_url: str | None = None
    collected_at: datetime | None = None
    entities: JsonObject = Field(default_factory=dict)
    fingerprint: str | None = None
    credibility: float | None = Field(default=None, ge=0, le=1)
    freshness: str | None = None
    processing_status: str = Field(default="parsed", min_length=1)
    parse_error: str | None = None
    legacy_brain_evidence_id: str | None = None

    @field_validator("published_at", "available_at", "collected_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_timezone(value)


class EvidenceResponse(ApiSchema):
    evidence_id: str
    evidence_type: str
    source: str
    symbols: tuple[str, ...]
    published_at: datetime
    available_at: datetime
    summary: str
    reliability: float
    content_hash: str
    metadata: JsonObject
    title: str | None
    raw_content: str | None
    raw_response: dict[str, Any] | None
    source_type: str | None
    source_identifier: str | None
    source_url: str | None
    collected_at: datetime | None
    entities: JsonObject
    fingerprint: str | None
    credibility: float | None
    freshness: str | None
    processing_status: str
    parse_error: str | None
    legacy_brain_evidence_id: str | None
    created_at: datetime


def evidence_response(evidence: Evidence) -> EvidenceResponse:
    return EvidenceResponse.model_validate(evidence.model_dump())
