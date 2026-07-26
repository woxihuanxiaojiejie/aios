from __future__ import annotations

from fastapi.testclient import TestClient
from tests.api_helpers import evidence_payload

from aios.api.app import create_app
from aios.storage.postgres import PostgresStorage


def _client(database_url: str) -> TestClient:
    return TestClient(create_app(storage=PostgresStorage(database_url)))


def test_research_workbench_watchlist_persists_across_app_recreation(
    migrated_postgres_url: str,
) -> None:
    api = _client(migrated_postgres_url)

    created = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": " 600519 ", "market": " cn ", "note": "  policy watch "},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["symbol"] == "600519"
    assert body["market"] == "CN"
    assert body["note"] == "policy watch"
    assert body["status"] == "active"

    duplicate = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "entity_conflict"

    listed = api.get("/api/v1/research/watchlist")
    assert listed.status_code == 200
    assert listed.json()["items"] == [body]

    fresh_api = _client(migrated_postgres_url)
    persisted = fresh_api.get("/api/v1/research/watchlist")
    assert persisted.status_code == 200
    assert persisted.json()["items"] == [body]

    patched = fresh_api.patch(
        f"/api/v1/research/watchlist/{body['watchlist_item_id']}",
        json={"note": " refreshed "},
    )
    assert patched.status_code == 200
    assert patched.json()["note"] == "refreshed"

    archived = fresh_api.post(
        f"/api/v1/research/watchlist/{body['watchlist_item_id']}/archive"
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    replacement = fresh_api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN"},
    )
    assert replacement.status_code == 201

    restore_conflict = fresh_api.post(
        f"/api/v1/research/watchlist/{body['watchlist_item_id']}/restore"
    )
    assert restore_conflict.status_code == 409
    assert restore_conflict.json()["error"]["code"] == "entity_conflict"


def test_research_workbench_evidence_persists_across_app_recreation(
    migrated_postgres_url: str,
) -> None:
    api = _client(migrated_postgres_url)
    created = api.post(
        "/api/v1/evidence",
        json=evidence_payload(content_hash="research-workbench-evidence-hash"),
    )
    assert created.status_code == 201
    body = created.json()

    fresh_api = _client(migrated_postgres_url)
    listed = fresh_api.get("/api/v1/evidence")
    assert listed.status_code == 200
    assert listed.json()["items"] == [body]

    fetched = fresh_api.get(f"/api/v1/evidence/{body['evidence_id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body
