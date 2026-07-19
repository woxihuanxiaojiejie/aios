from __future__ import annotations

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:17-alpine", driver="psycopg").with_env(
        "PGDATA",
        "/tmp/pgdata",
    ) as postgres:
        yield postgres.get_connection_url()


def alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture()
def migrated_postgres_url(postgres_url: str) -> Iterator[str]:
    config = alembic_config(postgres_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield postgres_url
    command.downgrade(config, "base")


def table_count(database_url: str, table_name: str) -> int:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            result = connection.execute(text(f"select count(*) from {table_name}"))
            return int(result.scalar_one())
    finally:
        engine.dispose()
