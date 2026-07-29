from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from aios.application.brain003 import DiscussionService
from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.kernel.brain002 import AnalysisTask, SkillResult
from aios.kernel.enums import SkillDirection, SkillExecutionStatus
from aios.kernel.evidence import Evidence
from aios.storage.memory import InMemoryStorage


@pytest.mark.external_llm
def test_real_litellm_brain003_discussion_smoke() -> None:
    if os.getenv("AIOS_RUN_BRAIN003_EXTERNAL_LLM_TESTS") != "1":
        pytest.skip("set AIOS_RUN_BRAIN003_EXTERNAL_LLM_TESTS=1 to run BRAIN-003 smoke")
    model = os.getenv("AIOS_EXTERNAL_LLM_MODEL")
    if not model:
        pytest.skip("set AIOS_EXTERNAL_LLM_MODEL to run external LLM smoke")

    as_of = datetime.now(UTC)
    evidence = _evidence(as_of)
    task = AnalysisTask(
        symbol="000001.SZ",
        market="cn",
        asset_type="stock",
        horizon="swing",
        as_of=as_of,
        evidence_ids=tuple(item.evidence_id for item in evidence),
    )
    skill_results = _skill_results()

    outcome = DiscussionService(
        llm=LiteLLMAdapter(),
        model=model,
        timeout_seconds=90,
        max_attempts=1,
    ).discuss(task=task, skill_results=skill_results, evidence=evidence)

    assert outcome.execution.status is SkillExecutionStatus.SUCCEEDED
    assert outcome.execution.provider == model.split("/", maxsplit=1)[0]
    assert outcome.execution.model
    assert outcome.execution.raw_response
    assert outcome.execution.parsed_response
    assert outcome.execution.token_usage.total_tokens is not None
    assert outcome.result is not None
    assert outcome.result.discussion_summary
    assert 0 <= outcome.result.discussion_confidence <= 1
    assert outcome.result.counter_arguments
    assert outcome.result.revision_suggestions

    storage = InMemoryStorage()
    storage.save(outcome.execution)
    storage.save(outcome.result)
    assert storage.get(type(outcome.result), outcome.result.discussion_result_id)


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


def _evidence(as_of: datetime) -> tuple[Evidence, ...]:
    published_at = as_of - timedelta(minutes=10)
    available_at = as_of - timedelta(minutes=5)
    return (
        Evidence(
            evidence_id="ev_price",
            evidence_type="market_daily_bar",
            source="brain003-smoke",
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
            source="brain003-smoke",
            symbols=("000001.SZ",),
            published_at=published_at,
            available_at=available_at,
            summary="A company announcement disclosed material uncertainty.",
            reliability=0.9,
            content_hash="hash-announcement",
        ),
    )
