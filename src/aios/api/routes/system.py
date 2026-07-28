from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, Request

from aios.api.dependencies import StorageDep
from aios.application.system_status import SystemStatusService, SystemStatusSummary

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusSummary)
def get_system_status(
    request: Request,
    storage: StorageDep,
) -> SystemStatusSummary:
    started_at = cast(
        "datetime | None",
        getattr(request.app.state, "started_at", None),
    )
    return SystemStatusService(
        storage=storage,
        started_at=started_at,
    ).build(as_of=datetime.now(UTC))
