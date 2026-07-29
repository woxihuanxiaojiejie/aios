from __future__ import annotations

from fastapi import APIRouter, Query, status

from aios.api.dependencies import LifecycleDep
from aios.api.schemas.business_views import (
    BusinessListResponse,
    ReviewSummaryResponse,
    review_summary_list_response,
)
from aios.api.schemas.common import ListResponse, page
from aios.api.schemas.review import (
    ReviewCreateRequest,
    ReviewResponse,
    review_response,
)
from aios.application.business_views import BusinessViewService
from aios.kernel.review import Review

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    request: ReviewCreateRequest,
    lifecycle: LifecycleDep,
) -> ReviewResponse:
    review = Review(**request.model_dump())
    return review_response(lifecycle.create_review(review))


@router.get("/summary", response_model=BusinessListResponse[ReviewSummaryResponse])
def list_review_summary(
    lifecycle: LifecycleDep,
    page_number: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    include_test_data: bool = False,
) -> BusinessListResponse[ReviewSummaryResponse]:
    return review_summary_list_response(
        BusinessViewService(lifecycle.storage).reviews_summary(
            page=page_number,
            page_size=page_size,
            include_test_data=include_test_data,
        )
    )


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str, lifecycle: LifecycleDep) -> ReviewResponse:
    return review_response(lifecycle.get_entity(Review, review_id))


@router.get("", response_model=ListResponse[ReviewResponse])
def list_reviews(
    lifecycle: LifecycleDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[ReviewResponse]:
    items = [review_response(item) for item in lifecycle.list_entities(Review)]
    return page(items, limit, offset)
