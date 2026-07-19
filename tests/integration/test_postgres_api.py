from fastapi.testclient import TestClient
from tests.api_helpers import (
    create_lifecycle,
)

from aios.api.app import create_app
from aios.storage.postgres import PostgresStorage


def test_postgres_api_lifecycle_persists_after_app_recreation(
    migrated_postgres_url: str,
) -> None:
    api = TestClient(create_app(storage=PostgresStorage(migrated_postgres_url)))
    lifecycle = create_lifecycle(api)

    approved = api.post(
        f"/api/v1/learnings/{lifecycle['learning']['learning_id']}/approve"
    )
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"

    fresh_api = TestClient(create_app(storage=PostgresStorage(migrated_postgres_url)))
    persisted = fresh_api.get(
        f"/api/v1/learnings/{lifecycle['learning']['learning_id']}"
    )
    assert persisted.status_code == 200
    assert persisted.json()["approval_status"] == "approved"
