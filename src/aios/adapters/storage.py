from __future__ import annotations

from typing import Protocol, TypeVar

from aios.kernel.base import KernelModel

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
