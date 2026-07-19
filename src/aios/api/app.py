from __future__ import annotations

from fastapi import FastAPI

from aios.adapters.llm import LLMAdapter
from aios.adapters.market_data import MarketDataAdapter
from aios.adapters.storage import Storage
from aios.api.errors import add_exception_handlers
from aios.api.routes import (
    decision_generation,
    decisions,
    evidence,
    experiments,
    health,
    learnings,
    market_data,
    reviews,
)
from aios.application.decision_generation import GenerationRecorder
from aios.integrations.akshare.adapter import AKShareMarketDataAdapter
from aios.integrations.baostock.adapter import BaoStockMarketDataAdapter
from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.storage.postgres import PostgresStorage
from aios.storage.postgres.generation_records import LLMGenerationRecordStore


def create_app(
    storage: Storage | None = None,
    market_data_adapter: MarketDataAdapter | None = None,
    baostock_market_data_adapter: MarketDataAdapter | None = None,
    llm_adapter: LLMAdapter | None = None,
    generation_recorder: GenerationRecorder | None = None,
) -> FastAPI:
    app = FastAPI(title="AIOS", version="0.1.0")
    resolved_storage = storage or PostgresStorage()
    app.state.storage = resolved_storage
    app.state.market_data_adapter = market_data_adapter or AKShareMarketDataAdapter()
    app.state.baostock_market_data_adapter = (
        baostock_market_data_adapter or BaoStockMarketDataAdapter()
    )
    app.state.llm_adapter = llm_adapter or LiteLLMAdapter()
    app.state.generation_recorder = generation_recorder or _generation_recorder(
        resolved_storage
    )
    add_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(evidence.router, prefix="/api/v1")
    app.include_router(experiments.router, prefix="/api/v1")
    app.include_router(decisions.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")
    app.include_router(learnings.router, prefix="/api/v1")
    app.include_router(market_data.router, prefix="/api/v1")
    app.include_router(market_data.baostock_router, prefix="/api/v1")
    app.include_router(decision_generation.router, prefix="/api/v1")
    return app


def create_default_app() -> FastAPI:
    return create_app()


def _generation_recorder(storage: Storage) -> GenerationRecorder | None:
    if isinstance(storage, PostgresStorage):
        return LLMGenerationRecordStore(storage.database_url)
    return None
