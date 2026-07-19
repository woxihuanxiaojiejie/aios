from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient


def now() -> datetime:
    return datetime(2026, 7, 19, 8, 0, tzinfo=UTC)


def evidence_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidence_type": "filing",
        "source": "company-report",
        "symbols": ["NVDA"],
        "published_at": now().isoformat(),
        "available_at": (now() + timedelta(minutes=1)).isoformat(),
        "summary": "updated guidance",
        "reliability": 0.85,
        "content_hash": "hash-guidance",
        "metadata": {"form": "10-Q"},
    }
    payload.update(overrides)
    return payload


def experiment_payload(evidence_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "guidance-check",
        "model": "model-v1",
        "prompt_version": "prompt-v1",
        "agent_config_version": "agent-v1",
        "dataset_snapshot": "snapshot-v1",
        "evidence_ids": [evidence_id],
        "parameters": {"temperature": 0},
        "started_at": (now() + timedelta(minutes=2)).isoformat(),
    }
    payload.update(overrides)
    return payload


def decision_payload(
    experiment_id: str,
    evidence_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "experiment_id": experiment_id,
        "symbol": "NVDA",
        "action": "buy",
        "horizon": "5d",
        "confidence": 0.72,
        "expected_return": 0.04,
        "max_expected_loss": 0.02,
        "evidence_ids": [evidence_id],
        "reasoning_summary": "guidance improved while risk stayed bounded",
        "valid_until": (now() + timedelta(days=5)).isoformat(),
    }
    payload.update(overrides)
    return payload


def review_payload(decision_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "decision_id": decision_id,
        "actual_return": 0.03,
        "direction_correct": True,
        "risk_limit_breached": False,
        "outcome": "profit",
        "cause_tags": ["guidance"],
        "review_summary": "decision matched thesis",
    }
    payload.update(overrides)
    return payload


def learning_payload(review_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "review_id": review_id,
        "learning_type": "agent_weight_update",
        "target": "guidance-signal-weight",
        "before": {"weight": 0.4},
        "after": {"weight": 0.45},
        "reason": "reviewed profitable decision",
    }
    payload.update(overrides)
    return payload


def create_lifecycle(client: TestClient) -> dict[str, dict[str, Any]]:
    evidence = client.post("/api/v1/evidence", json=evidence_payload()).json()
    experiment = client.post(
        "/api/v1/experiments",
        json=experiment_payload(evidence["evidence_id"]),
    ).json()
    decision = client.post(
        "/api/v1/decisions",
        json=decision_payload(experiment["experiment_id"], evidence["evidence_id"]),
    ).json()
    review = client.post(
        "/api/v1/reviews",
        json=review_payload(decision["decision_id"]),
    ).json()
    learning = client.post(
        "/api/v1/learnings",
        json=learning_payload(review["review_id"]),
    ).json()
    return {
        "evidence": evidence,
        "experiment": experiment,
        "decision": decision,
        "review": review,
        "learning": learning,
    }
