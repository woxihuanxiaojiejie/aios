from tests.factories import (
    make_decision,
    make_evidence,
    make_experiment,
    make_learning,
    make_review,
)

from aios.kernel.decision import Decision
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.storage.postgres.storage import PostgresStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def test_postgres_decision_lifecycle_persists_across_storage_instances(
    migrated_postgres_url: str,
) -> None:
    service = DecisionLifecycleService(PostgresStorage(migrated_postgres_url))

    evidence = service.register_evidence(make_evidence())
    experiment = service.start_experiment(make_experiment(evidence.evidence_id))
    decision = service.create_decision(
        make_decision(experiment.experiment_id, evidence.evidence_id)
    )
    review = service.create_review(make_review(decision.decision_id))
    learning = service.propose_learning(make_learning(review.review_id))

    fresh_storage = PostgresStorage(migrated_postgres_url)
    assert fresh_storage.get(Evidence, evidence.evidence_id) == evidence
    assert fresh_storage.get(Experiment, experiment.experiment_id) == experiment
    assert fresh_storage.get(Decision, decision.decision_id) == decision
    assert fresh_storage.get(Review, review.review_id) == review
    assert fresh_storage.get(Learning, learning.learning_id) == learning
