from __future__ import annotations

import builtins
import concurrent.futures
import json
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from tenacity import Retrying, stop_after_attempt, wait_fixed

from aios.adapters.llm import LLMAdapter, LLMStructuredResult
from aios.kernel.base import ensure_utc, utc_now
from aios.kernel.brain002 import (
    AnalysisTask,
    SkillDefinition,
    SkillExecution,
    SkillResultPayload,
    TokenUsage,
)
from aios.kernel.brain002 import SkillResult as SkillResultRecord
from aios.kernel.enums import SkillExecutionStatus, SkillStatus
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


class SkillInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    market: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)
    analysis_horizon: str = Field(min_length=1)
    as_of: datetime
    evidence: tuple[Evidence, ...]
    market_context: dict[str, Any] = Field(default_factory=dict)
    user_constraints: dict[str, Any] = Field(default_factory=dict)
    skill_context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("as_of")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)


@dataclass(frozen=True)
class SkillPrompt:
    system_prompt: str
    user_prompt: str
    prompt_version: str


@dataclass(frozen=True)
class SkillResponseParseResult:
    raw_response: str
    extracted_payload: dict[str, Any] | None
    validation_error: Any | None
    payload: SkillResultPayload | None


class SkillResponseParser:
    def parse(self, raw_response: str) -> SkillResponseParseResult:
        extracted_payload: dict[str, Any] | None = None
        try:
            extracted_payload = self._extract_json_object(raw_response)
            payload = SkillResultPayload.model_validate(extracted_payload)
            return SkillResponseParseResult(
                raw_response=raw_response,
                extracted_payload=extracted_payload,
                validation_error=None,
                payload=payload,
            )
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            validation_error = (
                exc.errors() if isinstance(exc, ValidationError) else str(exc)
            )
            return SkillResponseParseResult(
                raw_response=raw_response,
                extracted_payload=extracted_payload,
                validation_error=validation_error,
                payload=None,
            )

    def _extract_json_object(self, raw_response: str) -> dict[str, Any]:
        text = self._strip_json_code_fence(raw_response.strip())
        decoder = json.JSONDecoder()
        starts = [index for index in (text.find("{"), text.find("[")) if index >= 0]
        if not starts:
            msg = "LLM response did not contain a JSON object"
            raise ValueError(msg)
        parsed, _ = decoder.raw_decode(text[min(starts) :])
        if not isinstance(parsed, dict):
            msg = "LLM response JSON root must be an object"
            raise ValueError(msg)
        return self._unwrap_common_payload(parsed)

    def _strip_json_code_fence(self, text: str) -> str:
        if not text.startswith("```"):
            return text
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _unwrap_common_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        for key in ("payload", "result", "output"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        arguments = payload.get("arguments")
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
            except json.JSONDecodeError:
                return payload
            if isinstance(parsed, dict):
                return parsed
        return payload


class ExecutableSkill(Protocol):
    definition: SkillDefinition
    response_schema: type[BaseModel]
    prompt_version: str

    def build_prompt(self, skill_input: SkillInput) -> SkillPrompt:
        """Build an isolated prompt from the unified skill input."""


@dataclass(frozen=True)
class SkillExecutionOutcome:
    executions: tuple[SkillExecution, ...]
    results: tuple[SkillResultRecord, ...]


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


class SkillExecutor:
    def __init__(
        self,
        *,
        llm: LLMAdapter,
        model: str,
        timeout_seconds: float = 30.0,
        max_attempts: int = 2,
    ) -> None:
        self._llm = llm
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts

    def execute(
        self,
        *,
        task: AnalysisTask,
        skills: Iterable[ExecutableSkill],
        evidence: Iterable[Evidence],
        market_context: dict[str, Any] | None = None,
    ) -> SkillExecutionOutcome:
        allowed_evidence = self._point_in_time_evidence(task, evidence)
        executions: builtins.list[SkillExecution] = []
        results: builtins.list[SkillResultRecord] = []
        for skill in skills:
            execution, result = self._execute_one(
                task=task,
                skill=skill,
                evidence=allowed_evidence,
                market_context=market_context or {},
            )
            executions.append(execution)
            if result is not None:
                results.append(result)
        return SkillExecutionOutcome(
            executions=tuple(executions),
            results=tuple(results),
        )

    def _execute_one(
        self,
        *,
        task: AnalysisTask,
        skill: ExecutableSkill,
        evidence: tuple[Evidence, ...],
        market_context: dict[str, Any],
    ) -> tuple[SkillExecution, SkillResultRecord | None]:
        started_at = utc_now()
        attempts = 0
        prompt_version = skill.prompt_version
        try:
            skill_input = SkillInput(
                task_id=task.task_id,
                symbol=task.symbol,
                market=task.market,
                asset_type=task.asset_type,
                analysis_horizon=task.horizon,
                as_of=task.as_of,
                evidence=evidence,
                market_context=market_context,
                user_constraints=task.user_constraints,
                skill_context={},
            )
            prompt = skill.build_prompt(skill_input)
            prompt_version = prompt.prompt_version

            llm_result, payload, repair_attempted, attempts = (
                self._generate_valid_payload(
                    skill=skill,
                    prompt=prompt,
                    evidence=evidence,
                )
            )
            finished_at = utc_now()
            execution = self._execution_record(
                task=task,
                skill=skill,
                started_at=started_at,
                finished_at=finished_at,
                status=SkillExecutionStatus.SUCCEEDED,
                prompt_version=prompt_version,
                llm_result=llm_result,
                retry_count=attempts - 1,
                error=None,
            )
            result = self._result_record(
                execution=execution,
                skill=skill,
                payload=payload,
                llm_result=llm_result,
                repair_attempted=repair_attempted,
            )
            return execution, result
        except TimeoutError as exc:
            return self._failed_execution(
                task=task,
                skill=skill,
                started_at=started_at,
                prompt_version=prompt_version,
                retry_count=max(attempts - 1, 0),
                status=SkillExecutionStatus.TIMED_OUT,
                error=str(exc),
            ), None
        except Exception as exc:
            return self._failed_execution(
                task=task,
                skill=skill,
                started_at=started_at,
                prompt_version=prompt_version,
                retry_count=max(attempts - 1, 0),
                status=SkillExecutionStatus.FAILED,
                error=str(exc),
            ), None

    def _generate_valid_payload(
        self,
        *,
        skill: ExecutableSkill,
        prompt: SkillPrompt,
        evidence: tuple[Evidence, ...],
    ) -> tuple[LLMStructuredResult, SkillResultPayload, bool, int]:
        attempts = 0

        def generate(system_prompt: str, user_prompt: str) -> LLMStructuredResult:
            nonlocal attempts
            retryer = Retrying(
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_fixed(0),
                reraise=True,
            )

            def attempt() -> LLMStructuredResult:
                nonlocal attempts
                attempts += 1
                return self._run_with_timeout(
                    lambda: self._llm.generate_structured(
                        model=self._model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_schema=skill.response_schema,
                        temperature=0.0,
                    )
                )

            return retryer(attempt)

        try:
            llm_result = generate(prompt.system_prompt, prompt.user_prompt)
            payload = self._validated_payload(llm_result.parsed)
            self._validate_evidence_references(payload, evidence)
            return llm_result, payload, False, attempts
        except Exception as first_exc:
            if not self._is_repairable_response_error(first_exc):
                raise
            repair_prompt = self._repair_prompt(
                prompt=prompt,
                error=first_exc,
                evidence=evidence,
            )
            try:
                repaired_result = generate(
                    repair_prompt.system_prompt,
                    repair_prompt.user_prompt,
                )
                repaired_payload = self._validated_payload(repaired_result.parsed)
                self._validate_evidence_references(repaired_payload, evidence)
                return repaired_result, repaired_payload, True, attempts
            except Exception as second_exc:
                raise second_exc from first_exc

    def _repair_prompt(
        self,
        *,
        prompt: SkillPrompt,
        error: Exception,
        evidence: tuple[Evidence, ...],
    ) -> SkillPrompt:
        raw_response = getattr(error, "raw_response", None)
        extracted_payload = getattr(error, "extracted_payload", None)
        validation_error = getattr(error, "validation_error", None) or str(error)
        allowed_evidence_ids = [item.evidence_id for item in evidence]
        repair_payload = {
            "repair_instruction": (
                "Do not redo the investment analysis. Preserve the original "
                "conclusion semantics and only repair structure, field names, "
                "types, and evidence ID references. Return only JSON matching "
                "SkillResultPayload. The output must be a flat object; do not "
                "nest the original payload inside conclusion or any other field."
            ),
            "required_top_level_keys": [
                "conclusion",
                "direction",
                "confidence",
                "supporting_evidence_ids",
                "contradicting_evidence_ids",
                "assumptions",
                "risk_factors",
                "invalid_conditions",
                "missing_information",
                "reasoning_summary",
            ],
            "field_types": {
                "conclusion": "string, not object",
                "direction": "bullish | bearish | neutral | uncertain",
                "confidence": "number from 0 to 1",
                "supporting_evidence_ids": "array of allowed evidence ID strings",
                "contradicting_evidence_ids": "array of allowed evidence ID strings",
                "assumptions": "array of strings",
                "risk_factors": "array of strings",
                "invalid_conditions": "array of strings",
                "missing_information": "array of strings",
                "reasoning_summary": "string",
            },
            "original_user_prompt": prompt.user_prompt,
            "original_raw_response": raw_response,
            "original_extracted_payload": extracted_payload,
            "validation_error": validation_error,
            "allowed_evidence_ids": allowed_evidence_ids,
        }
        return SkillPrompt(
            system_prompt=(
                f"{prompt.system_prompt}\n"
                "The previous response failed SkillResultPayload validation. "
                "Do not redo the investment analysis. Preserve the original "
                "conclusion semantics and only repair structure, field names, "
                "types, and evidence ID references. Return only JSON matching "
                "SkillResultPayload."
            ),
            user_prompt=json.dumps(repair_payload, ensure_ascii=True, sort_keys=True),
            prompt_version=prompt.prompt_version,
        )

    def _is_repairable_response_error(self, error: Exception) -> bool:
        return isinstance(error, ValueError) or any(
            getattr(error, attribute, None) is not None
            for attribute in ("raw_response", "extracted_payload", "validation_error")
        )

    def _validate_evidence_references(
        self,
        payload: SkillResultPayload,
        evidence: tuple[Evidence, ...],
    ) -> None:
        valid_evidence_ids = {item.evidence_id for item in evidence}
        unknown_supporting = sorted(
            set(payload.supporting_evidence_ids) - valid_evidence_ids
        )
        unknown_contradicting = sorted(
            set(payload.contradicting_evidence_ids) - valid_evidence_ids
        )
        errors: builtins.list[str] = []
        if unknown_supporting:
            errors.append(f"unknown supporting_evidence_ids: {unknown_supporting}")
        if unknown_contradicting:
            errors.append(
                f"unknown contradicting_evidence_ids: {unknown_contradicting}"
            )
        if errors:
            raise ValueError("; ".join(errors))

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

    def _run_with_timeout(
        self,
        operation: Callable[[], LLMStructuredResult],
    ) -> LLMStructuredResult:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future: concurrent.futures.Future[LLMStructuredResult] = executor.submit(
            operation
        )
        try:
            return future.result(timeout=self._timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            msg = f"Skill execution timed out after {self._timeout_seconds}s"
            raise TimeoutError(msg) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _validated_payload(self, parsed: BaseModel) -> SkillResultPayload:
        try:
            return SkillResultPayload.model_validate(parsed.model_dump())
        except ValidationError as exc:
            msg = f"SkillResultPayload validation failed: {exc}"
            raise ValueError(msg) from exc

    def _execution_record(
        self,
        *,
        task: AnalysisTask,
        skill: ExecutableSkill,
        started_at: datetime,
        finished_at: datetime,
        status: SkillExecutionStatus,
        prompt_version: str,
        llm_result: LLMStructuredResult,
        retry_count: int,
        error: str | None,
    ) -> SkillExecution:
        return SkillExecution(
            task_id=task.task_id,
            skill_id=skill.definition.skill_id,
            skill_version=skill.definition.version,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            provider=llm_result.provider,
            model=llm_result.model,
            prompt_version=prompt_version,
            token_usage=TokenUsage(
                prompt_tokens=llm_result.prompt_tokens,
                completion_tokens=llm_result.completion_tokens,
                total_tokens=llm_result.total_tokens,
            ),
            latency_ms=llm_result.latency_ms,
            retry_count=retry_count,
            error=error,
        )

    def _failed_execution(
        self,
        *,
        task: AnalysisTask,
        skill: ExecutableSkill,
        started_at: datetime,
        prompt_version: str,
        retry_count: int,
        status: SkillExecutionStatus,
        error: str,
    ) -> SkillExecution:
        return SkillExecution(
            task_id=task.task_id,
            skill_id=skill.definition.skill_id,
            skill_version=skill.definition.version,
            started_at=started_at,
            finished_at=utc_now(),
            status=status,
            prompt_version=prompt_version,
            latency_ms=None,
            retry_count=retry_count,
            error=error,
        )

    def _result_record(
        self,
        *,
        execution: SkillExecution,
        skill: ExecutableSkill,
        payload: SkillResultPayload,
        llm_result: LLMStructuredResult,
        repair_attempted: bool,
    ) -> SkillResultRecord:
        return SkillResultRecord(
            execution_id=execution.execution_id,
            skill_id=skill.definition.skill_id,
            skill_version=skill.definition.version,
            conclusion=payload.conclusion,
            direction=payload.direction,
            confidence=payload.confidence,
            supporting_evidence_ids=payload.supporting_evidence_ids,
            contradicting_evidence_ids=payload.contradicting_evidence_ids,
            assumptions=payload.assumptions,
            risk_factors=payload.risk_factors,
            invalid_conditions=payload.invalid_conditions,
            missing_information=payload.missing_information,
            reasoning_summary=payload.reasoning_summary,
            raw_output={
                "parsed": llm_result.parsed.model_dump(mode="json"),
                "raw_response": llm_result.raw_response,
                "extracted_payload": llm_result.extracted_payload,
                "validation_error": llm_result.validation_error,
                "request_id": llm_result.request_id,
                "finish_reason": llm_result.raw_finish_reason,
                "repair_attempted": repair_attempted,
            },
        )
