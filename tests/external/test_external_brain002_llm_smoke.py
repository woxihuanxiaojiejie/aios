from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from aios.application.brain002 import ExecutableSkill, SkillExecutor
from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.kernel.brain002 import AnalysisTask
from aios.kernel.evidence import Evidence
from aios.skills.brain002 import (
    AnnouncementRiskSkill,
    MarketSentimentSkill,
    PolicyImpactSkill,
    SectorStrengthSkill,
    TechnicalTrendSkill,
)


@pytest.mark.external_llm
def test_real_litellm_brain002_mvp_skills_smoke() -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_LLM_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_LLM_TESTS=1 to run external LLM smoke")
    model = os.getenv("AIOS_EXTERNAL_LLM_MODEL")
    if not model:
        pytest.skip("set AIOS_EXTERNAL_LLM_MODEL to run external LLM smoke")

    as_of = datetime.now(UTC)
    evidence = _brain002_evidence(as_of)
    task = AnalysisTask(
        symbol="000001.SZ",
        market="cn",
        asset_type="stock",
        horizon="swing",
        as_of=as_of,
        evidence_ids=tuple(item.evidence_id for item in evidence),
    )
    skills = cast(
        "tuple[ExecutableSkill, ...]",
        (
            TechnicalTrendSkill(),
            SectorStrengthSkill(),
            PolicyImpactSkill(),
            AnnouncementRiskSkill(),
            MarketSentimentSkill(),
        ),
    )

    outcome = SkillExecutor(
        llm=LiteLLMAdapter(),
        model=model,
        timeout_seconds=90,
        max_attempts=1,
    ).execute(task=task, skills=skills, evidence=evidence)

    valid_evidence_ids = {item.evidence_id for item in evidence}
    assert len(outcome.executions) == 5
    assert len(outcome.results) == 5
    assert {result.skill_id for result in outcome.results} == {
        "technical_trend",
        "sector_strength",
        "policy_impact",
        "announcement_risk",
        "market_sentiment",
    }
    for execution in outcome.executions:
        assert execution.provider == model.split("/", maxsplit=1)[0]
        assert execution.model
        assert execution.latency_ms is not None
        assert execution.error is None
    for result in outcome.results:
        assert set(result.supporting_evidence_ids).issubset(valid_evidence_ids)
        assert result.risk_factors
        assert result.invalid_conditions
        assert result.missing_information


def _brain002_evidence(as_of: datetime) -> tuple[Evidence, ...]:
    published_at = as_of - timedelta(minutes=10)
    available_at = as_of - timedelta(minutes=5)
    return (
        _evidence(
            "ev_technical_trend",
            "market_daily_bar",
            "Price closed above the 20 day moving average on rising volume.",
            published_at,
            available_at,
        ),
        _evidence(
            "ev_sector_strength",
            "sector_snapshot",
            "Brokerage sector outperformed the broad market with improving breadth.",
            published_at,
            available_at,
        ),
        _evidence(
            "ev_policy_impact",
            "policy",
            "National regulators announced capital market support measures.",
            published_at,
            available_at,
            metadata={"source_domain": "policy", "policy_level": "national"},
        ),
        _evidence(
            "ev_announcement_risk",
            "company_announcement",
            "The company disclosed no major litigation or shareholder reduction.",
            published_at,
            available_at,
        ),
        _evidence(
            "ev_market_sentiment",
            "market_sentiment_snapshot",
            "Market risk appetite improved and advancing issues broadened.",
            published_at,
            available_at,
        ),
    )


def _evidence(
    evidence_id: str,
    evidence_type: str,
    summary: str,
    published_at: datetime,
    available_at: datetime,
    *,
    metadata: dict[str, object] | None = None,
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source="brain002-smoke",
        symbols=("000001.SZ",),
        published_at=published_at,
        available_at=available_at,
        summary=summary,
        reliability=0.9,
        content_hash=f"hash-{evidence_id}",
        metadata=metadata or {},
    )
