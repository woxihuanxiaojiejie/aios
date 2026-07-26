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
from aios.kernel.brain003 import DiscussionResult
from aios.kernel.brain004 import (
    DecisionExecution,
    DecisionResult,
    DecisionResultPayload,
)
from aios.kernel.enums import SkillExecutionStatus
from aios.kernel.errors import ReferenceIntegrityError
from aios.kernel.evidence import Evidence

DECISION_PROMPT_VERSION = "decision_v1"
DECISION_OUTPUT_CONTRACT = (
    "Output exactly one flat JSON object with these top-level keys and no "
    "additional keys: direction, confidence, action, reasoning, "
    "supporting_skills, opposing_skills, discussion_refs, evidence_refs, risks, "
    "rejected_directions, decision_summary. direction must be one of bullish, "
    "bearish, neutral, no_trade. confidence must be a number from 0 to 1. "
    "action must be one of buy, sell, hold, observe, no_trade. reasoning must "
    "be an array of objects with reason string, skill_ids array, "
    "discussion_refs array, and evidence_ids array. supporting_skills and "
    "opposing_skills must contain only supplied Skill IDs. discussion_refs "
    "must name supplied Discussion fields such as discussion_summary, "
    "conflict:<skill_id>:<skill_id>, evidence_review:<skill_id>, "
    "counter_argument:<skill_id>, or revision:<skill_id>. evidence_refs and "
    "nested evidence_ids must contain only supplied Evidence IDs. risks must "
    "be an array of objects with risk, uncertainty, invalid_condition, and "
    "evidence_ids. rejected_directions must explain why unselected directions "
    "were rejected, and must not include the selected direction. Every reason "
    "must be traceable to supplied skills, discussion refs, or evidence. Do "
    "not call skills. Do not browse. Do not fetch news or market data. Do not "
    "redo market analysis. Do not modify weights. Do not perform Learning, "
    "Settlement, Broker actions, automatic order placement, position sizing, "
    "stop-loss, or take-profit planning."
)


@dataclass(frozen=True)
class DecisionPrompt:
    system_prompt: str
    user_prompt: str
    prompt_version: str = DECISION_PROMPT_VERSION


@dataclass(frozen=True)
class DecisionOutcome:
    execution: DecisionExecution
    result: DecisionResult | None


class DecisionValidator:
    def validate_inputs(
        self,
        *,
        task: AnalysisTask,
        skill_results: tuple[SkillResult, ...],
        discussion_result: DiscussionResult,
        evidence: tuple[Evidence, ...],
    ) -> None:
        if len(skill_results) < 1:
            msg = "Decision requires at least one SkillResult"
            raise ValueError(msg)
        if discussion_result.task_id != task.task_id:
            msg = "DiscussionResult task_id must match AnalysisTask task_id"
            raise ReferenceIntegrityError(msg)

        skill_result_ids = {item.result_id for item in skill_results}
        discussion_skill_result_ids = set(discussion_result.skill_result_ids)
        unknown_discussion_result_ids = sorted(
            discussion_skill_result_ids - skill_result_ids
        )
        if unknown_discussion_result_ids:
            msg = f"unknown Discussion SkillResult IDs: {unknown_discussion_result_ids}"
            raise ReferenceIntegrityError(msg)

        evidence_ids = {item.evidence_id for item in evidence}
        if task.evidence_ids:
            missing_task_ids = sorted(set(task.evidence_ids) - evidence_ids)
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

        discussion_evidence_ids = self._discussion_evidence_ids(discussion_result)
        unknown_discussion_evidence_ids = sorted(
            discussion_evidence_ids - allowed_evidence_ids
        )
        if unknown_discussion_evidence_ids:
            msg = (
                "DiscussionResult references unknown evidence IDs: "
                f"{unknown_discussion_evidence_ids}"
            )
            raise ReferenceIntegrityError(msg)

    def validate_output_references(
        self,
        *,
        payload: DecisionResultPayload,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> None:
        skill_ids = {item.skill_id for item in skill_results}
        evidence_ids = {item.evidence_id for item in evidence}
        unknown_skill_ids: set[str] = set()
        unknown_evidence_ids: set[str] = set()

        unknown_skill_ids.update(set(payload.supporting_skills) - skill_ids)
        unknown_skill_ids.update(set(payload.opposing_skills) - skill_ids)
        unknown_evidence_ids.update(set(payload.evidence_refs) - evidence_ids)

        for reason in payload.reasoning:
            unknown_skill_ids.update(set(reason.skill_ids) - skill_ids)
            unknown_evidence_ids.update(set(reason.evidence_ids) - evidence_ids)
        for risk in payload.risks:
            unknown_evidence_ids.update(set(risk.evidence_ids) - evidence_ids)
        for rejection in payload.rejected_directions:
            unknown_skill_ids.update(set(rejection.skill_ids) - skill_ids)
            unknown_evidence_ids.update(set(rejection.evidence_ids) - evidence_ids)

        errors: list[str] = []
        if unknown_skill_ids:
            errors.append(f"unknown decision skill IDs: {sorted(unknown_skill_ids)}")
        if unknown_evidence_ids:
            errors.append(
                f"unknown decision evidence IDs: {sorted(unknown_evidence_ids)}"
            )
        if errors:
            raise ReferenceIntegrityError("; ".join(errors))

    def _discussion_evidence_ids(self, discussion_result: DiscussionResult) -> set[str]:
        evidence_ids: set[str] = set()
        for conflict in discussion_result.conflicts:
            evidence_ids.update(conflict.evidence_ids)
        for review in discussion_result.evidence_reviews:
            evidence_ids.update(review.referenced_evidence_ids)
        for argument in discussion_result.counter_arguments:
            evidence_ids.update(argument.evidence_ids)
        return evidence_ids


class DecisionService:
    def __init__(
        self,
        *,
        llm: LLMAdapter,
        model: str,
        timeout_seconds: float = 30.0,
        max_attempts: int = 2,
        validator: DecisionValidator | None = None,
    ) -> None:
        self._llm = llm
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._validator = validator or DecisionValidator()

    def decide(
        self,
        *,
        task: AnalysisTask,
        skill_results: Iterable[SkillResult],
        discussion_result: DiscussionResult,
        evidence: Iterable[Evidence],
    ) -> DecisionOutcome:
        started_at = utc_now()
        skill_result_tuple = tuple(skill_results)
        evidence_tuple = self._point_in_time_evidence(task, evidence)
        attempts = 0
        try:
            self._validator.validate_inputs(
                task=task,
                skill_results=skill_result_tuple,
                discussion_result=discussion_result,
                evidence=evidence_tuple,
            )
            prompt = self._build_prompt(
                task=task,
                skill_results=skill_result_tuple,
                discussion_result=discussion_result,
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
                discussion_result=discussion_result,
                evidence=evidence_tuple,
                started_at=started_at,
                finished_at=finished_at,
                status=SkillExecutionStatus.SUCCEEDED,
                prompt_version=prompt.prompt_version,
                llm_result=llm_result,
                retry_count=attempts - 1,
                error=None,
            )
            result = DecisionResult(
                decision_execution_id=execution.decision_execution_id,
                task_id=task.task_id,
                discussion_result_id=discussion_result.discussion_result_id,
                skill_result_ids=tuple(item.result_id for item in skill_result_tuple),
                **payload.model_dump(),
            )
            return DecisionOutcome(execution=execution, result=result)
        except Exception as exc:
            return DecisionOutcome(
                execution=DecisionExecution(
                    task_id=task.task_id,
                    discussion_result_id=discussion_result.discussion_result_id,
                    skill_result_ids=tuple(
                        item.result_id for item in skill_result_tuple
                    )
                    or ("unavailable",),
                    evidence_ids=tuple(item.evidence_id for item in evidence_tuple)
                    or ("unavailable",),
                    started_at=started_at,
                    finished_at=utc_now(),
                    status=SkillExecutionStatus.FAILED,
                    prompt_version=DECISION_PROMPT_VERSION,
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
        discussion_result: DiscussionResult,
        evidence: tuple[Evidence, ...],
    ) -> DecisionPrompt:
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
            "discussion_result": {
                "discussion_result_id": discussion_result.discussion_result_id,
                "skill_result_ids": list(discussion_result.skill_result_ids),
                "conflicts": [
                    item.model_dump(mode="json") for item in discussion_result.conflicts
                ],
                "evidence_reviews": [
                    item.model_dump(mode="json")
                    for item in discussion_result.evidence_reviews
                ],
                "counter_arguments": [
                    item.model_dump(mode="json")
                    for item in discussion_result.counter_arguments
                ],
                "revision_suggestions": [
                    item.model_dump(mode="json")
                    for item in discussion_result.revision_suggestions
                ],
                "discussion_summary": discussion_result.discussion_summary,
                "discussion_confidence": discussion_result.discussion_confidence,
            },
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
        return DecisionPrompt(
            system_prompt=(
                "You are BRAIN-004 Decision. Produce the final auditable "
                "investment decision from BRAIN-001 Evidence, BRAIN-002 Skill "
                "Results, and BRAIN-003 Discussion Result only. "
                f"{DECISION_OUTPUT_CONTRACT}"
            ),
            user_prompt=json.dumps(payload, ensure_ascii=True, sort_keys=True),
        )

    def _generate_valid_payload(
        self,
        *,
        prompt: DecisionPrompt,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> tuple[LLMStructuredResult, DecisionResultPayload, int]:
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
                        response_schema=DecisionResultPayload,
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
        prompt: DecisionPrompt,
        error: Exception,
    ) -> DecisionPrompt:
        repair_payload = {
            "repair_instruction": (
                "Do not redo the decision. Preserve the original final decision "
                "semantics and only repair structure, field names, types, and "
                "input Skill/Evidence ID references. Return only JSON matching "
                "DecisionResultPayload."
            ),
            "required_top_level_keys": [
                "direction",
                "confidence",
                "action",
                "reasoning",
                "supporting_skills",
                "opposing_skills",
                "discussion_refs",
                "evidence_refs",
                "risks",
                "rejected_directions",
                "decision_summary",
            ],
            "original_user_prompt": prompt.user_prompt,
            "original_raw_response": getattr(error, "raw_response", None),
            "original_extracted_payload": getattr(
                error,
                "extracted_payload",
                None,
            ),
            "validation_error": getattr(error, "validation_error", None) or str(error),
        }
        return DecisionPrompt(
            system_prompt=(
                f"{prompt.system_prompt}\n"
                "The previous response failed DecisionResultPayload validation. "
                "Do not redo the decision. Only repair JSON structure and valid "
                "references. Return only JSON matching DecisionResultPayload."
            ),
            user_prompt=json.dumps(repair_payload, ensure_ascii=True, sort_keys=True),
            prompt_version=prompt.prompt_version,
        )

    def _is_repairable_response_error(self, error: Exception) -> bool:
        return isinstance(error, ValueError | ValidationError) or any(
            getattr(error, attribute, None) is not None
            for attribute in ("raw_response", "extracted_payload", "validation_error")
        )

    def _validated_payload(self, parsed: BaseModel) -> DecisionResultPayload:
        try:
            return DecisionResultPayload.model_validate(parsed.model_dump())
        except ValidationError as exc:
            msg = f"DecisionResultPayload validation failed: {exc}"
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
            msg = f"Decision execution timed out after {self._timeout_seconds}s"
            raise TimeoutError(msg) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _execution_record(
        self,
        *,
        task: AnalysisTask,
        skill_results: tuple[SkillResult, ...],
        discussion_result: DiscussionResult,
        evidence: tuple[Evidence, ...],
        started_at: datetime,
        finished_at: datetime,
        status: SkillExecutionStatus,
        prompt_version: str,
        llm_result: LLMStructuredResult,
        retry_count: int,
        error: str | None,
    ) -> DecisionExecution:
        return DecisionExecution(
            task_id=task.task_id,
            discussion_result_id=discussion_result.discussion_result_id,
            skill_result_ids=tuple(item.result_id for item in skill_results),
            evidence_ids=tuple(item.evidence_id for item in evidence),
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


class DecisionRepository:
    """Protocol-shaped wrapper for storage implementations that save decisions."""

    def __init__(self, storage: Any) -> None:
        self._storage = storage

    def save(self, outcome: DecisionOutcome) -> None:
        self._storage.save(outcome.execution)
        if outcome.result is not None:
            self._storage.save(outcome.result)
