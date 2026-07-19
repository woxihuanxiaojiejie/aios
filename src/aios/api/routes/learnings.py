from __future__ import annotations

from fastapi import APIRouter, Query, status

from aios.api.dependencies import LifecycleDep
from aios.api.schemas.common import ListResponse, page
from aios.api.schemas.learning import (
    LearningCreateRequest,
    LearningResponse,
    learning_response,
)
from aios.kernel.learning import Learning

router = APIRouter(prefix="/learnings", tags=["learnings"])


@router.post("", response_model=LearningResponse, status_code=status.HTTP_201_CREATED)
def create_learning(
    request: LearningCreateRequest,
    lifecycle: LifecycleDep,
) -> LearningResponse:
    learning = Learning(**request.model_dump())
    return learning_response(lifecycle.propose_learning(learning))


@router.get("/{learning_id}", response_model=LearningResponse)
def get_learning(learning_id: str, lifecycle: LifecycleDep) -> LearningResponse:
    return learning_response(lifecycle.get_entity(Learning, learning_id))


@router.get("", response_model=ListResponse[LearningResponse])
def list_learnings(
    lifecycle: LifecycleDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[LearningResponse]:
    items = [learning_response(item) for item in lifecycle.list_entities(Learning)]
    return page(items, limit, offset)


@router.post("/{learning_id}/approve", response_model=LearningResponse)
def approve_learning(learning_id: str, lifecycle: LifecycleDep) -> LearningResponse:
    return learning_response(lifecycle.approve_learning(learning_id))


@router.post("/{learning_id}/reject", response_model=LearningResponse)
def reject_learning(learning_id: str, lifecycle: LifecycleDep) -> LearningResponse:
    return learning_response(lifecycle.reject_learning(learning_id))
