from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from tests.factories import fixed_now, make_evidence

from aios.api.app import create_app
from aios.kernel.decision import Decision
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.storage.memory import InMemoryStorage


def client() -> tuple[TestClient, InMemoryStorage]:
    storage = InMemoryStorage()
    return TestClient(create_app(storage=storage)), storage


def test_research_session_api_create_list_get_and_cancel() -> None:
    api, storage = client()
    watchlist = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN", "note": "policy watch"},
    ).json()
    evidence = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000201",
    ).model_copy(update={"symbols": ("600519",)})
    storage.save(evidence)
    as_of = (fixed_now() + timedelta(hours=1)).isoformat().replace("+00:00", "Z")

    created = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": as_of,
            "evidence_ids": [evidence.evidence_id],
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["research_session_id"].startswith("rs_")
    assert body["scope"]["watchlist_item_id"] == watchlist["watchlist_item_id"]
    assert body["scope"]["symbol"] == "600519"
    assert body["scope"]["market"] == "CN"
    assert body["scope"]["watchlist_note_snapshot"] == "policy watch"
    assert body["scope"]["horizon_days"] == 3
    assert body["status"] == "evidence_ready"
    assert body["evidence_ids"] == [evidence.evidence_id]
    assert body["experiment_id"] is None
    assert body["cancelled_at"] is None
    assert "price" not in body
    assert "bars" not in body
    assert storage.list(Experiment) == []
    assert storage.list(Decision) == []

    duplicate = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": as_of,
            "evidence_ids": [],
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "entity_conflict"

    listed = api.get("/api/v1/research/sessions").json()
    assert listed["count"] == 1
    assert listed["items"] == [body]
    assert api.get("/api/v1/research/sessions?market=cn").json()["count"] == 1
    assert api.get("/api/v1/research/sessions?symbol=600519").json()["count"] == 1
    assert api.get("/api/v1/research/sessions?horizon_days=3").json()["count"] == 1
    assert (
        api.get("/api/v1/research/sessions?status=evidence_ready").json()["count"] == 1
    )

    fetched = api.get(f"/api/v1/research/sessions/{body['research_session_id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body

    cancelled = api.post(
        f"/api/v1/research/sessions/{body['research_session_id']}/cancel"
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None

    recreated = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": as_of,
            "evidence_ids": [],
        },
    )
    assert recreated.status_code == 201
    assert recreated.json()["status"] == "created"


def test_research_session_api_errors_and_forbidden_fields() -> None:
    api, storage = client()
    watchlist = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN"},
    ).json()
    as_of = datetime(2026, 7, 22, 6, 0, tzinfo=UTC)
    future = Evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000202",
        evidence_type="filing",
        source="company-report",
        symbols=("600519",),
        published_at=as_of + timedelta(minutes=1),
        available_at=as_of + timedelta(minutes=2),
        summary="future",
        reliability=0.8,
        content_hash="future",
    )
    storage.save(future)

    bad_horizon = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 5,
            "as_of": as_of.isoformat(),
            "evidence_ids": [],
        },
    )
    assert bad_horizon.status_code in {400, 422}

    future_evidence = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": as_of.isoformat(),
            "evidence_ids": [future.evidence_id],
        },
    )
    assert future_evidence.status_code == 400
    assert future_evidence.json()["error"]["code"] == "reference_integrity_error"

    forbidden = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": as_of.isoformat(),
            "evidence_ids": [],
            "symbol": "000001",
            "status": "created",
        },
    )
    assert forbidden.status_code == 422

    missing = api.get("/api/v1/research/sessions/rs_missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "entity_not_found"

    api.post(f"/api/v1/research/watchlist/{watchlist['watchlist_item_id']}/archive")
    archived = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": as_of.isoformat(),
            "evidence_ids": [],
        },
    )
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "invalid_state_transition"
