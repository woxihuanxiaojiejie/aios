from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from aios.adapters.llm import LLMStructuredResult
from aios.application.brain004 import DecisionService
from aios.integrations.litellm.errors import LLMStructuredOutputError
from aios.kernel.brain002 import AnalysisTask, SkillResult
from aios.kernel.brain003 import DiscussionResult
from aios.kernel.brain004 import DecisionResultPayload
from aios.kernel.enums import Action, SkillDirection, SkillExecutionStatus
from aios.kernel.evidence import Evidence


class FakeLLM:
    def __init__(self, outcomes: list[LLMStructuredResult | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
                "temperature": temperature,
            }
        )
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_decision_service_generates_traceable_final_decision() -> None:
    payload = valid_decision_payload()
    llm = FakeLLM([structured_result(payload)])
    task = analysis_task()
    skill_results = brain002_results()
    discussion = discussion_result(skill_results)
    evidence = evidence_items()

    outcome = DecisionService(
        llm=llm,
        model="deepseek/deepseek-chat",
        timeout_seconds=5,
        max_attempts=1,
    ).decide(
        task=task,
        skill_results=skill_results,
        discussion_result=discussion,
        evidence=evidence,
    )

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.provider == "deepseek"
    assert outcome.execution.raw_response is not None
    assert outcome.execution.parsed_response["direction"] == "bullish"
    assert outcome.result is not None
    assert outcome.result.supporting_skills == ("technical_trend",)
    assert outcome.result.opposing_skills == ("announcement_risk",)
    assert outcome.result.evidence_refs == ("ev_price", "ev_announcement")
    assert outcome.result.rejected_directions[0].direction.value == "bearish"
    assert llm.calls[0]["response_schema"] is DecisionResultPayload
    assert "Do not call skills" in llm.calls[0]["system_prompt"]
    assert "Do not browse" in llm.calls[0]["system_prompt"]
    assert "Do not modify weights" in llm.calls[0]["system_prompt"]
    assert "discussion_result" in llm.calls[0]["user_prompt"]


def test_decision_service_repairs_structured_output_without_redeciding() -> None:
    malformed = LLMStructuredOutputError(
        "bad json",
        raw_response='{"summary":"bad"}',
        extracted_payload={"summary": "bad"},
        validation_error="missing direction",
        provider="deepseek",
        model="deepseek/deepseek-chat",
        latency_ms=3,
    )
    llm = FakeLLM([malformed, structured_result(valid_decision_payload())])

    outcome = DecisionService(
        llm=llm,
        model="deepseek/deepseek-chat",
        timeout_seconds=5,
        max_attempts=1,
    ).decide(
        task=analysis_task(),
        skill_results=brain002_results(),
        discussion_result=discussion_result(brain002_results()),
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.retry_count == 1
    assert outcome.result is not None
    assert "Do not redo the decision" in llm.calls[1]["system_prompt"]
    assert "original_raw_response" in llm.calls[1]["user_prompt"]


def test_decision_service_repairs_error_payload_with_non_json_values() -> None:
    malformed = LLMStructuredOutputError(
        "bad json",
        raw_response='{"action":"no_trade"}',
        extracted_payload={"action": Action.NO_TRADE},
        validation_error={"action": Action.NO_TRADE},
        provider="deepseek",
        model="deepseek/deepseek-v4-flash",
        latency_ms=3,
    )
    llm = FakeLLM([malformed, structured_result(valid_decision_payload())])

    outcome = DecisionService(
        llm=llm,
        model="deepseek/deepseek-v4-flash",
        timeout_seconds=5,
        max_attempts=1,
    ).decide(
        task=analysis_task(),
        skill_results=brain002_results(),
        discussion_result=discussion_result(brain002_results()),
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.retry_count == 1
    assert outcome.result is not None


def test_decision_service_repairs_field_info_validation_error() -> None:
    malformed = LLMStructuredOutputError(
        "bad json",
        raw_response='{"action":"no_trade"}',
        extracted_payload={"action": "no_trade"},
        validation_error={"action": Field(default="no_trade")},
        provider="deepseek",
        model="deepseek/deepseek-v4-pro",
        latency_ms=3,
    )
    llm = FakeLLM([malformed, structured_result(valid_decision_payload())])

    outcome = DecisionService(
        llm=llm,
        model="deepseek/deepseek-v4-pro",
        timeout_seconds=5,
        max_attempts=1,
    ).decide(
        task=analysis_task(),
        skill_results=brain002_results(),
        discussion_result=discussion_result(brain002_results()),
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.retry_count == 1
    assert outcome.result is not None


def test_decision_service_repairs_validation_error_with_enum_payload() -> None:
    class LooseDecisionPayload(BaseModel):
        direction: str
        confidence: float
        action: Action
        reasoning: list[dict[str, Any]]
        supporting_skills: list[str]
        opposing_skills: list[str]
        discussion_refs: list[str]
        evidence_refs: list[str]
        risks: list[dict[str, Any]]
        rejected_directions: list[dict[str, Any]]
        decision_summary: str

    invalid_parsed = LooseDecisionPayload.model_validate(
        valid_decision_payload()
        | {
            "action": Action.NO_TRADE,
            "supporting_skills": [],
            "opposing_skills": [],
        }
    )
    llm = FakeLLM(
        [
            LLMStructuredResult(
                parsed=invalid_parsed,
                provider="deepseek",
                model="deepseek/deepseek-v4-flash",
                raw_response=invalid_parsed.model_dump_json(),
                extracted_payload=invalid_parsed.model_dump(mode="json"),
                latency_ms=15,
            ),
            structured_result(valid_decision_payload()),
        ]
    )

    outcome = DecisionService(
        llm=llm,
        model="deepseek/deepseek-v4-flash",
        timeout_seconds=5,
        max_attempts=1,
    ).decide(
        task=analysis_task(),
        skill_results=brain002_results(),
        discussion_result=discussion_result(brain002_results()),
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.retry_count == 1
    assert outcome.result is not None
    assert "validation_error" in llm.calls[1]["user_prompt"]


def test_decision_service_rejects_missing_discussion_skill_result_reference() -> None:
    skill_results = brain002_results()
    discussion = discussion_result(skill_results).model_copy(
        update={"skill_result_ids": ("sr_missing",)}
    )

    outcome = DecisionService(
        llm=FakeLLM([structured_result(valid_decision_payload())]),
        model="deepseek/deepseek-chat",
    ).decide(
        task=analysis_task(),
        skill_results=skill_results,
        discussion_result=discussion,
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.FAILED
    assert outcome.result is None
    assert "unknown Discussion SkillResult IDs" in (outcome.execution.error or "")


def test_decision_service_rejects_output_references_outside_inputs() -> None:
    payload = valid_decision_payload()
    payload["evidence_refs"] = ["ev_unseen"]

    outcome = DecisionService(
        llm=FakeLLM([structured_result(payload)]),
        model="deepseek/deepseek-chat",
    ).decide(
        task=analysis_task(),
        skill_results=brain002_results(),
        discussion_result=discussion_result(brain002_results()),
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.FAILED
    assert outcome.result is None
    assert "unknown decision evidence IDs" in (outcome.execution.error or "")


def analysis_task() -> AnalysisTask:
    as_of = datetime.now(UTC)
    return AnalysisTask(
        task_id="at_example",
        symbol="000001.SZ",
        market="cn",
        asset_type="stock",
        horizon="swing",
        as_of=as_of,
        evidence_ids=("ev_price", "ev_announcement"),
    )


def brain002_results() -> tuple[SkillResult, ...]:
    return (
        SkillResult(
            result_id="sr_technical",
            execution_id="sx_technical",
            skill_id="technical_trend",
            skill_version="1.0.0",
            conclusion="Trend is bullish.",
            direction=SkillDirection.BULLISH,
            confidence=0.82,
            supporting_evidence_ids=("ev_price",),
            risk_factors=("Volume may fade.",),
            invalid_conditions=("MA20 breaks.",),
            missing_information=("Capital flow.",),
            reasoning_summary="MA20 and MACD support a bullish trend.",
            raw_output={"parsed": {"direction": "bullish"}},
        ),
        SkillResult(
            result_id="sr_announcement",
            execution_id="sx_announcement",
            skill_id="announcement_risk",
            skill_version="1.0.0",
            conclusion="Announcement risk is bearish.",
            direction=SkillDirection.BEARISH,
            confidence=0.76,
            supporting_evidence_ids=("ev_announcement",),
            risk_factors=("Risk may be priced in.",),
            invalid_conditions=("Company clarifies risk.",),
            missing_information=("Follow-up filing.",),
            reasoning_summary="Announcement risk conflicts with trend.",
            raw_output={"parsed": {"direction": "bearish"}},
        ),
    )


def discussion_result(skill_results: tuple[SkillResult, ...]) -> DiscussionResult:
    return DiscussionResult(
        discussion_result_id="dr_example",
        discussion_execution_id="dx_example",
        task_id="at_example",
        skill_result_ids=tuple(item.result_id for item in skill_results),
        conflicts=[
            {
                "skill_ids": ["technical_trend", "announcement_risk"],
                "conflict_type": "direction",
                "description": (
                    "Technical is bullish while announcement risk is bearish."
                ),
                "reason": "Announcement risk conflicts with trend analysis.",
                "evidence_ids": ["ev_price", "ev_announcement"],
            }
        ],
        evidence_reviews=[
            {
                "skill_id": "technical_trend",
                "sufficiency": "partial",
                "challenge": "Technical result lacks volume and capital flow checks.",
                "referenced_evidence_ids": ["ev_price"],
                "missing_evidence_categories": ["volume", "capital_flow"],
            }
        ],
        counter_arguments=[
            {
                "skill_id": "technical_trend",
                "argument": (
                    "The bullish trend may be wrong if announcement risk dominates."
                ),
                "failure_mode": "Risk disclosure overwhelms trend continuation.",
                "evidence_ids": ["ev_announcement"],
            }
        ],
        revision_suggestions=[
            {
                "skill_id": "technical_trend",
                "original_confidence": 0.82,
                "suggested_confidence": 0.7,
                "reason": "Announcement risk moderates bullish confidence.",
            }
        ],
        discussion_summary="The conflict should moderate but not veto the trend read.",
        discussion_confidence=0.68,
    )


def evidence_items() -> tuple[Evidence, ...]:
    as_of = datetime.now(UTC)
    return (
        Evidence(
            evidence_id="ev_price",
            evidence_type="market_daily_bar",
            source="test",
            symbols=("000001.SZ",),
            published_at=as_of - timedelta(minutes=10),
            available_at=as_of - timedelta(minutes=5),
            summary="Price is above MA20, MACD positive.",
            reliability=0.9,
            content_hash="hash-price",
        ),
        Evidence(
            evidence_id="ev_announcement",
            evidence_type="company_announcement",
            source="test",
            symbols=("000001.SZ",),
            published_at=as_of - timedelta(minutes=9),
            available_at=as_of - timedelta(minutes=4),
            summary="Announcement includes material uncertainty.",
            reliability=0.9,
            content_hash="hash-announcement",
        ),
    )


def valid_decision_payload() -> dict[str, Any]:
    return {
        "direction": "bullish",
        "confidence": 0.74,
        "action": "observe",
        "reasoning": [
            {
                "reason": "Technical trend remains stronger after discussion.",
                "skill_ids": ["technical_trend"],
                "discussion_refs": ["revision:technical_trend"],
                "evidence_ids": ["ev_price"],
            }
        ],
        "supporting_skills": ["technical_trend"],
        "opposing_skills": ["announcement_risk"],
        "discussion_refs": ["conflict:technical_vs_announcement"],
        "evidence_refs": ["ev_price", "ev_announcement"],
        "risks": [
            {
                "risk": "Announcement risk may dominate price trend.",
                "uncertainty": "Follow-up filings are unknown.",
                "invalid_condition": "Close below MA20 invalidates the bullish read.",
                "evidence_ids": ["ev_announcement"],
            }
        ],
        "rejected_directions": [
            {
                "direction": "bearish",
                "reason": "Announcement risk is not enough to outweigh trend.",
                "skill_ids": ["announcement_risk"],
                "discussion_refs": ["conflict:technical_vs_announcement"],
                "evidence_ids": ["ev_announcement"],
            },
            {
                "direction": "no_trade",
                "reason": "Evidence is sufficient and uncertainty is acceptable.",
                "skill_ids": ["technical_trend", "announcement_risk"],
                "discussion_refs": ["discussion_summary"],
                "evidence_ids": ["ev_price", "ev_announcement"],
            },
        ],
        "decision_summary": "Bullish is selected with moderated confidence.",
    }


def structured_result(payload: dict[str, Any]) -> LLMStructuredResult:
    parsed = DecisionResultPayload.model_validate(payload)
    return LLMStructuredResult(
        parsed=parsed,
        provider="deepseek",
        model="deepseek/deepseek-chat",
        request_id="req_1",
        raw_response=parsed.model_dump_json(),
        extracted_payload=parsed.model_dump(mode="json"),
        prompt_tokens=120,
        completion_tokens=90,
        total_tokens=210,
        latency_ms=15,
        raw_finish_reason="stop",
    )
