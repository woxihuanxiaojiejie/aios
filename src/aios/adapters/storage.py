from __future__ import annotations

from typing import Protocol, TypeVar

from aios.kernel.base import KernelModel
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome

EntityT = TypeVar("EntityT", bound=KernelModel)


class Storage(Protocol):
    def save(self, entity: KernelModel) -> None:
        """Persist a new entity."""

    def replace(self, entity: KernelModel) -> None:
        """Replace an existing entity without changing its id."""

    def get(self, entity_type: type[EntityT], entity_id: str) -> EntityT:
        """Return an entity by type and id."""

    def list(self, entity_type: type[EntityT]) -> list[EntityT]:
        """Return all entities of a given type."""

    def exists(self, entity_type: type[EntityT], entity_id: str) -> bool:
        """Check whether an entity exists."""

    def get_decision_outcome_by_decision_id(
        self,
        decision_id: str,
    ) -> DecisionOutcome | None:
        """Return the settlement outcome for a Decision if one exists."""

    def get_decision_evaluation_by_decision_id(
        self,
        decision_id: str,
        evaluation_rules_version: str,
    ) -> DecisionEvaluation | None:
        """Return the versioned evaluation for a Decision if one exists."""

    def get_review_by_decision_id(self, decision_id: str) -> Review | None:
        """Return the Review for a Decision if one exists."""
