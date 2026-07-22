from __future__ import annotations

from collections.abc import Iterator

import pytest
from alembic import command
from testcontainers.postgres import PostgresContainer
from tests.integration.conftest import alembic_config


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:17-alpine", driver="psycopg").with_env(
        "PGDATA",
        "/tmp/pgdata",
    ) as postgres:
        yield postgres.get_connection_url()


@pytest.fixture()
def migrated_postgres_url(postgres_url: str) -> Iterator[str]:
    config = alembic_config(postgres_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield postgres_url
    command.downgrade(config, "base")
