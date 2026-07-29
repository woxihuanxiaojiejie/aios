from __future__ import annotations

from datetime import timedelta

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


def create_session(api: TestClient, storage: InMemoryStorage) -> tuple[str, str]:
    watchlist = api.post(
        "/api/v1/research/watchlist",
        json={"symbol": "600519", "market": "CN"},
    ).json()
    evidence = make_evidence().model_copy(update={"symbols": ("600519",)})
    storage.save(evidence)
    session = api.post(
        "/api/v1/research/sessions",
        json={
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": (fixed_now() + timedelta(hours=1)).isoformat(),
            "evidence_ids": [evidence.evidence_id],
        },
    ).json()
    return session["research_session_id"], evidence.evidence_id


def test_agent_report_api_create_list_get_archive() -> None:
    api, storage = client()
    session_id, evidence_id = create_session(api, storage)

    created = api.post(
        f"/api/v1/research/sessions/{session_id}/agent-reports",
        json={
            "role": "technical",
            "summary": "trend",
            "stance": "watch",
            "confidence": 0.7,
            "evidence_ids": [evidence_id],
            "source": "manual",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["report_id"].startswith("ar_")
    assert body["research_session_id"] == session_id
    assert body["role"] == "technical"
    assert body["status"] == "active"
    assert body["evidence_ids"] == [evidence_id]
    assert "price" not in body
    assert "bars" not in body
    assert storage.list(Experiment) == []
    assert storage.list(Decision) == []

    duplicate = api.post(
        f"/api/v1/research/sessions/{session_id}/agent-reports",
        json={
            "role": "technical",
            "summary": "again",
            "stance": "watch",
            "confidence": 0.6,
            "evidence_ids": [],
            "source": "manual",
        },
    )
    assert duplicate.status_code == 409

    assert api.get(f"/api/v1/research/sessions/{session_id}/agent-reports").json()[
        "items"
    ] == [body]
    assert api.get(f"/api/v1/research/agent-reports/{body['report_id']}").json() == body

    archived = api.post(f"/api/v1/research/agent-reports/{body['report_id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived_at"] is not None


def test_hypothesis_api_create_list_get_and_update_status() -> None:
    api, storage = client()
    session_id, evidence_id = create_session(api, storage)
    report = api.post(
        f"/api/v1/research/sessions/{session_id}/agent-reports",
        json={
            "role": "news",
            "summary": "news",
            "stance": "watch",
            "confidence": 0.6,
            "evidence_ids": [evidence_id],
            "source": "manual",
        },
    ).json()

    created = api.post(
        f"/api/v1/research/sessions/{session_id}/hypotheses",
        json={
            "statement": "Demand improves",
            "rationale": "report",
            "direction": "bullish",
            "horizon_days": 3,
            "confidence": 0.55,
            "supporting_report_ids": [report["report_id"]],
            "supporting_evidence_ids": [evidence_id],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["hypothesis_id"].startswith("hp_")
    assert body["status"] == "proposed"
    assert body["supporting_report_ids"] == [report["report_id"]]
    assert storage.list(Evidence)
    assert storage.list(Experiment) == []
    assert storage.list(Decision) == []

    assert api.get(f"/api/v1/research/sessions/{session_id}/hypotheses").json()[
        "items"
    ] == [body]
    assert (
        api.get(f"/api/v1/research/hypotheses/{body['hypothesis_id']}").json() == body
    )

    updated = api.post(
        f"/api/v1/research/hypotheses/{body['hypothesis_id']}/status",
        json={"status": "validated"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "validated"


def test_research_record_api_rejects_bad_references() -> None:
    api, storage = client()
    session_id, _evidence_id = create_session(api, storage)

    report = api.post(
        f"/api/v1/research/sessions/{session_id}/agent-reports",
        json={
            "role": "capital_flow",
            "summary": "capital",
            "stance": "neutral",
            "confidence": 0.6,
            "evidence_ids": ["ev_missing"],
            "source": "manual",
        },
    )
    assert report.status_code == 400
    assert report.json()["error"]["code"] == "reference_integrity_error"

    valid_report = api.post(
        f"/api/v1/research/sessions/{session_id}/agent-reports",
        json={
            "role": "capital_flow",
            "summary": "capital",
            "stance": "neutral",
            "confidence": 0.6,
            "evidence_ids": [],
            "source": "manual",
        },
    ).json()

    hypothesis = api.post(
        f"/api/v1/research/sessions/{session_id}/hypotheses",
        json={
            "statement": "x",
            "rationale": "x",
            "direction": "bullish",
            "horizon_days": 7,
            "confidence": 0.5,
            "supporting_report_ids": [valid_report["report_id"]],
            "supporting_evidence_ids": [],
        },
    )
    assert hypothesis.status_code == 409
    assert hypothesis.json()["error"]["code"] == "invalid_state_transition"
