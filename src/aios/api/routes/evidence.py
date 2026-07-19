from __future__ import annotations

from fastapi import APIRouter, Query, status

from aios.api.dependencies import LifecycleDep
from aios.api.schemas.common import ListResponse, page
from aios.api.schemas.evidence import (
    EvidenceCreateRequest,
    EvidenceResponse,
    evidence_response,
)
from aios.kernel.evidence import Evidence

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_evidence(
    request: EvidenceCreateRequest,
    lifecycle: LifecycleDep,
) -> EvidenceResponse:
    evidence = Evidence(**request.model_dump())
    return evidence_response(lifecycle.register_evidence(evidence))


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: str, lifecycle: LifecycleDep) -> EvidenceResponse:
    return evidence_response(lifecycle.get_entity(Evidence, evidence_id))


@router.get("", response_model=ListResponse[EvidenceResponse])
def list_evidence(
    lifecycle: LifecycleDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[EvidenceResponse]:
    items = [evidence_response(item) for item in lifecycle.list_entities(Evidence)]
    return page(items, limit, offset)
