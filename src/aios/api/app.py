from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aios.adapters.llm import LLMAdapter
from aios.adapters.market_data import MarketDataAdapter
from aios.adapters.storage import Storage
from aios.adapters.vibe_trading import VibeTradingResearchAdapter
from aios.api.errors import add_exception_handlers
from aios.api.routes import (
    brain_evidence,
    decision_generation,
    decisions,
    evidence,
    experiments,
    health,
    learnings,
    market_data,
    research,
    reviews,
)
from aios.application.decision_generation import GenerationRecorder
from aios.integrations.akshare.adapter import AKShareMarketDataAdapter
from aios.integrations.baostock.adapter import BaoStockMarketDataAdapter
from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.storage.postgres import PostgresStorage
from aios.storage.postgres.evidence_repository import EvidenceRepository
from aios.storage.postgres.generation_records import LLMGenerationRecordStore
from aios.vibe_trading.adapter import VibeTradingAdapter


def create_app(
    storage: Storage | None = None,
    market_data_adapter: MarketDataAdapter | None = None,
    baostock_market_data_adapter: MarketDataAdapter | None = None,
    llm_adapter: LLMAdapter | None = None,
    generation_recorder: GenerationRecorder | None = None,
    vibe_trading_adapter: VibeTradingResearchAdapter | None = None,
    evidence_repository: EvidenceRepository | None = None,
) -> FastAPI:
    load_dotenv(override=True)
    app = FastAPI(title="AIOS", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    resolved_storage = storage or PostgresStorage()
    app.state.storage = resolved_storage
    app.state.brain_evidence_repository = (
        evidence_repository or _brain_evidence_repository(resolved_storage)
    )
    app.state.market_data_adapter = market_data_adapter or AKShareMarketDataAdapter()
    app.state.baostock_market_data_adapter = (
        baostock_market_data_adapter or BaoStockMarketDataAdapter()
    )
    app.state.llm_adapter = llm_adapter or LiteLLMAdapter()
    app.state.generation_recorder = generation_recorder or _generation_recorder(
        resolved_storage
    )
    app.state.vibe_trading_adapter = vibe_trading_adapter or VibeTradingAdapter()
    add_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(evidence.router, prefix="/api/v1")
    app.include_router(brain_evidence.router, prefix="/api/v1")
    app.include_router(experiments.router, prefix="/api/v1")
    app.include_router(decisions.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")
    app.include_router(learnings.router, prefix="/api/v1")
    app.include_router(market_data.router, prefix="/api/v1")
    app.include_router(market_data.baostock_router, prefix="/api/v1")
    app.include_router(decision_generation.router, prefix="/api/v1")
    app.include_router(research.router, prefix="/api/v1")
    return app


def create_default_app() -> FastAPI:
    return create_app()


def _generation_recorder(storage: Storage) -> GenerationRecorder | None:
    if isinstance(storage, PostgresStorage):
        return LLMGenerationRecordStore(storage.database_url)
    return None


def _brain_evidence_repository(storage: Storage) -> EvidenceRepository | None:
    if isinstance(storage, PostgresStorage):
        return EvidenceRepository(storage.database_url)
    return None


def _cors_origins() -> list[str]:
    configured = os.getenv("AIOS_CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ]
