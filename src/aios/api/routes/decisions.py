from __future__ import annotations

from fastapi import APIRouter, Query, status

from aios.api.dependencies import LifecycleDep
from aios.api.schemas.common import ListResponse, page
from aios.api.schemas.decision import (
    DecisionCreateRequest,
    DecisionResponse,
    decision_response,
)
from aios.kernel.decision import Decision

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
def create_decision(
    request: DecisionCreateRequest,
    lifecycle: LifecycleDep,
) -> DecisionResponse:
    decision = Decision(**request.model_dump())
    return decision_response(lifecycle.create_decision(decision))


@router.get("/{decision_id}", response_model=DecisionResponse)
def get_decision(decision_id: str, lifecycle: LifecycleDep) -> DecisionResponse:
    return decision_response(lifecycle.get_entity(Decision, decision_id))


@router.get("", response_model=ListResponse[DecisionResponse])
def list_decisions(
    lifecycle: LifecycleDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[DecisionResponse]:
    items = [decision_response(item) for item in lifecycle.list_entities(Decision)]
    return page(items, limit, offset)
