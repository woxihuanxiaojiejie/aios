from __future__ import annotations

from fastapi import APIRouter, Query, status

from aios.api.dependencies import LifecycleDep
from aios.api.schemas.business_views import (
    LearningDetailResponse,
    learning_detail_response,
)
from aios.api.schemas.common import ListResponse, page
from aios.api.schemas.learning import (
    LearningCreateRequest,
    LearningResponse,
    learning_response,
)
from aios.application.business_views import BusinessViewService
from aios.application.test_data_filter import should_include_test_data
from aios.kernel.learning import Learning

router = APIRouter(prefix="/learnings", tags=["learnings"])


@router.post("", response_model=LearningResponse, status_code=status.HTTP_201_CREATED)
def create_learning(
    request: LearningCreateRequest,
    lifecycle: LifecycleDep,
) -> LearningResponse:
    learning = Learning(**request.model_dump())
    return learning_response(lifecycle.propose_learning(learning))


@router.get("/{learning_id}/detail", response_model=LearningDetailResponse)
def get_learning_detail(
    learning_id: str,
    lifecycle: LifecycleDep,
) -> LearningDetailResponse:
    return learning_detail_response(
        BusinessViewService(lifecycle.storage).learning_detail(learning_id)
    )


@router.get("/{learning_id}", response_model=LearningResponse)
def get_learning(learning_id: str, lifecycle: LifecycleDep) -> LearningResponse:
    return learning_response(lifecycle.get_entity(Learning, learning_id))


@router.get("", response_model=ListResponse[LearningResponse])
def list_learnings(
    lifecycle: LifecycleDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    include_test_data: bool = Query(default=False),
) -> ListResponse[LearningResponse]:
    items = [
        learning_response(item)
        for item in lifecycle.list_entities(Learning)
        if should_include_test_data(item, include_test_data=include_test_data)
    ]
    return page(items, limit, offset)


@router.post("/{learning_id}/approve", response_model=LearningResponse)
def approve_learning(learning_id: str, lifecycle: LifecycleDep) -> LearningResponse:
    return learning_response(lifecycle.approve_learning(learning_id))


@router.post("/{learning_id}/reject", response_model=LearningResponse)
def reject_learning(learning_id: str, lifecycle: LifecycleDep) -> LearningResponse:
    return learning_response(lifecycle.reject_learning(learning_id))


@router.post("/{learning_id}/defer", response_model=LearningResponse)
def defer_learning(learning_id: str, lifecycle: LifecycleDep) -> LearningResponse:
    return learning_response(lifecycle.defer_learning(learning_id))
