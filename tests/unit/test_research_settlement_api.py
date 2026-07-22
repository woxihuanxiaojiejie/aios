from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from tests.unit.test_research_settlement_service import (
    FixtureMarketDataAdapter,
    market_bar,
    seed_finalized_research_decision,
)

from aios.api.app import create_app
from aios.kernel.learning import Learning


def test_research_settlement_api_settles_assembly_and_returns_trace() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    api = TestClient(
        create_app(
            storage=storage,
            market_data_adapter=FixtureMarketDataAdapter(
                [
                    market_bar(decision.created_at.date(), "10.00"),
                    market_bar(
                        decision.valid_until.date() + timedelta(days=1), "10.40"
                    ),
                ]
            ),
        )
    )

    response = api.post(
        f"/api/v1/research/assemblies/{assembly_id}/settlement",
        json={"as_of": (decision.valid_until + timedelta(days=1)).isoformat()},
    )
    duplicate = api.post(
        f"/api/v1/research/assemblies/{assembly_id}/settlement",
        json={"as_of": (decision.valid_until + timedelta(days=2)).isoformat()},
    )

    assert response.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.json() == response.json()
    body = response.json()
    assert body["record"]["assembly_id"] == assembly_id
    assert body["record"]["decision_id"] == decision.decision_id
    assert body["outcome"]["status"] == "settled"
    assert body["evaluation"]["evaluation_rules_version"] == "decision-evaluation-v1"
    assert "supported hypotheses" in body["review"]["review_summary"]
    assert len(body["learnings"]) == 2
    assert len(storage.list(Learning)) == 2


def test_research_settlement_api_rejects_not_ready_assembly() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    api = TestClient(
        create_app(
            storage=storage,
            market_data_adapter=FixtureMarketDataAdapter(
                [
                    market_bar(decision.created_at.date(), "10.00"),
                    market_bar(
                        decision.valid_until.date() + timedelta(days=1), "10.40"
                    ),
                ]
            ),
        )
    )

    response = api.post(
        f"/api/v1/research/assemblies/{assembly_id}/settlement",
        json={"as_of": (decision.valid_until - timedelta(seconds=1)).isoformat()},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state_transition"
