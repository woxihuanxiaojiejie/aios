from __future__ import annotations

from datetime import timedelta

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from tests.factories import (
    fixed_now,
    make_decision,
    make_evaluation,
    make_evidence,
    make_experiment,
    make_learning,
    make_outcome,
    make_review,
)
from tests.integration.conftest import alembic_config, table_count

from aios.kernel.decision import Decision
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    StorageOperationError,
)
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.storage.postgres.storage import PostgresStorage


def seed_lifecycle(
    storage: PostgresStorage,
) -> tuple[Evidence, Experiment, Decision, Review, Learning]:
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    decision = make_decision(experiment.experiment_id, evidence.evidence_id)
    review = make_review(decision.decision_id)
    learning = make_learning(review.review_id)
    for entity in [evidence, experiment, decision, review, learning]:
        storage.save(entity)
    return evidence, experiment, decision, review, learning


def test_save_and_read_all_core_entities(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, review, learning = seed_lifecycle(storage)

    assert storage.get(Evidence, evidence.evidence_id) == evidence
    assert storage.get(Experiment, experiment.experiment_id) == experiment
    assert storage.get(Decision, decision.decision_id) == decision
    assert storage.get(Review, review.review_id) == review
    assert storage.get(Learning, learning.learning_id) == learning


def test_list_exists_duplicate_and_missing(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    first = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000201",
        created_at=fixed_now() + timedelta(minutes=1),
    )
    second = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000200",
        created_at=fixed_now(),
    )

    storage.save(first)
    storage.save(second)

    assert storage.exists(Evidence, first.evidence_id)
    assert [item.evidence_id for item in storage.list(Evidence)] == [
        second.evidence_id,
        first.evidence_id,
    ]

    with pytest.raises(DuplicateEntityError):
        storage.save(first)

    with pytest.raises(MissingEntityError):
        storage.get(Evidence, "ev_missing")


def test_jsonb_fields_round_trip(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, review, learning = seed_lifecycle(storage)

    assert storage.get(Evidence, evidence.evidence_id).metadata["nested"] == {"page": 3}
    assert storage.get(Experiment, experiment.experiment_id).parameters == {
        "temperature": 0,
        "weights": [1, 2],
    }
    assert storage.get(Decision, decision.decision_id).evidence_ids == (
        evidence.evidence_id,
    )
    assert storage.get(Review, review.review_id).cause_tags == (
        "guidance",
        "momentum",
    )
    assert storage.get(Learning, learning.learning_id).after == {
        "weight": 0.45,
        "tags": ["guidance"],
    }


def test_decision_settlement_query_methods(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, _review, _learning = seed_lifecycle(storage)
    outcome = make_outcome(decision.decision_id, experiment.experiment_id)
    evaluation = make_evaluation(
        decision.decision_id,
        outcome.outcome_id,
        experiment.experiment_id,
    )

    storage.save(outcome)
    storage.save(evaluation)

    assert storage.get(DecisionOutcome, outcome.outcome_id) == outcome
    assert storage.get(DecisionEvaluation, evaluation.evaluation_id) == evaluation
    assert storage.get_decision_outcome_by_decision_id(decision.decision_id) == outcome
    assert (
        storage.get_decision_evaluation_by_decision_id(
            decision.decision_id,
            evaluation.evaluation_rules_version,
        )
        == evaluation
    )
    assert storage.get_decision_outcome_by_decision_id("dc_missing") is None
    assert (
        storage.get_decision_evaluation_by_decision_id(
            decision.decision_id,
            "missing-rules",
        )
        is None
    )
    assert storage.get(Evidence, evidence.evidence_id) == evidence


def test_write_failure_rolls_back(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    invalid = make_decision("ex_missing", "ev_missing")

    with pytest.raises(StorageOperationError):
        storage.save(invalid)

    assert table_count(migrated_postgres_url, "decisions") == 0


def test_review_decision_id_unique_constraint(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, _review, _learning = seed_lifecycle(storage)
    duplicate_review = make_review(
        decision.decision_id,
        review_id="rv_00000000-0000-0000-0000-000000000002",
    )

    with pytest.raises(StorageOperationError):
        storage.save(duplicate_review)

    assert storage.get(Evidence, evidence.evidence_id) == evidence
    assert storage.get(Experiment, experiment.experiment_id) == experiment


def test_foreign_keys_and_delete_restrict(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    decision = make_decision(experiment.experiment_id, evidence.evidence_id)

    storage.save(evidence)
    with pytest.raises(StorageOperationError):
        storage.save(decision)

    storage.save(experiment)
    storage.save(decision)

    engine = create_engine(migrated_postgres_url)
    try:
        with engine.begin() as connection, pytest.raises(IntegrityError):
            connection.execute(
                text("delete from experiments where experiment_id = :id"),
                {"id": experiment.experiment_id},
            )
    finally:
        engine.dispose()


def test_migration_upgrade_downgrade_upgrade(postgres_url: str) -> None:
    config = alembic_config(postgres_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(postgres_url)
    try:
        inspector = inspect(engine)
        assert {
            "evidence",
            "experiments",
            "decisions",
            "reviews",
            "learnings",
            "llm_generation_records",
            "decision_outcomes",
            "decision_evaluations",
        } <= set(inspector.get_table_names())
        review_columns = {
            column["name"]: column for column in inspector.get_columns("reviews")
        }
        assert review_columns["actual_return"]["nullable"] is True
        assert review_columns["direction_correct"]["nullable"] is True
        assert review_columns["risk_limit_breached"]["nullable"] is True
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(postgres_url)
    try:
        inspector = inspect(engine)
        assert "evidence" not in inspector.get_table_names()
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(postgres_url)
    try:
        inspector = inspect(engine)
        assert "decision_evaluations" in inspector.get_table_names()
    finally:
        engine.dispose()
