from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from aios.adapters.storage import Storage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def get_storage(request: Request) -> Storage:
    return cast("Storage", request.app.state.storage)


def get_lifecycle(
    storage: Annotated[Storage, Depends(get_storage)],
) -> DecisionLifecycleService:
    return DecisionLifecycleService(storage)


LifecycleDep = Annotated[DecisionLifecycleService, Depends(get_lifecycle)]
