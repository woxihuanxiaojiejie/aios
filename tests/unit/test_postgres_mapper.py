from datetime import UTC

import pytest
from tests.factories import (
    make_decision,
    make_evidence,
    make_experiment,
    make_learning,
    make_review,
)

from aios.kernel.base import KernelModel
from aios.kernel.decision import Decision
from aios.kernel.errors import UnsupportedEntityError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.storage.postgres.mapper import model_to_entity, to_model


class UnsupportedEntity(KernelModel):
    id_field = "unsupported_id"

    unsupported_id: str = "zz_unsupported"


@pytest.mark.parametrize(
    "entity",
    [
        make_evidence(),
        make_experiment(make_evidence().evidence_id),
        make_decision(
            make_experiment(make_evidence().evidence_id).experiment_id,
            make_evidence().evidence_id,
        ),
        make_review(
            make_decision(
                make_experiment(make_evidence().evidence_id).experiment_id,
                make_evidence().evidence_id,
            ).decision_id
        ),
        make_learning(
            make_review(
                make_decision(
                    make_experiment(make_evidence().evidence_id).experiment_id,
                    make_evidence().evidence_id,
                ).decision_id
            ).review_id
        ),
    ],
)
def test_domain_to_orm_and_back(entity: KernelModel) -> None:
    model = to_model(entity)
    restored = model_to_entity(model)

    assert restored == entity


def test_jsonb_and_utc_fields_round_trip() -> None:
    evidence = make_evidence()
    restored_evidence = model_to_entity(to_model(evidence))

    assert isinstance(restored_evidence, Evidence)
    assert restored_evidence.symbols == ("NVDA", "MSFT")
    assert restored_evidence.metadata == {"form": "10-Q", "nested": {"page": 3}}
    assert restored_evidence.created_at.tzinfo is UTC

    experiment = make_experiment(evidence.evidence_id)
    restored_experiment = model_to_entity(to_model(experiment))
    assert isinstance(restored_experiment, Experiment)
    assert restored_experiment.evidence_ids == (evidence.evidence_id,)
    assert restored_experiment.parameters == {"temperature": 0, "weights": [1, 2]}

    decision = make_decision(experiment.experiment_id, evidence.evidence_id)
    restored_decision = model_to_entity(to_model(decision))
    assert isinstance(restored_decision, Decision)
    assert restored_decision.evidence_ids == (evidence.evidence_id,)

    review = make_review(decision.decision_id)
    restored_review = model_to_entity(to_model(review))
    assert isinstance(restored_review, Review)
    assert restored_review.cause_tags == ("guidance", "momentum")

    learning = make_learning(review.review_id)
    restored_learning = model_to_entity(to_model(learning))
    assert isinstance(restored_learning, Learning)
    assert restored_learning.before == {"weight": 0.4, "tags": ["guidance"]}
    assert restored_learning.after == {"weight": 0.45, "tags": ["guidance"]}


def test_unsupported_entity_mapping_fails() -> None:
    with pytest.raises(UnsupportedEntityError, match="UnsupportedEntity"):
        to_model(UnsupportedEntity())
