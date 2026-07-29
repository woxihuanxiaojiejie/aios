from __future__ import annotations

from fastapi.testclient import TestClient
from tests.factories import make_decision, make_evidence, make_experiment

from aios.api.app import create_app
from aios.kernel.enums import DecisionDirection
from aios.storage.memory import InMemoryStorage


def test_trade_plan_api_creates_and_gets_plan() -> None:
    storage = InMemoryStorage()
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    decision = make_decision(experiment.experiment_id, evidence.evidence_id)
    decision = decision.model_copy(
        update={
            "research_session_id": "rs_00000000-0000-0000-0000-000000000001",
            "direction": DecisionDirection.BULLISH,
            "target_range": (12.0, 13.0),
            "entry_conditions": ("close above 10",),
            "stop_loss": 9.25,
            "invalidation_conditions": ("close below 9.25",),
            "position_suggestion": 0.25,
            "planned_settlement_at": decision.valid_until,
        }
    )
    storage.save(evidence)
    storage.save(experiment)
    storage.save(decision)
    api = TestClient(create_app(storage=storage))

    created = api.post(f"/api/v1/research/decisions/{decision.decision_id}/trade-plan")

    assert created.status_code == 201
    created_body = created.json()
    assert created_body["decision_id"] == decision.decision_id
    assert created_body["status"] == "ready"
    assert created_body["target"] == [12.0, 13.0]

    fetched = api.get(f"/api/v1/research/trade-plans/{created_body['trade_plan_id']}")

    assert fetched.status_code == 200
    assert fetched.json() == created_body


def test_trade_plan_api_repeated_create_returns_existing_plan() -> None:
    storage = InMemoryStorage()
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    decision = make_decision(experiment.experiment_id, evidence.evidence_id)
    decision = decision.model_copy(
        update={
            "research_session_id": "rs_00000000-0000-0000-0000-000000000001",
            "direction": DecisionDirection.BULLISH,
            "target_range": (12.0, 13.0),
            "entry_conditions": ("close above 10",),
            "stop_loss": 9.25,
            "invalidation_conditions": ("close below 9.25",),
            "position_suggestion": 0.25,
            "planned_settlement_at": decision.valid_until,
        }
    )
    storage.save(evidence)
    storage.save(experiment)
    storage.save(decision)
    api = TestClient(create_app(storage=storage))

    first = api.post(f"/api/v1/research/decisions/{decision.decision_id}/trade-plan")
    second = api.post(f"/api/v1/research/decisions/{decision.decision_id}/trade-plan")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
