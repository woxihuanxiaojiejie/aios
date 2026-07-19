from __future__ import annotations

from datetime import timedelta

import pytest
from tests.factories import make_evidence, make_experiment
from tests.llm_helpers import CapturingGenerationRecorder, FakeLLMAdapter

from aios.application.decision_generation import (
    DecisionEvidenceValidationError,
    DecisionGenerationService,
    UnsupportedPromptVersionError,
)
from aios.integrations.litellm.errors import LLMStructuredOutputError, LLMUpstreamError
from aios.integrations.litellm.schemas import DecisionDraft
from aios.kernel.decision import Decision
from aios.kernel.enums import Action
from aios.kernel.errors import MissingEntityError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def seed_service(
    *,
    llm: FakeLLMAdapter | None = None,
    experiment: Experiment | None = None,
    evidence: Evidence | None = None,
    recorder: CapturingGenerationRecorder | None = None,
) -> tuple[DecisionGenerationService, DecisionLifecycleService, FakeLLMAdapter]:
    storage = InMemoryStorage()
    lifecycle = DecisionLifecycleService(storage)
    evidence = evidence or make_evidence()
    experiment = experiment or make_experiment(
        evidence.evidence_id,
        prompt_version="decision-v1",
    )
    lifecycle.register_evidence(evidence)
    lifecycle.start_experiment(experiment)
    fake_llm = llm or FakeLLMAdapter()
    service = DecisionGenerationService(
        lifecycle=lifecycle,
        llm_adapter=fake_llm,
        generation_recorder=recorder,
    )
    return service, lifecycle, fake_llm


def test_generate_decision_success_reuses_lifecycle_and_records_metadata() -> None:
    recorder = CapturingGenerationRecorder([])
    service, lifecycle, llm = seed_service(recorder=recorder)

    result = service.generate(
        experiment_id="ex_00000000-0000-0000-0000-000000000001",
        symbol="NVDA",
        horizon="1d",
    )

    stored = lifecycle.get_entity(Decision, result.decision.decision_id)
    assert stored == result.decision
    assert result.decision.valid_until == result.decision.created_at + timedelta(days=1)
    assert llm.calls[0]["model"] == "model-v1"
    assert llm.calls[0]["temperature"] == 0
    assert recorder.records[0].decision_id == result.decision.decision_id
    assert result.generation.prompt_version == "decision-v1"


def test_generate_rejects_missing_experiment() -> None:
    service, _lifecycle, _llm = seed_service()

    with pytest.raises(MissingEntityError):
        service.generate(experiment_id="ex_missing", symbol="NVDA", horizon="1d")


def test_generate_rejects_missing_evidence() -> None:
    storage = InMemoryStorage()
    lifecycle = DecisionLifecycleService(storage)
    experiment = make_experiment("ev_missing", prompt_version="decision-v1")
    storage.save(experiment)
    service = DecisionGenerationService(
        lifecycle=lifecycle,
        llm_adapter=FakeLLMAdapter(),
    )

    with pytest.raises(MissingEntityError):
        service.generate(
            experiment_id=experiment.experiment_id,
            symbol="NVDA",
            horizon="1d",
        )


def test_generate_rejects_unsupported_prompt_version() -> None:
    experiment = make_experiment(
        "ev_00000000-0000-0000-0000-000000000001",
        prompt_version="prompt-v1",
    )
    service, _lifecycle, _llm = seed_service(experiment=experiment)

    with pytest.raises(UnsupportedPromptVersionError):
        service.generate(
            experiment_id=experiment.experiment_id,
            symbol="NVDA",
            horizon="1d",
        )


def test_generate_rejects_model_evidence_not_in_experiment() -> None:
    draft = DecisionDraft(
        action=Action.HOLD,
        confidence=0.5,
        expected_return=0,
        max_expected_loss=0.01,
        horizon="1d",
        reasoning_summary="Uses evidence that was not provided.",
        supporting_evidence_ids=["ev_fake"],
        risk_factors=[],
        invalidation_conditions=[],
    )
    service, _lifecycle, _llm = seed_service(llm=FakeLLMAdapter(draft=draft))

    with pytest.raises(DecisionEvidenceValidationError):
        service.generate(
            experiment_id="ex_00000000-0000-0000-0000-000000000001",
            symbol="NVDA",
            horizon="1d",
        )


def test_generate_rejects_draft_horizon_mismatch() -> None:
    draft = DecisionDraft(
        action=Action.HOLD,
        confidence=0.5,
        expected_return=0,
        max_expected_loss=0.01,
        horizon="3d",
        reasoning_summary="Different horizon.",
        supporting_evidence_ids=["ev_00000000-0000-0000-0000-000000000001"],
        risk_factors=[],
        invalidation_conditions=[],
    )
    service, _lifecycle, _llm = seed_service(llm=FakeLLMAdapter(draft=draft))

    with pytest.raises(DecisionEvidenceValidationError):
        service.generate(
            experiment_id="ex_00000000-0000-0000-0000-000000000001",
            symbol="NVDA",
            horizon="1d",
        )


def test_generate_propagates_llm_failures_without_saving() -> None:
    service, lifecycle, _llm = seed_service(
        llm=FakeLLMAdapter(error=LLMUpstreamError("provider failed"))
    )

    with pytest.raises(LLMUpstreamError):
        service.generate(
            experiment_id="ex_00000000-0000-0000-0000-000000000001",
            symbol="NVDA",
            horizon="1d",
        )

    assert lifecycle.list_entities(Decision) == []


def test_generate_reads_only_temperature_parameter() -> None:
    experiment = make_experiment(
        "ev_00000000-0000-0000-0000-000000000001",
        prompt_version="decision-v1",
    ).model_copy(update={"parameters": {"temperature": 0.2, "top_p": 0.9}})
    service, _lifecycle, llm = seed_service(experiment=experiment)

    service.generate(
        experiment_id=experiment.experiment_id,
        symbol="NVDA",
        horizon="1d",
    )

    assert llm.calls[0]["temperature"] == 0.2
    assert "top_p" not in llm.calls[0]


def test_generate_rejects_invalid_temperature() -> None:
    experiment = make_experiment(
        "ev_00000000-0000-0000-0000-000000000001",
        prompt_version="decision-v1",
    ).model_copy(update={"parameters": {"temperature": 2}})
    service, _lifecycle, _llm = seed_service(experiment=experiment)

    with pytest.raises(ValueError):
        service.generate(
            experiment_id=experiment.experiment_id,
            symbol="NVDA",
            horizon="1d",
        )


def test_generate_wraps_non_draft_model_output() -> None:
    class BadLLM(FakeLLMAdapter):
        def generate_structured(self, **kwargs: object):  # type: ignore[no-untyped-def]
            result = super().generate_structured(**kwargs)
            return result.model_copy(update={"parsed": {"not": "a draft"}})

    service, _lifecycle, _llm = seed_service(llm=BadLLM())

    with pytest.raises(LLMStructuredOutputError):
        service.generate(
            experiment_id="ex_00000000-0000-0000-0000-000000000001",
            symbol="NVDA",
            horizon="1d",
        )
