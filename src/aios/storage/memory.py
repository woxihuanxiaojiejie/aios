from __future__ import annotations

from collections import defaultdict
from typing import cast

from aios.kernel.base import KernelModel
from aios.kernel.errors import DuplicateEntityError, MissingEntityError


class InMemoryStorage:
    def __init__(self) -> None:
        self._entities: dict[type[KernelModel], dict[str, KernelModel]] = defaultdict(
            dict
        )

    def save(self, entity: KernelModel) -> None:
        entity_type = type(entity)
        entity_id = entity.entity_id
        if entity_id in self._entities[entity_type]:
            msg = f"{entity_type.__name__} with id {entity_id} already exists"
            raise DuplicateEntityError(msg)
        self._entities[entity_type][entity_id] = entity

    def get[EntityT: KernelModel](
        self, entity_type: type[EntityT], entity_id: str
    ) -> EntityT:
        try:
            entity = self._entities[entity_type][entity_id]
        except KeyError as exc:
            msg = f"{entity_type.__name__} with id {entity_id} does not exist"
            raise MissingEntityError(msg) from exc
        return cast("EntityT", entity)

    def list[EntityT: KernelModel](self, entity_type: type[EntityT]) -> list[EntityT]:
        return [
            cast("EntityT", entity) for entity in self._entities[entity_type].values()
        ]

    def exists[EntityT: KernelModel](
        self, entity_type: type[EntityT], entity_id: str
    ) -> bool:
        return entity_id in self._entities[entity_type]
