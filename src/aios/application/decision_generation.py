from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from aios.adapters.llm import LLMAdapter, LLMStructuredResult
from aios.integrations.litellm.errors import LLMStructuredOutputError
from aios.integrations.litellm.schemas import DecisionDraft
from aios.kernel.decision import Decision
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.prompts.decision_v1 import build_decision_prompt, prompt_hash
from aios.prompts.versions import DECISION_V1
from aios.workflows.decision_lifecycle import DecisionLifecycleService


class DecisionEvidenceValidationError(Exception):
    """Raised when model-selected Evidence is not allowed."""


class UnsupportedPromptVersionError(Exception):
    """Raised when an Experiment references an unsupported prompt version."""


@dataclass(frozen=True)
class GenerationMetadata:
    provider: str
    model: str
    prompt_version: str
    prompt_hash: str
    evidence_snapshot_hash: str
    temperature: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int
    request_id: str | None
    raw_finish_reason: str | None


@dataclass(frozen=True)
class LLMGenerationRecord:
    decision_id: str
    experiment_id: str
    provider: str
    model: str
    prompt_version: str
    prompt_hash: str
    evidence_snapshot_hash: str
    temperature: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int
    created_at: datetime


class GenerationRecorder(Protocol):
    def save_generation_record(self, record: LLMGenerationRecord) -> None:
        """Persist bounded LLM generation metadata."""


@dataclass(frozen=True)
class DecisionGenerationResult:
    decision: Decision
    generation: GenerationMetadata


class DecisionGenerationService:
    def __init__(
        self,
        *,
        lifecycle: DecisionLifecycleService,
        llm_adapter: LLMAdapter,
        generation_recorder: GenerationRecorder | None = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._llm_adapter = llm_adapter
        self._generation_recorder = generation_recorder

    def generate(
        self,
        *,
        experiment_id: str,
        symbol: str,
        horizon: str,
    ) -> DecisionGenerationResult:
        experiment = self._lifecycle.get_entity(Experiment, experiment_id)
        if experiment.prompt_version != DECISION_V1:
            msg = f"Unsupported prompt version: {experiment.prompt_version}"
            raise UnsupportedPromptVersionError(msg)

        evidence = [
            self._lifecycle.get_entity(Evidence, evidence_id)
            for evidence_id in experiment.evidence_ids
        ]
        prompt = build_decision_prompt(
            experiment=experiment,
            evidence=evidence,
            symbol=symbol,
            horizon=horizon,
        )
        temperature = self._temperature(experiment)
        llm_result = self._llm_adapter.generate_structured(
            model=experiment.model,
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            response_schema=DecisionDraft,
            temperature=temperature,
        )
        draft = self._draft(llm_result)
        self._validate_draft(draft, experiment, horizon)
        created_at = datetime.now(UTC)
        decision = Decision(
            experiment_id=experiment.experiment_id,
            symbol=symbol,
            action=draft.action,
            horizon=horizon,
            confidence=draft.confidence,
            expected_return=draft.expected_return,
            max_expected_loss=draft.max_expected_loss,
            evidence_ids=draft.supporting_evidence_ids,
            reasoning_summary=self._reasoning_summary(draft),
            created_at=created_at,
            valid_until=created_at + self._horizon_delta(horizon),
        )
        saved = self._lifecycle.create_decision(decision)
        generation = GenerationMetadata(
            provider=llm_result.provider,
            model=llm_result.model,
            prompt_version=experiment.prompt_version,
            prompt_hash=prompt_hash(prompt),
            evidence_snapshot_hash=prompt.evidence_snapshot_hash,
            temperature=temperature,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            total_tokens=llm_result.total_tokens,
            latency_ms=llm_result.latency_ms,
            request_id=llm_result.request_id,
            raw_finish_reason=llm_result.raw_finish_reason,
        )
        self._record(saved, generation)
        return DecisionGenerationResult(decision=saved, generation=generation)

    def _draft(self, llm_result: LLMStructuredResult) -> DecisionDraft:
        if not isinstance(llm_result.parsed, DecisionDraft):
            msg = "LLM structured result did not contain a DecisionDraft"
            raise LLMStructuredOutputError(msg)
        return llm_result.parsed

    def _validate_draft(
        self,
        draft: DecisionDraft,
        experiment: Experiment,
        horizon: str,
    ) -> None:
        if draft.horizon != horizon:
            msg = "DecisionDraft horizon must match the request horizon"
            raise DecisionEvidenceValidationError(msg)
        if not set(draft.supporting_evidence_ids).issubset(
            set(experiment.evidence_ids)
        ):
            msg = "DecisionDraft evidence must be a subset of Experiment evidence_ids"
            raise DecisionEvidenceValidationError(msg)

    def _temperature(self, experiment: Experiment) -> float:
        value = experiment.parameters.get("temperature", 0)
        temperature = float(value)
        if not 0 <= temperature <= 1:
            msg = "temperature must be between 0 and 1"
            raise ValueError(msg)
        return temperature

    def _horizon_delta(self, horizon: str) -> timedelta:
        if horizon.endswith("d") and horizon[:-1].isdigit():
            return timedelta(days=int(horizon[:-1]))
        if horizon.endswith("w") and horizon[:-1].isdigit():
            return timedelta(weeks=int(horizon[:-1]))
        msg = "horizon must use natural time such as 1d, 3d, or 1w"
        raise ValueError(msg)

    def _reasoning_summary(self, draft: DecisionDraft) -> str:
        parts = [draft.reasoning_summary]
        if draft.risk_factors:
            parts.append(f"Risk factors: {'; '.join(draft.risk_factors)}.")
        if draft.invalidation_conditions:
            parts.append(
                f"Invalidation conditions: {'; '.join(draft.invalidation_conditions)}."
            )
        return " ".join(parts)

    def _record(self, decision: Decision, generation: GenerationMetadata) -> None:
        if self._generation_recorder is None:
            return
        self._generation_recorder.save_generation_record(
            LLMGenerationRecord(
                decision_id=decision.decision_id,
                experiment_id=decision.experiment_id,
                provider=generation.provider,
                model=generation.model,
                prompt_version=generation.prompt_version,
                prompt_hash=generation.prompt_hash,
                evidence_snapshot_hash=generation.evidence_snapshot_hash,
                temperature=generation.temperature,
                prompt_tokens=generation.prompt_tokens,
                completion_tokens=generation.completion_tokens,
                total_tokens=generation.total_tokens,
                latency_ms=generation.latency_ms,
                created_at=decision.created_at,
            )
        )
