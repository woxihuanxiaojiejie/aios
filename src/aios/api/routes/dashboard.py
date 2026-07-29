from __future__ import annotations

from fastapi import APIRouter, Query

from aios.api.dependencies import LifecycleDep
from aios.api.schemas.dashboard import (
    DashboardSummaryResponse,
    dashboard_summary_response,
)
from aios.application.dashboard import DashboardSummaryService
from aios.kernel.base import utc_now

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    lifecycle: LifecycleDep,
    include_test_data: bool = Query(default=False),
) -> DashboardSummaryResponse:
    return dashboard_summary_response(
        DashboardSummaryService(lifecycle.storage).summary(
            generated_at=utc_now(),
            include_test_data=include_test_data,
        )
    )
