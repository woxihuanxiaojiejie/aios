from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from aios.kernel.errors import DatabaseConfigurationError

DATABASE_URL_ENV = "AIOS_DATABASE_URL"


def get_database_url() -> str:
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        msg = f"{DATABASE_URL_ENV} is required for PostgreSQL storage"
        raise DatabaseConfigurationError(msg)
    return database_url


def make_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or get_database_url())


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
