from datetime import UTC, datetime, timedelta

import pytest

from aios.kernel.decision import Decision
from aios.kernel.enums import Action
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    ReferenceIntegrityError,
)
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def now() -> datetime:
    return datetime.now(UTC)


def evidence() -> Evidence:
    return Evidence(
        evidence_type="news",
        source="wire",
        symbols=["MSFT"],
        published_at=now(),
        available_at=now(),
        summary="earnings surprise",
        reliability=0.8,
        content_hash="hash-msft",
    )


def experiment(evidence_id: str) -> Experiment:
    return Experiment(
        name="baseline",
        model="model-v1",
        prompt_version="prompt-v1",
        agent_config_version="agent-v1",
        dataset_snapshot="snapshot-v1",
        evidence_ids=[evidence_id],
        started_at=now(),
    )


def decision(experiment_id: str, evidence_id: str) -> Decision:
    return Decision(
        experiment_id=experiment_id,
        symbol="MSFT",
        action=Action.HOLD,
        horizon="1d",
        confidence=0.6,
        expected_return=0.0,
        max_expected_loss=0.01,
        evidence_ids=[evidence_id],
        reasoning_summary="unclear edge",
        valid_until=now() + timedelta(days=1),
    )


def test_storage_rejects_duplicate_ids_and_missing_reads() -> None:
    storage = InMemoryStorage()
    item = evidence()

    storage.save(item)

    with pytest.raises(DuplicateEntityError):
        storage.save(item)

    with pytest.raises(MissingEntityError):
        storage.get(Evidence, "ev_missing")


def test_lifecycle_rejects_missing_references() -> None:
    service = DecisionLifecycleService(InMemoryStorage())
    item = evidence()

    with pytest.raises(ReferenceIntegrityError):
        service.start_experiment(experiment(item.evidence_id))

    service.register_evidence(item)

    with pytest.raises(ReferenceIntegrityError):
        service.create_decision(decision("ex_missing", item.evidence_id))
