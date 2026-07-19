from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from aios.adapters.market_data import MarketDataAdapter
from aios.adapters.storage import Storage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def get_storage(request: Request) -> Storage:
    return cast("Storage", request.app.state.storage)


def get_market_data_adapter(request: Request) -> MarketDataAdapter:
    return cast("MarketDataAdapter", request.app.state.market_data_adapter)


def get_lifecycle(
    storage: Annotated[Storage, Depends(get_storage)],
) -> DecisionLifecycleService:
    return DecisionLifecycleService(storage)


LifecycleDep = Annotated[DecisionLifecycleService, Depends(get_lifecycle)]
MarketDataAdapterDep = Annotated[
    MarketDataAdapter,
    Depends(get_market_data_adapter),
]
