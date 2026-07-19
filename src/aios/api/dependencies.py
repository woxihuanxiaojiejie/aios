from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from aios.adapters.llm import LLMAdapter
from aios.adapters.market_data import MarketDataAdapter
from aios.adapters.storage import Storage
from aios.application.decision_generation import GenerationRecorder
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def get_storage(request: Request) -> Storage:
    return cast("Storage", request.app.state.storage)


def get_market_data_adapter(request: Request) -> MarketDataAdapter:
    return cast("MarketDataAdapter", request.app.state.market_data_adapter)


def get_baostock_market_data_adapter(request: Request) -> MarketDataAdapter:
    return cast("MarketDataAdapter", request.app.state.baostock_market_data_adapter)


def get_llm_adapter(request: Request) -> LLMAdapter:
    return cast("LLMAdapter", request.app.state.llm_adapter)


def get_generation_recorder(request: Request) -> GenerationRecorder | None:
    return cast("GenerationRecorder | None", request.app.state.generation_recorder)


def get_lifecycle(
    storage: Annotated[Storage, Depends(get_storage)],
) -> DecisionLifecycleService:
    return DecisionLifecycleService(storage)


LifecycleDep = Annotated[DecisionLifecycleService, Depends(get_lifecycle)]
MarketDataAdapterDep = Annotated[
    MarketDataAdapter,
    Depends(get_market_data_adapter),
]
BaoStockMarketDataAdapterDep = Annotated[
    MarketDataAdapter,
    Depends(get_baostock_market_data_adapter),
]
LLMAdapterDep = Annotated[LLMAdapter, Depends(get_llm_adapter)]
GenerationRecorderDep = Annotated[
    GenerationRecorder | None,
    Depends(get_generation_recorder),
]
