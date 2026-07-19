from __future__ import annotations

from fastapi.testclient import TestClient
from tests.api_helpers import evidence_payload, experiment_payload
from tests.llm_helpers import FakeLLMAdapter

from aios.api.app import create_app
from aios.integrations.litellm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
from aios.storage.memory import InMemoryStorage


def client(llm: FakeLLMAdapter | None = None) -> TestClient:
    return TestClient(
        create_app(storage=InMemoryStorage(), llm_adapter=llm or FakeLLMAdapter())
    )


def seed(api: TestClient) -> tuple[str, str]:
    evidence = api.post("/api/v1/evidence", json=evidence_payload()).json()
    experiment = api.post(
        "/api/v1/experiments",
        json=experiment_payload(
            evidence["evidence_id"],
            model="fake/model",
            prompt_version="decision-v1",
        ),
    ).json()
    return evidence["evidence_id"], experiment["experiment_id"]


def test_decision_generation_api_success() -> None:
    api = client()
    _evidence_id, experiment_id = seed(api)

    response = api.post(
        "/api/v1/decision-generation/generate",
        json={"experiment_id": experiment_id, "symbol": "NVDA", "horizon": "1d"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"]["decision_id"].startswith("dc_")
    assert body["decision"]["action"] == "hold"
    assert body["generation"]["provider"] == "fake"
    assert body["generation"]["prompt_version"] == "decision-v1"
    assert "prompt" not in body["generation"]


def test_decision_generation_api_request_validation() -> None:
    response = client().post("/api/v1/decision-generation/generate", json={})

    assert response.status_code == 422


def test_decision_generation_api_missing_experiment() -> None:
    response = client().post(
        "/api/v1/decision-generation/generate",
        json={"experiment_id": "ex_missing", "symbol": "NVDA", "horizon": "1d"},
    )

    assert response.status_code == 404


def test_decision_generation_api_maps_llm_errors() -> None:
    cases = [
        (LLMConfigurationError("missing key"), 503),
        (LLMAuthenticationError("bad api key secret"), 503),
        (LLMRateLimitError("limited"), 503),
        (LLMTimeoutError("timeout"), 504),
        (LLMStructuredOutputError("raw provider payload secret"), 502),
    ]

    for error, status_code in cases:
        api = client(FakeLLMAdapter(error=error))
        _evidence_id, experiment_id = seed(api)
        response = api.post(
            "/api/v1/decision-generation/generate",
            json={"experiment_id": experiment_id, "symbol": "NVDA", "horizon": "1d"},
        )
        assert response.status_code == status_code
        assert "secret" not in response.json()["error"]["message"]


def test_decision_generation_openapi_generates() -> None:
    schema = client().app.openapi()

    assert "/api/v1/decision-generation/generate" in schema["paths"]
