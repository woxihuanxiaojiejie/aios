from __future__ import annotations

from aios.adapters.storage import Storage
from aios.kernel.base import KernelModel
from aios.kernel.decision import Decision
from aios.kernel.errors import ReferenceIntegrityError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review


class DecisionLifecycleService:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def register_evidence(self, evidence: Evidence) -> Evidence:
        self._storage.save(evidence)
        return evidence

    def start_experiment(self, experiment: Experiment) -> Experiment:
        for evidence_id in experiment.evidence_ids:
            self._require_exists(Evidence, evidence_id)
        self._storage.save(experiment)
        return experiment

    def create_decision(self, decision: Decision) -> Decision:
        self._require_exists(Experiment, decision.experiment_id)
        for evidence_id in decision.evidence_ids:
            self._require_exists(Evidence, evidence_id)
        self._storage.save(decision)
        return decision

    def create_review(self, review: Review) -> Review:
        self._require_exists(Decision, review.decision_id)
        self._storage.save(review)
        return review

    def propose_learning(self, learning: Learning) -> Learning:
        self._require_exists(Review, learning.review_id)
        self._storage.save(learning)
        return learning

    def _require_exists(self, entity_type: type[KernelModel], entity_id: str) -> None:
        if not self._storage.exists(entity_type, entity_id):
            msg = f"{entity_type.__name__} with id {entity_id} is required"
            raise ReferenceIntegrityError(msg)
