from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from aios.kernel.decision import Decision
from aios.kernel.enums import Action, ApprovalStatus
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review


def now() -> datetime:
    return datetime.now(UTC)


def test_entity_ids_use_required_prefixes() -> None:
    evidence = Evidence(
        evidence_type="news",
        source="filing",
        symbols=["AAPL"],
        published_at=now(),
        available_at=now(),
        summary="material update",
        reliability=0.9,
        content_hash="hash-1",
    )
    experiment = Experiment(
        name="baseline",
        model="decision-model",
        prompt_version="prompt-v1",
        agent_config_version="agent-v1",
        dataset_snapshot="dataset-v1",
        evidence_ids=[evidence.evidence_id],
        started_at=now(),
    )
    decision = Decision(
        experiment_id=experiment.experiment_id,
        symbol="AAPL",
        action=Action.BUY,
        horizon="1d",
        confidence=0.7,
        expected_return=0.03,
        max_expected_loss=0.01,
        evidence_ids=[evidence.evidence_id],
        reasoning_summary="positive expected value",
        valid_until=now() + timedelta(hours=1),
    )
    review = Review(
        decision_id=decision.decision_id,
        actual_return=0.04,
        direction_correct=True,
        risk_limit_breached=False,
        outcome="profit",
        cause_tags=["signal", "signal"],
        review_summary="decision worked",
    )
    learning = Learning(
        review_id=review.review_id,
        learning_type="prompt_update",
        target="prompt-v1",
        before={"threshold": 0.6},
        after={"threshold": 0.7},
        reason="reduce marginal calls",
    )

    assert evidence.evidence_id.startswith("ev_")
    assert experiment.experiment_id.startswith("ex_")
    assert decision.decision_id.startswith("dc_")
    assert review.review_id.startswith("rv_")
    assert learning.learning_id.startswith("lr_")


def test_evidence_validates_time_reliability_and_symbols() -> None:
    with pytest.raises(ValidationError):
        Evidence(
            evidence_type="news",
            source="wire",
            symbols=[""],
            published_at=datetime.now(),
            available_at=now() - timedelta(minutes=1),
            summary="bad evidence",
            reliability=1.5,
            content_hash="hash-2",
        )


def test_experiment_validates_evidence_and_finish_time() -> None:
    with pytest.raises(ValidationError):
        Experiment(
            name="invalid",
            model="model",
            prompt_version="prompt-v1",
            agent_config_version="agent-v1",
            dataset_snapshot="dataset-v1",
            evidence_ids=[],
            started_at=now(),
            finished_at=now() - timedelta(seconds=1),
        )


def test_decision_validates_action_confidence_and_valid_until() -> None:
    with pytest.raises(ValidationError):
        Decision(
            experiment_id="ex_missing",
            symbol="AAPL",
            action="panic",
            horizon="1d",
            confidence=1.2,
            expected_return=0.01,
            max_expected_loss=0.02,
            evidence_ids=[],
            reasoning_summary="invalid",
            valid_until=now() - timedelta(seconds=1),
        )


def test_learning_defaults_to_pending_and_requires_change() -> None:
    learning = Learning(
        review_id="rv_example",
        learning_type="rule_update",
        target="risk-rule",
        before={"max_loss": 0.02},
        after={"max_loss": 0.01},
        reason="review found excessive risk",
    )

    assert learning.approval_status is ApprovalStatus.PENDING

    with pytest.raises(ValidationError):
        Learning(
            review_id="rv_example",
            learning_type="memory_update",
            target="memory",
            before={"a": 1},
            after={"a": 1},
            reason="unchanged",
        )
