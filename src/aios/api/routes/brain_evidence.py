from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from aios.api.dependencies import BrainEvidenceRepositoryDep
from aios.api.schemas.brain_evidence import (
    BrainEvidenceListResponse,
    BrainEvidenceResponse,
    brain_evidence_response,
)
from aios.storage.postgres.evidence_repository import (
    EvidenceRepository,
    TimestampField,
)

router = APIRouter(prefix="/brain/evidence", tags=["brain-evidence"])


@router.get("/{evidence_id}", response_model=BrainEvidenceResponse)
def get_brain_evidence(
    evidence_id: UUID,
    repository: BrainEvidenceRepositoryDep,
    include_provider_record: bool = False,
    include_metadata: bool = False,
    include_raw_artifact_path: bool = False,
) -> BrainEvidenceResponse:
    configured_repository = _require_repository(repository)
    evidence = configured_repository.get_by_id(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Brain Evidence not found")
    return brain_evidence_response(
        evidence,
        include_provider_record=include_provider_record,
        include_metadata=include_metadata,
        include_raw_artifact_path=include_raw_artifact_path,
    )


@router.get("", response_model=BrainEvidenceListResponse)
def list_brain_evidence(
    repository: BrainEvidenceRepositoryDep,
    source: str | None = None,
    source_type: str | None = None,
    fingerprint: str | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    collected_from: datetime | None = None,
    collected_to: datetime | None = None,
    as_of: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort_by: TimestampField = "collected_at",
    sort_order: Literal["asc", "desc"] = "asc",
    include_provider_record: bool = False,
    include_metadata: bool = False,
    include_raw_artifact_path: bool = False,
) -> BrainEvidenceListResponse:
    configured_repository = _require_repository(repository)
    timestamps = (
        published_from,
        published_to,
        collected_from,
        collected_to,
        as_of,
    )
    if any(
        value is not None and (value.tzinfo is None or value.utcoffset() is None)
        for value in timestamps
    ):
        raise HTTPException(status_code=422, detail="datetime must include timezone")
    items, count = configured_repository.query(
        source=source,
        source_type=source_type,
        fingerprint=fingerprint,
        published_from=published_from,
        published_to=published_to,
        collected_from=collected_from,
        collected_to=collected_to,
        available_before=as_of,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return BrainEvidenceListResponse(
        items=[
            brain_evidence_response(
                item,
                include_provider_record=include_provider_record,
                include_metadata=include_metadata,
                include_raw_artifact_path=include_raw_artifact_path,
            )
            for item in items
        ],
        limit=limit,
        offset=offset,
        count=count,
    )


def _require_repository(
    repository: EvidenceRepository | None,
) -> EvidenceRepository:
    if repository is None:
        raise HTTPException(
            status_code=503,
            detail="BRAIN-001 Evidence repository is not configured",
        )
    return repository
