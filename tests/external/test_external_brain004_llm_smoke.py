from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from aios.application.brain004 import DecisionService
from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.kernel.brain002 import AnalysisTask, SkillResult
from aios.kernel.brain003 import DiscussionResult
from aios.kernel.brain004 import DecisionResult
from aios.kernel.enums import SkillDirection, SkillExecutionStatus
from aios.kernel.evidence import Evidence
from aios.storage.memory import InMemoryStorage


@pytest.mark.external_llm
def test_real_litellm_brain004_decision_smoke() -> None:
    if os.getenv("AIOS_RUN_BRAIN004_EXTERNAL_LLM_TESTS") != "1":
        pytest.skip("set AIOS_RUN_BRAIN004_EXTERNAL_LLM_TESTS=1 to run BRAIN-004 smoke")
    model = os.getenv("AIOS_EXTERNAL_LLM_MODEL")
    if not model:
        pytest.skip("set AIOS_EXTERNAL_LLM_MODEL to run external LLM smoke")

    as_of = datetime.now(UTC)
    evidence = _evidence(as_of)
    task = AnalysisTask(
        task_id="at_smoke",
        symbol="000001.SZ",
        market="cn",
        asset_type="stock",
        horizon="swing",
        as_of=as_of,
        evidence_ids=tuple(item.evidence_id for item in evidence),
    )
    skill_results = _skill_results()
    discussion = _discussion_result(skill_results)

    outcome = DecisionService(
        llm=LiteLLMAdapter(),
        model=model,
        timeout_seconds=90,
        max_attempts=1,
    ).decide(
        task=task,
        skill_results=skill_results,
        discussion_result=discussion,
        evidence=evidence,
    )

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.provider == model.split("/", maxsplit=1)[0]
    assert outcome.execution.model
    assert outcome.execution.raw_response
    assert outcome.execution.parsed_response
    assert outcome.execution.token_usage.total_tokens is not None
    assert outcome.result is not None
    assert outcome.result.direction.value in {
        "bullish",
        "bearish",
        "neutral",
        "no_trade",
    }
    assert 0 <= outcome.result.confidence <= 1
    assert outcome.result.reasoning
    assert outcome.result.evidence_refs
    assert outcome.result.rejected_directions

    storage = InMemoryStorage()
    storage.save(outcome.execution)
    storage.save(outcome.result)
    assert storage.get(DecisionResult, outcome.result.decision_result_id)


def _skill_results() -> tuple[SkillResult, ...]:
    return (
        SkillResult(
            result_id="sr_technical",
            execution_id="sx_technical",
            skill_id="technical_trend",
            skill_version="1.0.0",
            conclusion="Trend is constructive.",
            direction=SkillDirection.BULLISH,
            confidence=0.82,
            supporting_evidence_ids=("ev_price",),
            risk_factors=("Volume confirmation may fade.",),
            invalid_conditions=("Close breaks below MA20.",),
            missing_information=("Capital flow details.",),
            reasoning_summary="MA20 and MACD support a constructive trend read.",
            raw_output={"parsed": {"direction": "bullish"}},
        ),
        SkillResult(
            result_id="sr_announcement",
            execution_id="sx_announcement",
            skill_id="announcement_risk",
            skill_version="1.0.0",
            conclusion="Announcement risk is negative.",
            direction=SkillDirection.BEARISH,
            confidence=0.76,
            supporting_evidence_ids=("ev_announcement",),
            risk_factors=("Risk may already be reflected.",),
            invalid_conditions=("Company issues a clarifying filing.",),
            missing_information=("Regulator follow-up.",),
            reasoning_summary=(
                "The announcement creates risk that conflicts with trend."
            ),
            raw_output={"parsed": {"direction": "bearish"}},
        ),
    )


def _discussion_result(skill_results: tuple[SkillResult, ...]) -> DiscussionResult:
    return DiscussionResult(
        discussion_execution_id="dx_smoke",
        task_id="at_smoke",
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
                "reason": "Announcement risk makes the bullish confidence less robust.",
            }
        ],
        discussion_summary=(
            "The skill results conflict and confidence should be moderated."
        ),
        discussion_confidence=0.68,
    )


def _evidence(as_of: datetime) -> tuple[Evidence, ...]:
    published_at = as_of - timedelta(minutes=10)
    available_at = as_of - timedelta(minutes=5)
    return (
        Evidence(
            evidence_id="ev_price",
            evidence_type="market_daily_bar",
            source="brain004-smoke",
            symbols=("000001.SZ",),
            published_at=published_at,
            available_at=available_at,
            summary="Price is above MA20 and MACD is positive, but volume is mixed.",
            reliability=0.9,
            content_hash="hash-price",
        ),
        Evidence(
            evidence_id="ev_announcement",
            evidence_type="company_announcement",
            source="brain004-smoke",
            symbols=("000001.SZ",),
            published_at=published_at,
            available_at=available_at,
            summary="A company announcement disclosed material uncertainty.",
            reliability=0.9,
            content_hash="hash-announcement",
        ),
    )
