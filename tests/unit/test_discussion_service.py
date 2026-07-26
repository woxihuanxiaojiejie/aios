from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from aios.adapters.llm import LLMStructuredResult
from aios.application.brain003 import DiscussionService
from aios.integrations.litellm.errors import LLMStructuredOutputError
from aios.kernel.brain002 import AnalysisTask, SkillResult
from aios.kernel.brain003 import DiscussionResultPayload
from aios.kernel.enums import SkillDirection, SkillExecutionStatus
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


def test_discussion_service_generates_auditable_discussion_result() -> None:
    payload = valid_discussion_payload()
    llm = FakeLLM([structured_result(payload)])
    task = analysis_task()
    skill_results = brain002_results()
    evidence = evidence_items()

    outcome = DiscussionService(
        llm=llm,
        model="deepseek/deepseek-chat",
        timeout_seconds=5,
        max_attempts=1,
    ).discuss(task=task, skill_results=skill_results, evidence=evidence)

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.provider == "deepseek"
    assert outcome.execution.raw_response is not None
    assert outcome.execution.parsed_response["discussion_summary"]
    assert outcome.result is not None
    assert outcome.result.conflicts[0].skill_ids == (
        "technical_trend",
        "announcement_risk",
    )
    assert llm.calls[0]["response_schema"] is DiscussionResultPayload
    assert "Do not call skills" in llm.calls[0]["system_prompt"]
    assert "Buy" not in outcome.result.discussion_summary


def test_discussion_service_repairs_structured_output_without_rediscussing() -> None:
    malformed = LLMStructuredOutputError(
        "bad json",
        raw_response='{"summary":"bad"}',
        extracted_payload={"summary": "bad"},
        validation_error="missing discussion_summary",
        provider="deepseek",
        model="deepseek/deepseek-chat",
        latency_ms=3,
    )
    llm = FakeLLM([malformed, structured_result(valid_discussion_payload())])

    outcome = DiscussionService(
        llm=llm,
        model="deepseek/deepseek-chat",
        timeout_seconds=5,
        max_attempts=1,
    ).discuss(
        task=analysis_task(),
        skill_results=brain002_results(),
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.retry_count == 1
    assert outcome.result is not None
    assert "Do not redo the discussion" in llm.calls[1]["system_prompt"]
    assert "original_raw_response" in llm.calls[1]["user_prompt"]


def test_discussion_service_rejects_missing_skill_result_evidence_reference() -> None:
    broken_result = brain002_results()[0].model_copy(
        update={"supporting_evidence_ids": ("ev_missing",)}
    )

    outcome = DiscussionService(
        llm=FakeLLM([structured_result(valid_discussion_payload())]),
        model="deepseek/deepseek-chat",
    ).discuss(
        task=analysis_task(),
        skill_results=(broken_result,),
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.FAILED
    assert outcome.result is None
    assert "unknown evidence IDs" in (outcome.execution.error or "")


def test_discussion_service_rejects_discussion_evidence_outside_inputs() -> None:
    payload = valid_discussion_payload()
    payload["conflicts"][0]["evidence_ids"] = ["ev_unseen"]

    outcome = DiscussionService(
        llm=FakeLLM([structured_result(payload)]),
        model="deepseek/deepseek-chat",
    ).discuss(
        task=analysis_task(),
        skill_results=brain002_results(),
        evidence=evidence_items(),
    )

    assert outcome.execution.status is SkillExecutionStatus.FAILED
    assert outcome.result is None
    assert "unknown discussion evidence IDs" in (outcome.execution.error or "")


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


def valid_discussion_payload() -> dict[str, Any]:
    return {
        "conflicts": [
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
        "evidence_reviews": [
            {
                "skill_id": "technical_trend",
                "sufficiency": "partial",
                "challenge": "Technical result lacks volume and capital flow checks.",
                "referenced_evidence_ids": ["ev_price"],
                "missing_evidence_categories": ["volume", "capital_flow"],
            }
        ],
        "counter_arguments": [
            {
                "skill_id": "technical_trend",
                "argument": (
                    "The bullish trend may be wrong if announcement risk dominates."
                ),
                "failure_mode": "Risk disclosure overwhelms trend continuation.",
                "evidence_ids": ["ev_announcement"],
            }
        ],
        "revision_suggestions": [
            {
                "skill_id": "technical_trend",
                "original_confidence": 0.82,
                "suggested_confidence": 0.7,
                "reason": "Announcement risk makes the bullish confidence less robust.",
            }
        ],
        "discussion_summary": (
            "The skill results conflict and confidence should be moderated."
        ),
        "discussion_confidence": 0.68,
    }


def structured_result(payload: dict[str, Any]) -> LLMStructuredResult:
    parsed = DiscussionResultPayload.model_validate(payload)
    return LLMStructuredResult(
        parsed=parsed,
        provider="deepseek",
        model="deepseek/deepseek-chat",
        request_id="req_1",
        raw_response=parsed.model_dump_json(),
        extracted_payload=parsed.model_dump(mode="json"),
        prompt_tokens=100,
        completion_tokens=80,
        total_tokens=180,
        latency_ms=12,
        raw_finish_reason="stop",
    )
