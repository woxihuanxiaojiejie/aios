from __future__ import annotations

from datetime import datetime

from aios.adapters.storage import Storage
from aios.kernel.base import KernelModel
from aios.kernel.decision import Decision
from aios.kernel.enums import ApprovalStatus, ExperimentStatus
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
    ReferenceIntegrityError,
)
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

    def complete_experiment(
        self,
        experiment_id: str,
        finished_at: datetime,
    ) -> Experiment:
        experiment = self._storage.get(Experiment, experiment_id)
        if experiment.status is ExperimentStatus.FINISHED:
            msg = f"Experiment {experiment_id} is already finished"
            raise InvalidStateTransitionError(msg)
        replacement = Experiment(
            **{
                **experiment.model_dump(),
                "status": ExperimentStatus.FINISHED,
                "finished_at": finished_at,
            }
        )
        self._storage.replace(replacement)
        return replacement

    def get_entity[EntityT: KernelModel](
        self,
        entity_type: type[EntityT],
        entity_id: str,
    ) -> EntityT:
        return self._storage.get(entity_type, entity_id)

    def list_entities[EntityT: KernelModel](
        self,
        entity_type: type[EntityT],
    ) -> list[EntityT]:
        return self._storage.list(entity_type)

    def create_decision(self, decision: Decision) -> Decision:
        self._require_exists(Experiment, decision.experiment_id)
        experiment = self._storage.get(Experiment, decision.experiment_id)
        if not set(decision.evidence_ids).issubset(set(experiment.evidence_ids)):
            msg = "Decision evidence_ids must be a subset of Experiment evidence_ids"
            raise ReferenceIntegrityError(msg)
        for evidence_id in decision.evidence_ids:
            self._require_exists(Evidence, evidence_id)
        self._storage.save(decision)
        return decision

    def create_review(self, review: Review) -> Review:
        self._require_exists(Decision, review.decision_id)
        if any(
            item.decision_id == review.decision_id
            for item in self._storage.list(Review)
        ):
            msg = f"Decision {review.decision_id} already has a Review"
            raise DuplicateEntityError(msg)
        self._storage.save(review)
        return review

    def propose_learning(self, learning: Learning) -> Learning:
        self._require_exists(Review, learning.review_id)
        if learning.approval_status is not ApprovalStatus.PENDING:
            msg = "Learning proposals must start as pending"
            raise InvalidStateTransitionError(msg)
        self._storage.save(learning)
        return learning

    def approve_learning(self, learning_id: str) -> Learning:
        return self._decide_learning(learning_id, ApprovalStatus.APPROVED)

    def reject_learning(self, learning_id: str) -> Learning:
        return self._decide_learning(learning_id, ApprovalStatus.REJECTED)

    def _require_exists(self, entity_type: type[KernelModel], entity_id: str) -> None:
        if not self._storage.exists(entity_type, entity_id):
            msg = f"{entity_type.__name__} with id {entity_id} is required"
            raise ReferenceIntegrityError(msg)

    def _decide_learning(
        self,
        learning_id: str,
        approval_status: ApprovalStatus,
    ) -> Learning:
        learning = self._storage.get(Learning, learning_id)
        if learning.approval_status is not ApprovalStatus.PENDING:
            msg = f"Learning {learning_id} has already been decided"
            raise InvalidStateTransitionError(msg)
        replacement = Learning(
            **{
                **learning.model_dump(),
                "approval_status": approval_status,
            }
        )
        self._storage.replace(replacement)
        return replacement
