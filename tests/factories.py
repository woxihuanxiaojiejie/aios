from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from aios.kernel.decision import Decision
from aios.kernel.enums import Action
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review


def fixed_now() -> datetime:
    return datetime(2026, 7, 19, 8, 0, tzinfo=UTC)


def make_evidence(
    *,
    evidence_id: str = "ev_00000000-0000-0000-0000-000000000001",
    summary: str = "updated guidance",
    created_at: datetime | None = None,
) -> Evidence:
    moment = fixed_now()
    return Evidence(
        evidence_id=evidence_id,
        evidence_type="filing",
        source="company-report",
        symbols=["NVDA", "MSFT"],
        published_at=moment,
        available_at=moment + timedelta(minutes=2),
        summary=summary,
        reliability=0.85,
        content_hash=f"hash-{evidence_id}",
        metadata={"form": "10-Q", "nested": {"page": 3}},
        created_at=created_at or moment,
    )


def make_experiment(
    evidence_id: str,
    *,
    experiment_id: str = "ex_00000000-0000-0000-0000-000000000001",
    model: str = "model-v1",
    prompt_version: str = "prompt-v1",
    parameters: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> Experiment:
    moment = fixed_now()
    return Experiment(
        experiment_id=experiment_id,
        name="guidance-check",
        model=model,
        prompt_version=prompt_version,
        agent_config_version="agent-v1",
        dataset_snapshot="snapshot-v1",
        evidence_ids=[evidence_id],
        parameters=parameters or {"temperature": 0, "weights": [1, 2]},
        started_at=moment + timedelta(minutes=3),
        finished_at=moment + timedelta(minutes=4),
        created_at=created_at or moment,
    )


def make_decision(
    experiment_id: str,
    evidence_id: str,
    *,
    decision_id: str = "dc_00000000-0000-0000-0000-000000000001",
    created_at: datetime | None = None,
) -> Decision:
    moment = fixed_now()
    created = created_at or moment + timedelta(minutes=5)
    return Decision(
        decision_id=decision_id,
        experiment_id=experiment_id,
        symbol="NVDA",
        action=Action.BUY,
        horizon="5d",
        confidence=0.72,
        expected_return=0.04,
        max_expected_loss=0.02,
        evidence_ids=[evidence_id],
        reasoning_summary="guidance improved while risk stayed bounded",
        created_at=created,
        valid_until=created + timedelta(days=5),
    )


def make_review(
    decision_id: str,
    *,
    review_id: str = "rv_00000000-0000-0000-0000-000000000001",
    created_at: datetime | None = None,
) -> Review:
    return Review(
        review_id=review_id,
        decision_id=decision_id,
        actual_return=0.03,
        direction_correct=True,
        risk_limit_breached=False,
        outcome="profit",
        cause_tags=["guidance", "momentum"],
        review_summary="decision matched the evidence-backed thesis",
        created_at=created_at or fixed_now() + timedelta(days=5),
    )


def make_learning(
    review_id: str,
    *,
    learning_id: str = "lr_00000000-0000-0000-0000-000000000001",
    created_at: datetime | None = None,
) -> Learning:
    return Learning(
        learning_id=learning_id,
        review_id=review_id,
        learning_type="agent_weight_update",
        target="guidance-signal-weight",
        before={"weight": 0.4, "tags": ["guidance"]},
        after={"weight": 0.45, "tags": ["guidance"]},
        reason="profitable reviewed decision",
        created_at=created_at or fixed_now() + timedelta(days=5, minutes=1),
    )
