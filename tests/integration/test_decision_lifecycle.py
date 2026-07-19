from datetime import UTC, datetime, timedelta

from aios.kernel.decision import Decision
from aios.kernel.enums import Action, ApprovalStatus
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def test_full_decision_lifecycle_round_trip() -> None:
    created_at = datetime.now(UTC)
    storage = InMemoryStorage()
    service = DecisionLifecycleService(storage)

    evidence = service.register_evidence(
        Evidence(
            evidence_type="filing",
            source="company-10q",
            symbols=["NVDA"],
            published_at=created_at,
            available_at=created_at + timedelta(minutes=2),
            summary="updated revenue guidance",
            reliability=0.85,
            content_hash="hash-nvda-guidance",
            metadata={"form": "10-Q"},
        )
    )
    experiment = service.start_experiment(
        Experiment(
            name="guidance-impact",
            model="model-v1",
            prompt_version="prompt-v1",
            agent_config_version="agent-config-v1",
            dataset_snapshot="snapshot-2026-07-19",
            evidence_ids=[evidence.evidence_id],
            parameters={"temperature": 0},
            started_at=created_at + timedelta(minutes=3),
            finished_at=created_at + timedelta(minutes=4),
        )
    )
    decision = service.create_decision(
        Decision(
            experiment_id=experiment.experiment_id,
            symbol="NVDA",
            action=Action.BUY,
            horizon="5d",
            confidence=0.72,
            expected_return=0.04,
            max_expected_loss=0.02,
            evidence_ids=[evidence.evidence_id],
            reasoning_summary="guidance improved while risk stayed bounded",
            valid_until=created_at + timedelta(days=5),
        )
    )
    review = service.create_review(
        Review(
            decision_id=decision.decision_id,
            actual_return=0.03,
            direction_correct=True,
            risk_limit_breached=False,
            outcome="profit",
            cause_tags=["guidance", "guidance", "momentum"],
            review_summary="move followed the evidence-backed thesis",
        )
    )
    learning = service.propose_learning(
        Learning(
            review_id=review.review_id,
            learning_type="agent_weight_update",
            target="guidance-signal-weight",
            before={"weight": 0.4},
            after={"weight": 0.45},
            reason="profitable reviewed decision",
        )
    )

    assert storage.get(Evidence, evidence.evidence_id) == evidence
    assert storage.get(Experiment, experiment.experiment_id) == experiment
    assert storage.get(Decision, decision.decision_id) == decision
    assert storage.get(Review, review.review_id) == review
    assert storage.get(Learning, learning.learning_id) == learning
    assert review.cause_tags == ("guidance", "momentum")
    assert learning.approval_status is ApprovalStatus.PENDING
