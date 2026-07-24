from __future__ import annotations

import builtins
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from aios.kernel.brain002 import AnalysisTask, SkillDefinition
from aios.kernel.enums import SkillStatus
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    ReferenceIntegrityError,
)
from aios.kernel.evidence import Evidence


@dataclass(frozen=True)
class SkillSelection:
    selected_skill_ids: tuple[str, ...]
    rejected_skill_ids: tuple[str, ...]
    selection_reason: dict[str, str]
    matched_conditions: dict[str, tuple[str, ...]]


class SkillRegistry:
    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], SkillDefinition] = {}
        self._versions: dict[str, builtins.list[str]] = defaultdict(list)
        self._active_versions: dict[str, str] = {}

    def register(self, definition: SkillDefinition) -> SkillDefinition:
        key = self._key(definition.skill_id, definition.version)
        if key in self._definitions:
            msg = (
                f"SkillDefinition {definition.skill_id} "
                f"version {definition.version} already exists"
            )
            raise DuplicateEntityError(msg)
        self._definitions[key] = definition
        self._versions[definition.skill_id].append(definition.version)
        if (
            definition.status is SkillStatus.ENABLED
            and definition.skill_id not in self._active_versions
        ):
            self._active_versions[definition.skill_id] = definition.version
        return definition

    def get(self, skill_id: str, version: str | None = None) -> SkillDefinition:
        selected_version = version
        if selected_version is None:
            return self.get_active_version(skill_id)
        key = self._key(skill_id, selected_version)
        try:
            return self._definitions[key]
        except KeyError as exc:
            msg = f"SkillDefinition {skill_id} version {selected_version} is missing"
            raise MissingEntityError(msg) from exc

    def list(self) -> builtins.list[SkillDefinition]:
        return sorted(
            self._definitions.values(),
            key=lambda definition: (
                definition.created_at,
                definition.skill_id,
                definition.version,
            ),
        )

    def enable(self, skill_id: str, version: str) -> SkillDefinition:
        definition = self.get(skill_id, version)
        enabled = definition.model_copy(update={"status": SkillStatus.ENABLED})
        self._definitions[self._key(skill_id, version)] = enabled
        if skill_id not in self._active_versions:
            self._active_versions[skill_id] = version
        return enabled

    def disable(self, skill_id: str, version: str) -> SkillDefinition:
        definition = self.get(skill_id, version)
        disabled = definition.model_copy(update={"status": SkillStatus.DISABLED})
        self._definitions[self._key(skill_id, version)] = disabled
        if self._active_versions.get(skill_id) == version:
            replacement = self._latest_enabled_version(
                skill_id,
                exclude_versions={version},
            )
            if replacement is None:
                self._active_versions.pop(skill_id, None)
            else:
                self._active_versions[skill_id] = replacement
        return disabled

    def get_active_version(self, skill_id: str) -> SkillDefinition:
        try:
            version = self._active_versions[skill_id]
        except KeyError as exc:
            msg = f"SkillDefinition {skill_id} has no active version"
            raise MissingEntityError(msg) from exc
        return self.get(skill_id, version)

    def list_compatible(
        self,
        *,
        market: str,
        asset_type: str,
        horizon: str,
        evidence_types: Iterable[str],
    ) -> builtins.list[SkillDefinition]:
        evidence_type_set = set(evidence_types)
        return [
            definition
            for definition in self.list()
            if definition.status is SkillStatus.ENABLED
            and market in definition.supported_markets
            and asset_type in definition.supported_asset_types
            and horizon in definition.supported_horizons
            and set(definition.required_evidence_types).issubset(evidence_type_set)
            and self._dependencies_active(definition)
        ]

    def replace_version(self, definition: SkillDefinition) -> SkillDefinition:
        key = self._key(definition.skill_id, definition.version)
        if key not in self._definitions:
            self.register(definition)
        else:
            self._definitions[key] = definition
        if definition.status is SkillStatus.ENABLED:
            self._active_versions[definition.skill_id] = definition.version
        return definition

    def rollback_version(self, skill_id: str) -> SkillDefinition:
        active = self.get_active_version(skill_id)
        replacement_version = self._latest_enabled_version(
            skill_id,
            exclude_versions={active.version},
        )
        if replacement_version is None:
            msg = f"SkillDefinition {skill_id} has no previous enabled version"
            raise MissingEntityError(msg)
        self._active_versions[skill_id] = replacement_version
        return self.get(skill_id, replacement_version)

    def _dependencies_active(self, definition: SkillDefinition) -> bool:
        return all(
            self._has_enabled_active_version(dependency_id)
            for dependency_id in definition.dependencies
        )

    def _has_enabled_active_version(self, skill_id: str) -> bool:
        try:
            return self.get_active_version(skill_id).status is SkillStatus.ENABLED
        except MissingEntityError:
            return False

    def _latest_enabled_version(
        self,
        skill_id: str,
        *,
        exclude_versions: set[str],
    ) -> str | None:
        candidates = [
            self.get(skill_id, version)
            for version in self._versions.get(skill_id, ())
            if version not in exclude_versions
            and self.get(skill_id, version).status is SkillStatus.ENABLED
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda definition: definition.created_at).version

    def _key(self, skill_id: str, version: str) -> tuple[str, str]:
        return skill_id, version


class SkillSelector:
    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def select(
        self,
        *,
        task: AnalysisTask,
        evidence: Iterable[Evidence],
    ) -> SkillSelection:
        point_in_time_evidence = self._point_in_time_evidence(task, evidence)
        evidence_types = {item.evidence_type for item in point_in_time_evidence}
        selected_skill_ids: builtins.list[str] = []
        rejected_skill_ids: builtins.list[str] = []
        selection_reason: dict[str, str] = {}
        matched_conditions: dict[str, tuple[str, ...]] = {
            "point_in_time_evidence_ids": tuple(
                item.evidence_id for item in point_in_time_evidence
            )
        }
        requested_skill_ids = set(task.requested_skill_ids)

        for definition in self._active_definitions():
            matched: builtins.list[str] = []
            reason = self._rejection_reason(
                definition=definition,
                task=task,
                evidence_types=evidence_types,
                evidence=point_in_time_evidence,
                requested_skill_ids=requested_skill_ids,
                matched=matched,
            )
            selection_reason[definition.skill_id] = reason
            matched_conditions[definition.skill_id] = tuple(matched)
            if reason == "selected":
                selected_skill_ids.append(definition.skill_id)
            else:
                rejected_skill_ids.append(definition.skill_id)

        return SkillSelection(
            selected_skill_ids=tuple(selected_skill_ids),
            rejected_skill_ids=tuple(rejected_skill_ids),
            selection_reason=selection_reason,
            matched_conditions=matched_conditions,
        )

    def _point_in_time_evidence(
        self,
        task: AnalysisTask,
        evidence: Iterable[Evidence],
    ) -> tuple[Evidence, ...]:
        evidence_by_id = {item.evidence_id: item for item in evidence}
        if task.evidence_ids:
            missing_ids = [
                evidence_id
                for evidence_id in task.evidence_ids
                if evidence_id not in evidence_by_id
            ]
            if missing_ids:
                msg = f"AnalysisTask references missing Evidence IDs: {missing_ids}"
                raise ReferenceIntegrityError(msg)
            ordered_evidence = [
                evidence_by_id[evidence_id] for evidence_id in task.evidence_ids
            ]
        else:
            ordered_evidence = list(evidence_by_id.values())
        return tuple(
            item for item in ordered_evidence if item.available_at <= task.as_of
        )

    def _active_definitions(self) -> tuple[SkillDefinition, ...]:
        active_definitions: builtins.list[SkillDefinition] = []
        seen_skill_ids: set[str] = set()
        for definition in self._registry.list():
            if definition.skill_id in seen_skill_ids:
                continue
            seen_skill_ids.add(definition.skill_id)
            try:
                active_definitions.append(
                    self._registry.get_active_version(definition.skill_id)
                )
            except MissingEntityError:
                if definition.status is SkillStatus.DISABLED:
                    active_definitions.append(definition)
        return tuple(active_definitions)

    def _rejection_reason(
        self,
        *,
        definition: SkillDefinition,
        task: AnalysisTask,
        evidence_types: set[str],
        evidence: tuple[Evidence, ...],
        requested_skill_ids: set[str],
        matched: builtins.list[str],
    ) -> str:
        if definition.status is not SkillStatus.ENABLED:
            return "disabled"
        if requested_skill_ids and definition.skill_id not in requested_skill_ids:
            return "not_requested"
        if task.market not in definition.supported_markets:
            return "market_not_supported"
        matched.append("market")
        if task.asset_type not in definition.supported_asset_types:
            return "asset_type_not_supported"
        matched.append("asset_type")
        if task.horizon not in definition.supported_horizons:
            return "horizon_not_supported"
        matched.append("horizon")
        if not set(definition.required_evidence_types).issubset(evidence_types):
            return "missing_evidence_type"
        matched.append("evidence_type")
        if not self._dependencies_active(definition):
            return "missing_dependency"
        if not self._trigger_conditions_match(definition.trigger_conditions, evidence):
            return "trigger_not_matched"
        if definition.trigger_conditions:
            matched.append("trigger_conditions")
        return "selected"

    def _trigger_conditions_match(
        self,
        trigger_conditions: dict[str, Any],
        evidence: tuple[Evidence, ...],
    ) -> bool:
        metadata_equals = trigger_conditions.get("metadata_equals")
        if metadata_equals is None:
            return True
        if not isinstance(metadata_equals, dict):
            return False
        return any(
            all(
                item.metadata.get(key) == value
                for key, value in metadata_equals.items()
            )
            for item in evidence
        )

    def _dependencies_active(self, definition: SkillDefinition) -> bool:
        return all(
            self._dependency_active(dependency_id)
            for dependency_id in definition.dependencies
        )

    def _dependency_active(self, skill_id: str) -> bool:
        try:
            active = self._registry.get_active_version(skill_id)
            return active.status is SkillStatus.ENABLED
        except MissingEntityError:
            return False
