from __future__ import annotations

from fastapi.testclient import TestClient

from aios.api.app import create_app
from aios.kernel.decision import Decision
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.storage.memory import InMemoryStorage


def client() -> tuple[TestClient, InMemoryStorage]:
    storage = InMemoryStorage()
    return TestClient(create_app(storage=storage)), storage


def test_watchlist_api_create_list_update_archive_restore() -> None:
    api, storage = client()

    created = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": " 600519 ", "market": " cn ", "note": "  policy watch "},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["watchlist_item_id"].startswith("wl_")
    assert body["symbol"] == "600519"
    assert body["market"] == "CN"
    assert body["note"] == "policy watch"
    assert body["status"] == "active"
    assert body["archived_at"] is None
    assert "price" not in body
    assert "bars" not in body
    assert storage.list(Evidence) == []
    assert storage.list(Experiment) == []
    assert storage.list(Decision) == []

    duplicate = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "entity_conflict"

    listed = api.get("/api/v1/research/watchlist").json()
    assert listed["count"] == 1
    assert listed["items"] == [body]

    assert (
        api.get(f"/api/v1/research/watchlist/{body['watchlist_item_id']}").json()[
            "symbol"
        ]
        == "600519"
    )

    patched = api.patch(
        f"/api/v1/research/watchlist/{body['watchlist_item_id']}",
        json={"note": " refreshed "},
    )
    assert patched.status_code == 200
    assert patched.json()["note"] == "refreshed"

    archived = api.post(
        f"/api/v1/research/watchlist/{body['watchlist_item_id']}/archive"
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived_at"] is not None

    assert api.get("/api/v1/research/watchlist").json()["items"] == []
    archived_list = api.get("/api/v1/research/watchlist?status=archived").json()
    assert archived_list["items"][0]["watchlist_item_id"] == body["watchlist_item_id"]

    restored = api.post(
        f"/api/v1/research/watchlist/{body['watchlist_item_id']}/restore"
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"
    assert restored.json()["archived_at"] is None


def test_watchlist_api_filters_missing_and_invalid_requests() -> None:
    api, _storage = client()
    first = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN"},
    ).json()
    api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "0700", "market": "HK"},
    )
    api.post(f"/api/v1/research/watchlist/{first['watchlist_item_id']}/archive")

    assert api.get("/api/v1/research/watchlist?market=hk").json()["count"] == 1
    assert api.get("/api/v1/research/watchlist?symbol=0700").json()["count"] == 1
    assert api.get("/api/v1/research/watchlist?status=archived").json()["count"] == 1

    missing = api.get("/api/v1/research/watchlist/wl_missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "entity_not_found"

    bad_body = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": " ", "market": "CN"},
    )
    assert bad_body.status_code in {400, 422}
    assert "error" in bad_body.json()

    forbidden_patch = api.patch(
        f"/api/v1/research/watchlist/{first['watchlist_item_id']}",
        json={"symbol": "000001", "note": "x"},
    )
    assert forbidden_patch.status_code == 422
