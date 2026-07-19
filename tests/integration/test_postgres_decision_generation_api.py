from __future__ import annotations

from fastapi.testclient import TestClient
from tests.api_helpers import evidence_payload, experiment_payload
from tests.llm_helpers import FakeLLMAdapter

from aios.api.app import create_app
from aios.kernel.decision import Decision
from aios.storage.postgres.generation_records import LLMGenerationRecordStore
from aios.storage.postgres.storage import PostgresStorage


def test_postgres_decision_generation_persists_decision_and_metadata(
    migrated_postgres_url: str,
) -> None:
    api = TestClient(
        create_app(
            storage=PostgresStorage(migrated_postgres_url),
            llm_adapter=FakeLLMAdapter(),
        )
    )
    evidence = api.post("/api/v1/evidence", json=evidence_payload()).json()
    experiment = api.post(
        "/api/v1/experiments",
        json=experiment_payload(
            evidence["evidence_id"],
            model="fake/model",
            prompt_version="decision-v1",
        ),
    ).json()

    response = api.post(
        "/api/v1/decision-generation/generate",
        json={
            "experiment_id": experiment["experiment_id"],
            "symbol": "NVDA",
            "horizon": "1d",
        },
    )

    assert response.status_code == 201
    decision_id = response.json()["decision"]["decision_id"]
    storage = PostgresStorage(migrated_postgres_url)
    assert storage.get(Decision, decision_id).decision_id == decision_id
    record = LLMGenerationRecordStore(migrated_postgres_url).get_by_decision_id(
        decision_id
    )
    assert record is not None
    assert record.provider == "fake"
    assert record.prompt_version == "decision-v1"
