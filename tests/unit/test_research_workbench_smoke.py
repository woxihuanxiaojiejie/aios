from __future__ import annotations

from fastapi.testclient import TestClient

from aios.api.app import create_app
from aios.storage.memory import InMemoryStorage


def test_research_workbench_required_routes_are_registered() -> None:
    api = TestClient(create_app(storage=InMemoryStorage()))

    evidence = api.get("/api/v1/evidence")
    assert evidence.status_code != 404
    assert evidence.status_code == 200

    watchlist = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN"},
    )
    assert watchlist.status_code != 404
    assert watchlist.status_code == 201
