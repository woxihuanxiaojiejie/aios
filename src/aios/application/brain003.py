from __future__ import annotations

import concurrent.futures
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError
from tenacity import Retrying, stop_after_attempt, wait_fixed

from aios.adapters.llm import LLMAdapter, LLMStructuredResult
from aios.kernel.base import utc_now
from aios.kernel.brain002 import AnalysisTask, SkillResult, TokenUsage
from aios.kernel.brain003 import (
    DiscussionExecution,
    DiscussionResult,
    DiscussionResultPayload,
)
from aios.kernel.enums import SkillExecutionStatus
from aios.kernel.errors import ReferenceIntegrityError
from aios.kernel.evidence import Evidence

DISCUSSION_PROMPT_VERSION = "discussion_v1"
DISCUSSION_OUTPUT_CONTRACT = (
    "Output exactly one flat JSON object with these top-level keys and no "
    "additional keys: conflicts, evidence_reviews, counter_arguments, "
    "revision_suggestions, discussion_summary, discussion_confidence. "
    "conflicts must be an array of objects, never a map, with skill_ids "
    "array, conflict_type string, description string, reason string, and "
    "evidence_ids array. evidence_reviews must be an array of objects, never "
    "a map, with skill_id string, sufficiency string, challenge string, "
    "referenced_evidence_ids array, and missing_evidence_categories array. "
    "counter_arguments must be an array of objects, never a map, with skill_id "
    "string, argument string, failure_mode string, and evidence_ids array. "
    "revision_suggestions must be an array of objects, never a map, with "
    "skill_id string, original_confidence number, suggested_confidence number, "
    "and reason string. discussion_summary must be a string. "
    "discussion_confidence must be a number from 0 to 1. Conflicts must "
    "identify direction, confidence, or evidence conflicts. Evidence reviews "
    "must challenge only evidence already cited or missing from the supplied "
    "Skill Results. Counter arguments must explain why each Skill Result might "
    "be wrong. Revision suggestions may only suggest confidence changes for "
    "this discussion output and must not modify stored weights. Do not output "
    "Buy, Sell, position sizing, orders, stop-loss, take-profit, Decision, "
    "Learning, or Settlement content."
)


@dataclass(frozen=True)
class DiscussionPrompt:
    system_prompt: str
    user_prompt: str
    prompt_version: str = DISCUSSION_PROMPT_VERSION


@dataclass(frozen=True)
class DiscussionOutcome:
    execution: DiscussionExecution
    result: DiscussionResult | None


class DiscussionValidator:
    def validate_inputs(
        self,
        *,
        task: AnalysisTask,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> None:
        if len(skill_results) < 1:
            msg = "Discussion requires at least one SkillResult"
            raise ValueError(msg)
        task_result_ids = set(task.evidence_ids)
        evidence_ids = {item.evidence_id for item in evidence}
        if task_result_ids:
            missing_task_ids = sorted(task_result_ids - evidence_ids)
            if missing_task_ids:
                msg = (
                    f"AnalysisTask references missing Evidence IDs: {missing_task_ids}"
                )
                raise ReferenceIntegrityError(msg)
        allowed_evidence_ids = (
            set(task.evidence_ids) if task.evidence_ids else evidence_ids
        )
        for result in skill_results:
            referenced_ids = set(result.supporting_evidence_ids) | set(
                result.contradicting_evidence_ids
            )
            unknown_ids = sorted(referenced_ids - allowed_evidence_ids)
            if unknown_ids:
                msg = (
                    f"SkillResult {result.result_id} references unknown evidence "
                    f"IDs: {unknown_ids}"
                )
                raise ReferenceIntegrityError(msg)

    def validate_output_references(
        self,
        *,
        payload: DiscussionResultPayload,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> None:
        skill_ids = {result.skill_id for result in skill_results}
        evidence_ids = {item.evidence_id for item in evidence}
        unknown_skill_ids: set[str] = set()
        unknown_evidence_ids: set[str] = set()

        for conflict in payload.conflicts:
            unknown_skill_ids.update(set(conflict.skill_ids) - skill_ids)
            unknown_evidence_ids.update(set(conflict.evidence_ids) - evidence_ids)
        for review in payload.evidence_reviews:
            if review.skill_id not in skill_ids:
                unknown_skill_ids.add(review.skill_id)
            unknown_evidence_ids.update(
                set(review.referenced_evidence_ids) - evidence_ids
            )
        for argument in payload.counter_arguments:
            if argument.skill_id not in skill_ids:
                unknown_skill_ids.add(argument.skill_id)
            unknown_evidence_ids.update(set(argument.evidence_ids) - evidence_ids)
        for suggestion in payload.revision_suggestions:
            if suggestion.skill_id not in skill_ids:
                unknown_skill_ids.add(suggestion.skill_id)

        errors: list[str] = []
        if unknown_skill_ids:
            errors.append(f"unknown discussion skill IDs: {sorted(unknown_skill_ids)}")
        if unknown_evidence_ids:
            errors.append(
                f"unknown discussion evidence IDs: {sorted(unknown_evidence_ids)}"
            )
        if errors:
            raise ReferenceIntegrityError("; ".join(errors))


class DiscussionService:
    def __init__(
        self,
        *,
        llm: LLMAdapter,
        model: str,
        timeout_seconds: float = 30.0,
        max_attempts: int = 2,
        validator: DiscussionValidator | None = None,
    ) -> None:
        self._llm = llm
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._validator = validator or DiscussionValidator()

    def discuss(
        self,
        *,
        task: AnalysisTask,
        skill_results: Iterable[SkillResult],
        evidence: Iterable[Evidence],
    ) -> DiscussionOutcome:
        started_at = utc_now()
        skill_result_tuple = tuple(skill_results)
        evidence_tuple = self._point_in_time_evidence(task, evidence)
        attempts = 0
        try:
            self._validator.validate_inputs(
                task=task,
                skill_results=skill_result_tuple,
                evidence=evidence_tuple,
            )
            prompt = self._build_prompt(
                task=task,
                skill_results=skill_result_tuple,
                evidence=evidence_tuple,
            )
            llm_result, payload, attempts = self._generate_valid_payload(
                prompt=prompt,
                skill_results=skill_result_tuple,
                evidence=evidence_tuple,
            )
            finished_at = utc_now()
            execution = self._execution_record(
                task=task,
                skill_results=skill_result_tuple,
                started_at=started_at,
                finished_at=finished_at,
                status=SkillExecutionStatus.SUCCEEDED,
                prompt_version=prompt.prompt_version,
                llm_result=llm_result,
                retry_count=attempts - 1,
                error=None,
            )
            result = DiscussionResult(
                discussion_execution_id=execution.discussion_execution_id,
                task_id=task.task_id,
                skill_result_ids=tuple(item.result_id for item in skill_result_tuple),
                **payload.model_dump(),
            )
            return DiscussionOutcome(execution=execution, result=result)
        except Exception as exc:
            return DiscussionOutcome(
                execution=DiscussionExecution(
                    task_id=task.task_id,
                    skill_result_ids=tuple(
                        item.result_id for item in skill_result_tuple
                    )
                    or ("unavailable",),
                    started_at=started_at,
                    finished_at=utc_now(),
                    status=SkillExecutionStatus.FAILED,
                    prompt_version=DISCUSSION_PROMPT_VERSION,
                    retry_count=max(attempts - 1, 0),
                    error=str(exc),
                ),
                result=None,
            )

    def _build_prompt(
        self,
        *,
        task: AnalysisTask,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> DiscussionPrompt:
        payload = {
            "task": {
                "task_id": task.task_id,
                "symbol": task.symbol,
                "market": task.market,
                "asset_type": task.asset_type,
                "horizon": task.horizon,
                "as_of": task.as_of.isoformat(),
                "evidence_ids": list(task.evidence_ids),
            },
            "skill_results": [
                {
                    "result_id": item.result_id,
                    "skill_id": item.skill_id,
                    "skill_version": item.skill_version,
                    "conclusion": item.conclusion,
                    "direction": item.direction.value,
                    "confidence": item.confidence,
                    "supporting_evidence_ids": list(item.supporting_evidence_ids),
                    "contradicting_evidence_ids": list(item.contradicting_evidence_ids),
                    "assumptions": list(item.assumptions),
                    "risk_factors": list(item.risk_factors),
                    "invalid_conditions": list(item.invalid_conditions),
                    "missing_information": list(item.missing_information),
                    "reasoning_summary": item.reasoning_summary,
                }
                for item in skill_results
            ],
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "evidence_type": item.evidence_type,
                    "source": item.source,
                    "available_at": item.available_at.isoformat(),
                    "summary": item.summary,
                    "reliability": item.reliability,
                    "metadata": item.metadata,
                }
                for item in evidence
            ],
        }
        return DiscussionPrompt(
            system_prompt=(
                "You are BRAIN-003 Discussion. One main Agent reviews multiple "
                "independent Skill Results from BRAIN-002. Do not call skills. "
                "Do not call providers. Do not browse. Do not fetch market data. "
                "Do not redo market analysis. Do not create trading decisions. "
                f"{DISCUSSION_OUTPUT_CONTRACT}"
            ),
            user_prompt=json.dumps(payload, ensure_ascii=True, sort_keys=True),
        )

    def _generate_valid_payload(
        self,
        *,
        prompt: DiscussionPrompt,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> tuple[LLMStructuredResult, DiscussionResultPayload, int]:
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
                        response_schema=DiscussionResultPayload,
                        temperature=0.0,
                    )
                )

            return retryer(attempt)

        try:
            llm_result = generate(prompt.system_prompt, prompt.user_prompt)
            payload = self._validated_payload(llm_result.parsed)
            self._validator.validate_output_references(
                payload=payload,
                skill_results=skill_results,
                evidence=evidence,
            )
            return llm_result, payload, attempts
        except Exception as first_exc:
            if not self._is_repairable_response_error(first_exc):
                raise
            repair_prompt = self._repair_prompt(prompt=prompt, error=first_exc)
            repaired_result = generate(
                repair_prompt.system_prompt,
                repair_prompt.user_prompt,
            )
            repaired_payload = self._validated_payload(repaired_result.parsed)
            self._validator.validate_output_references(
                payload=repaired_payload,
                skill_results=skill_results,
                evidence=evidence,
            )
            return repaired_result, repaired_payload, attempts

    def _repair_prompt(
        self,
        *,
        prompt: DiscussionPrompt,
        error: Exception,
    ) -> DiscussionPrompt:
        repair_payload = {
            "repair_instruction": (
                "Do not redo the discussion. Preserve the original discussion "
                "semantics and only repair structure, field names, types, and "
                "input Skill/Evidence ID references. Return only JSON matching "
                "DiscussionResultPayload."
            ),
            "required_top_level_keys": [
                "conflicts",
                "evidence_reviews",
                "counter_arguments",
                "revision_suggestions",
                "discussion_summary",
                "discussion_confidence",
            ],
            "field_types": {
                "conflicts": (
                    "array of objects with skill_ids, conflict_type, "
                    "description, reason, evidence_ids; never a map"
                ),
                "evidence_reviews": (
                    "array of objects with skill_id, sufficiency, challenge, "
                    "referenced_evidence_ids, missing_evidence_categories; "
                    "never a map"
                ),
                "counter_arguments": (
                    "array of objects with skill_id, argument, failure_mode, "
                    "evidence_ids; never a map"
                ),
                "revision_suggestions": (
                    "array of objects with skill_id, original_confidence, "
                    "suggested_confidence, reason; never a map"
                ),
                "discussion_summary": "string",
                "discussion_confidence": "number from 0 to 1",
            },
            "original_user_prompt": prompt.user_prompt,
            "original_raw_response": getattr(error, "raw_response", None),
            "original_extracted_payload": getattr(
                error,
                "extracted_payload",
                None,
            ),
            "validation_error": getattr(error, "validation_error", None) or str(error),
        }
        return DiscussionPrompt(
            system_prompt=(
                f"{prompt.system_prompt}\n"
                "The previous response failed DiscussionResultPayload validation. "
                "Do not redo the discussion. Only repair JSON structure and valid "
                "references. Return only JSON matching DiscussionResultPayload."
            ),
            user_prompt=json.dumps(repair_payload, ensure_ascii=True, sort_keys=True),
            prompt_version=prompt.prompt_version,
        )

    def _is_repairable_response_error(self, error: Exception) -> bool:
        return isinstance(error, ValueError | ValidationError) or any(
            getattr(error, attribute, None) is not None
            for attribute in ("raw_response", "extracted_payload", "validation_error")
        )

    def _validated_payload(self, parsed: BaseModel) -> DiscussionResultPayload:
        try:
            return DiscussionResultPayload.model_validate(parsed.model_dump())
        except ValidationError as exc:
            msg = f"DiscussionResultPayload validation failed: {exc}"
            raise ValueError(msg) from exc

    def _point_in_time_evidence(
        self,
        task: AnalysisTask,
        evidence: Iterable[Evidence],
    ) -> tuple[Evidence, ...]:
        evidence_by_id = {item.evidence_id: item for item in evidence}
        if task.evidence_ids:
            ordered_evidence = [
                evidence_by_id[evidence_id]
                for evidence_id in task.evidence_ids
                if evidence_id in evidence_by_id
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
            msg = f"Discussion execution timed out after {self._timeout_seconds}s"
            raise TimeoutError(msg) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _execution_record(
        self,
        *,
        task: AnalysisTask,
        skill_results: tuple[SkillResult, ...],
        started_at: datetime,
        finished_at: datetime,
        status: SkillExecutionStatus,
        prompt_version: str,
        llm_result: LLMStructuredResult,
        retry_count: int,
        error: str | None,
    ) -> DiscussionExecution:
        return DiscussionExecution(
            task_id=task.task_id,
            skill_result_ids=tuple(item.result_id for item in skill_results),
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
            raw_response=llm_result.raw_response,
            parsed_response=llm_result.parsed.model_dump(mode="json"),
            error=error,
        )


class DiscussionRepository:
    """Protocol-shaped wrapper for storage implementations that save discussions."""

    def __init__(self, storage: Any) -> None:
        self._storage = storage

    def save(self, outcome: DiscussionOutcome) -> None:
        self._storage.save(outcome.execution)
        if outcome.result is not None:
            self._storage.save(outcome.result)
