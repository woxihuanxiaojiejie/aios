from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from aios.adapters.llm import LLMStructuredResult
from aios.application.brain002 import (
    SkillExecutor,
    SkillInput,
    SkillPrompt,
)
from aios.kernel.brain002 import (
    AnalysisTask,
    SkillDefinition,
    SkillResultPayload,
)
from aios.kernel.enums import SkillDirection, SkillExecutionStatus
from aios.kernel.evidence import Evidence


def now() -> datetime:
    return datetime.now(UTC)


def evidence(evidence_id: str = "ev_price") -> Evidence:
    available_at = now()
    return Evidence(
        evidence_id=evidence_id,
        evidence_type="price",
        source="brain001",
        symbols=("000001",),
        published_at=available_at - timedelta(minutes=1),
        available_at=available_at,
        summary="price trend evidence",
        reliability=0.9,
        content_hash=f"hash-{evidence_id}",
    )


def task() -> AnalysisTask:
    return AnalysisTask(
        symbol="000001",
        market="cn",
        asset_type="stock",
        horizon="swing",
        as_of=now() + timedelta(minutes=1),
        evidence_ids=("ev_price",),
    )


def definition(skill_id: str) -> SkillDefinition:
    return SkillDefinition(
        skill_id=skill_id,
        name=skill_id.replace("_", " ").title(),
        version="1.0.0",
        description=f"{skill_id} analysis",
        supported_markets=("cn",),
        supported_asset_types=("stock",),
        supported_horizons=("swing",),
        required_evidence_types=("price",),
        input_schema={"type": "object"},
        output_schema=SkillResultPayload.model_json_schema(),
    )


class FakeSkill:
    response_schema = SkillResultPayload
    prompt_version = "fake_skill_v1"

    def __init__(self, skill_id: str) -> None:
        self.definition = definition(skill_id)
        self.seen_inputs: list[SkillInput] = []

    def build_prompt(self, skill_input: SkillInput) -> SkillPrompt:
        self.seen_inputs.append(skill_input)
        return SkillPrompt(
            system_prompt=f"Run {self.definition.skill_id}.",
            user_prompt=f"Analyze {self.definition.skill_id} for {skill_input.symbol}.",
            prompt_version=self.prompt_version,
        )


class InvalidPayload(BaseModel):
    text: str


class InvalidSkill(FakeSkill):
    response_schema = InvalidPayload


class FakeLLM:
    def __init__(
        self,
        handler: Callable[[str], BaseModel],
    ) -> None:
        self._handler = handler
        self.calls: list[str] = []

    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        self.calls.append(user_prompt)
        parsed = self._handler(user_prompt)
        return LLMStructuredResult(
            parsed=parsed,
            provider="fake",
            model=model,
            prompt_tokens=10,
            completion_tokens=6,
            total_tokens=16,
            latency_ms=7,
            raw_finish_reason="stop",
            raw_response=parsed.model_dump_json(),
            extracted_payload=parsed.model_dump(mode="json"),
        )


def payload(direction: SkillDirection = SkillDirection.BULLISH) -> SkillResultPayload:
    return SkillResultPayload(
        conclusion="Trend is constructive.",
        direction=direction,
        confidence=0.7,
        supporting_evidence_ids=("ev_price",),
        contradicting_evidence_ids=(),
        assumptions=("Liquidity remains normal.",),
        risk_factors=("Trend may reverse.",),
        invalid_conditions=("Support breaks.",),
        missing_information=("Intraday flow.",),
        reasoning_summary="Price evidence supports the conclusion.",
    )


def test_executor_runs_skills_in_isolation_and_keeps_success_after_failure() -> None:
    good_skill = FakeSkill("technical_trend")
    bad_skill = FakeSkill("policy_impact")

    def handler(user_prompt: str) -> SkillResultPayload:
        if "policy_impact" in user_prompt:
            raise RuntimeError("provider failed")
        return payload()

    outcome = SkillExecutor(
        llm=FakeLLM(handler),
        model="fake/model",
        timeout_seconds=1,
        max_attempts=1,
    ).execute(task=task(), skills=(good_skill, bad_skill), evidence=(evidence(),))

    assert [result.skill_id for result in outcome.results] == ["technical_trend"]
    assert {execution.status for execution in outcome.executions} == {
        SkillExecutionStatus.SUCCEEDED,
        SkillExecutionStatus.FAILED,
    }
    assert good_skill.seen_inputs[0].skill_context == {}
    assert bad_skill.seen_inputs[0].skill_context == {}


def test_executor_records_retry_token_and_latency_metadata() -> None:
    attempts = 0

    def handler(user_prompt: str) -> SkillResultPayload:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary failure")
        return payload()

    outcome = SkillExecutor(
        llm=FakeLLM(handler),
        model="fake/model",
        timeout_seconds=1,
        max_attempts=2,
    ).execute(
        task=task(),
        skills=(FakeSkill("technical_trend"),),
        evidence=(evidence(),),
    )

    execution = outcome.executions[0]
    assert execution.status is SkillExecutionStatus.SUCCEEDED
    assert execution.provider == "fake"
    assert execution.model == "fake/model"
    assert execution.token_usage.total_tokens == 16
    assert execution.latency_ms is not None
    assert execution.retry_count == 1
    assert outcome.results[0].raw_output["parsed"]["direction"] == "bullish"


def test_executor_marks_timed_out_skill_without_result() -> None:
    def handler(user_prompt: str) -> SkillResultPayload:
        time.sleep(0.05)
        return payload()

    outcome = SkillExecutor(
        llm=FakeLLM(handler),
        model="fake/model",
        timeout_seconds=0.001,
        max_attempts=1,
    ).execute(
        task=task(),
        skills=(FakeSkill("technical_trend"),),
        evidence=(evidence(),),
    )

    assert outcome.results == ()
    assert outcome.executions[0].status is SkillExecutionStatus.TIMED_OUT
    assert "timed out" in str(outcome.executions[0].error)


def test_executor_rejects_outputs_that_do_not_match_skill_result_payload() -> None:
    outcome = SkillExecutor(
        llm=FakeLLM(lambda user_prompt: InvalidPayload(text="free text only")),
        model="fake/model",
        timeout_seconds=1,
        max_attempts=1,
    ).execute(
        task=task(),
        skills=(InvalidSkill("technical_trend"),),
        evidence=(evidence(),),
    )

    assert outcome.results == ()
    assert outcome.executions[0].status is SkillExecutionStatus.FAILED
    assert "SkillResultPayload" in str(outcome.executions[0].error)


def test_executor_rejects_nonexistent_evidence_id_and_repairs_once() -> None:
    calls = 0

    def handler(user_prompt: str) -> SkillResultPayload:
        nonlocal calls
        calls += 1
        if calls == 1:
            return payload().model_copy(
                update={"supporting_evidence_ids": ("ev_missing",)}
            )
        assert "ev_missing" in user_prompt
        assert "Do not redo the investment analysis" in user_prompt
        return payload()

    outcome = SkillExecutor(
        llm=FakeLLM(handler),
        model="fake/model",
        timeout_seconds=1,
        max_attempts=1,
    ).execute(
        task=task(),
        skills=(FakeSkill("technical_trend"),),
        evidence=(evidence(),),
    )

    assert calls == 2
    assert outcome.executions[0].status is SkillExecutionStatus.SUCCEEDED
    assert outcome.executions[0].retry_count == 1
    assert outcome.results[0].supporting_evidence_ids == ("ev_price",)
    assert outcome.results[0].raw_output["repair_attempted"] is True


def test_executor_fails_after_one_repair_retry() -> None:
    calls = 0

    def handler(user_prompt: str) -> SkillResultPayload:
        nonlocal calls
        calls += 1
        return payload().model_copy(update={"supporting_evidence_ids": ("ev_missing",)})

    outcome = SkillExecutor(
        llm=FakeLLM(handler),
        model="fake/model",
        timeout_seconds=1,
        max_attempts=1,
    ).execute(
        task=task(),
        skills=(FakeSkill("technical_trend"),),
        evidence=(evidence(),),
    )

    assert calls == 2
    assert outcome.results == ()
    assert outcome.executions[0].status is SkillExecutionStatus.FAILED
    assert "unknown supporting_evidence_ids" in str(outcome.executions[0].error)


def test_executor_single_skill_repair_failure_does_not_block_other_skills() -> None:
    def handler(user_prompt: str) -> SkillResultPayload:
        if "policy_impact" in user_prompt:
            return payload().model_copy(
                update={"supporting_evidence_ids": ("ev_missing",)}
            )
        return payload()

    outcome = SkillExecutor(
        llm=FakeLLM(handler),
        model="fake/model",
        timeout_seconds=1,
        max_attempts=1,
    ).execute(
        task=task(),
        skills=(FakeSkill("technical_trend"), FakeSkill("policy_impact")),
        evidence=(evidence(),),
    )

    assert [result.skill_id for result in outcome.results] == ["technical_trend"]
    assert [execution.status for execution in outcome.executions] == [
        SkillExecutionStatus.SUCCEEDED,
        SkillExecutionStatus.FAILED,
    ]
