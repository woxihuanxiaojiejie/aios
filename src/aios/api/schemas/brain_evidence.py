from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aios.integrations.evidence import Evidence


class BrainEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID
    source: str
    source_type: str
    source_identifier: str | None
    source_url: str | None
    title: str
    summary: str | None
    content: str
    published_at: datetime | None
    collected_at: datetime
    available_at: datetime
    fingerprint: str
    provider_record: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    raw_artifact_path: Path | None = None


class BrainEvidenceListResponse(BaseModel):
    items: list[BrainEvidenceResponse]
    limit: int
    offset: int
    count: int


def brain_evidence_response(
    evidence: Evidence,
    *,
    include_provider_record: bool = False,
    include_metadata: bool = False,
    include_raw_artifact_path: bool = False,
) -> BrainEvidenceResponse:
    return BrainEvidenceResponse(
        evidence_id=evidence.evidence_id,
        source=evidence.source,
        source_type=evidence.source_type,
        source_identifier=evidence.source_identifier,
        source_url=evidence.source_url,
        title=evidence.title,
        summary=evidence.summary,
        content=evidence.content,
        published_at=evidence.published_at,
        collected_at=evidence.collected_at,
        available_at=evidence.available_at,
        fingerprint=evidence.fingerprint,
        provider_record=(
            evidence.provider_record.model_dump(mode="json")
            if include_provider_record
            else None
        ),
        metadata=evidence.metadata if include_metadata else None,
        raw_artifact_path=(
            evidence.raw_artifact_path if include_raw_artifact_path else None
        ),
    )
