from __future__ import annotations

from fastapi import FastAPI

from aios.adapters.storage import Storage
from aios.api.errors import add_exception_handlers
from aios.api.routes import decisions, evidence, experiments, health, learnings, reviews
from aios.storage.postgres import PostgresStorage


def create_app(storage: Storage | None = None) -> FastAPI:
    app = FastAPI(title="AIOS", version="0.1.0")
    app.state.storage = storage or PostgresStorage()
    add_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(evidence.router, prefix="/api/v1")
    app.include_router(experiments.router, prefix="/api/v1")
    app.include_router(decisions.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")
    app.include_router(learnings.router, prefix="/api/v1")
    return app


def create_default_app() -> FastAPI:
    return create_app()
