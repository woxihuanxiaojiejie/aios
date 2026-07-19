from __future__ import annotations

from datetime import datetime

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

    @field_validator("published_at", "available_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
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
    created_at: datetime


def evidence_response(evidence: Evidence) -> EvidenceResponse:
    return EvidenceResponse.model_validate(evidence.model_dump())
