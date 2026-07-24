from __future__ import annotations

import builtins
from collections import defaultdict
from collections.abc import Iterable

from aios.kernel.brain002 import SkillDefinition
from aios.kernel.enums import SkillStatus
from aios.kernel.errors import DuplicateEntityError, MissingEntityError


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
