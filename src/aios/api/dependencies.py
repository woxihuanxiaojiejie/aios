from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from aios.adapters.llm import LLMAdapter
from aios.adapters.market_data import MarketDataAdapter
from aios.adapters.storage import Storage
from aios.adapters.vibe_trading import VibeTradingResearchAdapter
from aios.application.brain002 import SkillRegistry
from aios.application.decision_generation import GenerationRecorder
from aios.storage.postgres.evidence_repository import EvidenceRepository
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


def get_vibe_trading_adapter(request: Request) -> VibeTradingResearchAdapter:
    return cast("VibeTradingResearchAdapter", request.app.state.vibe_trading_adapter)


def get_brain_evidence_repository(request: Request) -> EvidenceRepository | None:
    return cast(
        "EvidenceRepository | None",
        request.app.state.brain_evidence_repository,
    )


def get_brain002_registry(request: Request) -> SkillRegistry:
    return cast("SkillRegistry", request.app.state.brain002_registry)


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
StorageDep = Annotated[Storage, Depends(get_storage)]
Brain002RegistryDep = Annotated[SkillRegistry, Depends(get_brain002_registry)]
GenerationRecorderDep = Annotated[
    GenerationRecorder | None,
    Depends(get_generation_recorder),
]
VibeTradingAdapterDep = Annotated[
    VibeTradingResearchAdapter,
    Depends(get_vibe_trading_adapter),
]
BrainEvidenceRepositoryDep = Annotated[
    EvidenceRepository | None,
    Depends(get_brain_evidence_repository),
]
