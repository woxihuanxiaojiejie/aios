from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from tests.api_helpers import (
    create_lifecycle,
    decision_payload,
    evidence_payload,
    experiment_payload,
    learning_payload,
    now,
    review_payload,
)

from aios.api.app import create_app
from aios.kernel.base import KernelModel
from aios.kernel.errors import MissingEntityError, StorageOperationError
from aios.storage.memory import InMemoryStorage


def client() -> TestClient:
    return TestClient(create_app(storage=InMemoryStorage()))


class LeakyFailingStorage:
    def save(self, entity: KernelModel) -> None:
        raise StorageOperationError("select * from internal_table")

    def replace(self, entity: KernelModel) -> None:
        raise StorageOperationError("connection=internal")

    def get[EntityT: KernelModel](
        self,
        entity_type: type[EntityT],
        entity_id: str,
    ) -> EntityT:
        raise MissingEntityError(f"{entity_type.__name__} with id {entity_id} missing")

    def list[EntityT: KernelModel](self, entity_type: type[EntityT]) -> list[EntityT]:
        raise StorageOperationError("select * from evidence")

    def exists[EntityT: KernelModel](
        self,
        entity_type: type[EntityT],
        entity_id: str,
    ) -> bool:
        raise StorageOperationError("postgresql internal connection failed")


def test_health_and_openapi() -> None:
    api = client()

    assert api.get("/health").json() == {"status": "ok", "service": "aios"}
    assert api.get("/api/v1/health").json() == {"status": "ok", "service": "aios"}

    schema = api.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/evidence" in schema.json()["paths"]


def test_create_get_and_list_evidence() -> None:
    api = client()
    created = api.post("/api/v1/evidence", json=evidence_payload())

    assert created.status_code == 201
    body = created.json()
    assert body["evidence_id"].startswith("ev_")
    assert "created_at" in body

    assert api.get(f"/api/v1/evidence/{body['evidence_id']}").json() == body
    listed = api.get("/api/v1/evidence?limit=1&offset=0").json()
    assert listed == {"items": [body], "limit": 1, "offset": 0, "count": 1}


def test_evidence_validation_errors() -> None:
    api = client()

    bad_time = api.post(
        "/api/v1/evidence",
        json=evidence_payload(available_at="2026-07-19T07:00:00+00:00"),
    )
    assert bad_time.status_code == 400
    assert bad_time.json()["error"]["code"] == "validation_failed"

    bad_reliability = api.post(
        "/api/v1/evidence",
        json=evidence_payload(reliability=2),
    )
    assert bad_reliability.status_code == 422
    assert "error" in bad_reliability.json()


def test_create_and_complete_experiment() -> None:
    api = client()
    evidence = api.post("/api/v1/evidence", json=evidence_payload()).json()
    created = api.post(
        "/api/v1/experiments",
        json=experiment_payload(evidence["evidence_id"]),
    )

    assert created.status_code == 201
    experiment = created.json()
    assert experiment["status"] == "created"

    completed = api.post(
        f"/api/v1/experiments/{experiment['experiment_id']}/complete",
        json={"finished_at": (now() + timedelta(minutes=10)).isoformat()},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "finished"

    duplicate = api.post(
        f"/api/v1/experiments/{experiment['experiment_id']}/complete",
        json={"finished_at": (now() + timedelta(minutes=11)).isoformat()},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "invalid_state_transition"


def test_experiment_missing_evidence_and_bad_finish_time() -> None:
    api = client()
    missing = api.post(
        "/api/v1/experiments",
        json=experiment_payload("ev_missing"),
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "reference_integrity_error"

    not_found = api.post(
        "/api/v1/experiments/ex_missing/complete",
        json={"finished_at": (now() + timedelta(minutes=10)).isoformat()},
    )
    assert not_found.status_code == 404


def test_create_decision_and_reject_invalid_references() -> None:
    api = client()
    lifecycle = create_lifecycle(api)

    decision = api.get(
        f"/api/v1/decisions/{lifecycle['decision']['decision_id']}"
    ).json()
    assert decision["action"] == "buy"

    missing_experiment = api.post(
        "/api/v1/decisions",
        json=decision_payload("ex_missing", lifecycle["evidence"]["evidence_id"]),
    )
    assert missing_experiment.status_code == 400

    extra_evidence = api.post("/api/v1/evidence", json=evidence_payload()).json()
    not_subset = api.post(
        "/api/v1/decisions",
        json=decision_payload(
            lifecycle["experiment"]["experiment_id"],
            extra_evidence["evidence_id"],
        ),
    )
    assert not_subset.status_code == 400
    assert not_subset.json()["error"]["code"] == "reference_integrity_error"


def test_review_duplicate_conflict() -> None:
    api = client()
    lifecycle = create_lifecycle(api)

    duplicate = api.post(
        "/api/v1/reviews",
        json=review_payload(lifecycle["decision"]["decision_id"]),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "entity_conflict"


def test_learning_approve_reject_and_repeated_approval() -> None:
    api = client()
    lifecycle = create_lifecycle(api)
    learning_id = lifecycle["learning"]["learning_id"]

    assert lifecycle["learning"]["approval_status"] == "pending"

    approved = api.post(f"/api/v1/learnings/{learning_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"

    repeated = api.post(f"/api/v1/learnings/{learning_id}/reject")
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "invalid_state_transition"

    new_learning = api.post(
        "/api/v1/learnings",
        json=learning_payload(lifecycle["review"]["review_id"], target="rule"),
    ).json()
    rejected = api.post(f"/api/v1/learnings/{new_learning['learning_id']}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["approval_status"] == "rejected"


def test_learning_rejects_equal_before_after() -> None:
    api = client()
    lifecycle = create_lifecycle(api)
    response = api.post(
        "/api/v1/learnings",
        json=learning_payload(lifecycle["review"]["review_id"], after={"weight": 0.4}),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"


def test_missing_resource_pagination_and_error_format() -> None:
    api = client()

    missing = api.get("/api/v1/evidence/ev_missing")
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {
            "code": "entity_not_found",
            "message": "Evidence with id ev_missing does not exist",
            "details": {},
        }
    }

    bad_page = api.get("/api/v1/evidence?limit=201&offset=-1")
    assert bad_page.status_code == 422
    assert "error" in bad_page.json()


def test_request_datetime_must_have_timezone() -> None:
    api = client()
    response = api.post(
        "/api/v1/evidence",
        json=evidence_payload(published_at=now().replace(tzinfo=None).isoformat()),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"


def test_storage_errors_do_not_leak_internal_details() -> None:
    api = TestClient(create_app(storage=LeakyFailingStorage()))

    response = api.get("/api/v1/evidence")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["message"] == "Storage operation failed"
    assert "internal" not in str(body).lower()
    assert "select" not in str(body).lower()
