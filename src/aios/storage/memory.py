from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Protocol, cast

from aios.kernel.base import KernelModel
from aios.kernel.decision import Decision
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    UnsupportedEntityError,
)
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review

SUPPORTED_ENTITY_TYPES = (Evidence, Experiment, Decision, Review, Learning)


class _CreatedEntity(Protocol):
    entity_id: str
    created_at: datetime


class InMemoryStorage:
    def __init__(self) -> None:
        self._entities: dict[type[KernelModel], dict[str, KernelModel]] = defaultdict(
            dict
        )

    def save(self, entity: KernelModel) -> None:
        self._require_supported(type(entity))
        entity_type = type(entity)
        entity_id = entity.entity_id
        if entity_id in self._entities[entity_type]:
            msg = f"{entity_type.__name__} with id {entity_id} already exists"
            raise DuplicateEntityError(msg)
        self._entities[entity_type][entity_id] = entity

    def replace(self, entity: KernelModel) -> None:
        self._require_supported(type(entity))
        entity_type = type(entity)
        entity_id = entity.entity_id
        if entity_id not in self._entities[entity_type]:
            msg = f"{entity_type.__name__} with id {entity_id} does not exist"
            raise MissingEntityError(msg)
        self._entities[entity_type][entity_id] = entity

    def get[EntityT: KernelModel](
        self, entity_type: type[EntityT], entity_id: str
    ) -> EntityT:
        self._require_supported(entity_type)
        try:
            entity = self._entities[entity_type][entity_id]
        except KeyError as exc:
            msg = f"{entity_type.__name__} with id {entity_id} does not exist"
            raise MissingEntityError(msg) from exc
        return cast("EntityT", entity)

    def list[EntityT: KernelModel](self, entity_type: type[EntityT]) -> list[EntityT]:
        self._require_supported(entity_type)
        sorted_entities = sorted(
            self._entities[entity_type].values(),
            key=self._sort_key,
        )
        return [cast("EntityT", entity) for entity in sorted_entities]

    def exists[EntityT: KernelModel](
        self, entity_type: type[EntityT], entity_id: str
    ) -> bool:
        self._require_supported(entity_type)
        return entity_id in self._entities[entity_type]

    def _require_supported(self, entity_type: type[KernelModel]) -> None:
        if entity_type not in SUPPORTED_ENTITY_TYPES:
            msg = f"{entity_type.__name__} is not supported by InMemoryStorage"
            raise UnsupportedEntityError(msg)

    def _sort_key(self, entity: KernelModel) -> tuple[datetime, str]:
        sortable = cast("_CreatedEntity", entity)
        return sortable.created_at, sortable.entity_id
