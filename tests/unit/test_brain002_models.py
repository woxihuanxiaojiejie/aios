from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from aios.kernel.brain002 import (
    AnalysisTask,
    SkillDefinition,
    SkillExecution,
    SkillResult,
    TokenUsage,
)
from aios.kernel.enums import SkillDirection, SkillExecutionStatus, SkillStatus


def now() -> datetime:
    return datetime.now(UTC)


def test_brain002_entity_ids_use_stable_prefixes() -> None:
    skill = SkillDefinition(
        skill_id="technical_trend",
        name="Technical Trend",
        version="1.0.0",
        description="Analyzes price trend evidence only.",
        supported_markets=("cn",),
        supported_asset_types=("stock",),
        supported_horizons=("swing",),
        required_evidence_types=("market_daily_bar",),
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    task = AnalysisTask(
        symbol="000001",
        market="cn",
        asset_type="stock",
        horizon="swing",
        as_of=now(),
        evidence_ids=("ev_price",),
    )
    execution = SkillExecution(
        task_id=task.task_id,
        skill_id=skill.skill_id,
        skill_version=skill.version,
        started_at=now(),
        status=SkillExecutionStatus.RUNNING,
    )
    result = SkillResult(
        execution_id=execution.execution_id,
        skill_id=skill.skill_id,
        skill_version=skill.version,
        conclusion="Trend remains constructive.",
        direction=SkillDirection.BULLISH,
        confidence=0.67,
        supporting_evidence_ids=("ev_price",),
        risk_factors=("Volume confirmation may fade.",),
        invalid_conditions=("Break below support.",),
        missing_information=("Intraday liquidity profile.",),
        reasoning_summary="Price action and volume support a bullish read.",
        raw_output={"direction": "bullish"},
    )

    assert task.task_id.startswith("at_")
    assert execution.execution_id.startswith("sx_")
    assert result.result_id.startswith("sr_")


def test_skill_definition_validates_metadata_and_status_timestamps() -> None:
    created_at = now()

    with pytest.raises(ValidationError):
        SkillDefinition(
            skill_id=" ",
            name="Technical Trend",
            version="1.0.0",
            description="Analyzes price trend evidence only.",
            supported_markets=("cn", "cn"),
            supported_asset_types=("stock",),
            supported_horizons=("swing",),
            required_evidence_types=("market_daily_bar",),
            input_schema={},
            output_schema={},
            status=SkillStatus.DISABLED,
            created_at=created_at,
            updated_at=created_at - timedelta(seconds=1),
        )


def test_analysis_task_requires_aware_as_of_and_unique_evidence_ids() -> None:
    with pytest.raises(ValidationError):
        AnalysisTask(
            symbol="000001",
            market="cn",
            asset_type="stock",
            horizon="swing",
            as_of=datetime.now(),
            evidence_ids=("ev_price", "ev_price"),
        )


def test_skill_execution_validates_finish_time_and_token_usage() -> None:
    started_at = now()

    execution = SkillExecution(
        task_id="at_example",
        skill_id="technical_trend",
        skill_version="1.0.0",
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=12),
        status=SkillExecutionStatus.SUCCEEDED,
        provider="deepseek",
        model="deepseek/chat",
        prompt_version="technical_trend_v1",
        token_usage=TokenUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        latency_ms=12,
    )

    assert execution.token_usage.total_tokens == 15

    with pytest.raises(ValidationError):
        SkillExecution(
            task_id="at_example",
            skill_id="technical_trend",
            skill_version="1.0.0",
            started_at=started_at,
            finished_at=started_at - timedelta(milliseconds=1),
            status=SkillExecutionStatus.SUCCEEDED,
            latency_ms=-1,
        )


def test_skill_result_enforces_structured_output_contract() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            execution_id="sx_example",
            skill_id="technical_trend",
            skill_version="1.0.0",
            conclusion="Bullish without evidence is invalid.",
            direction=SkillDirection.BULLISH,
            confidence=0.7,
            supporting_evidence_ids=(),
            risk_factors=("Trend may reverse.",),
            invalid_conditions=("Support breaks.",),
            missing_information=("Volume detail.",),
            reasoning_summary="No evidence reference.",
            raw_output={},
        )

    uncertain = SkillResult(
        execution_id="sx_example",
        skill_id="technical_trend",
        skill_version="1.0.0",
        conclusion="Insufficient evidence.",
        direction=SkillDirection.UNCERTAIN,
        confidence=0.2,
        supporting_evidence_ids=(),
        risk_factors=("Evidence is sparse.",),
        invalid_conditions=("Fresh complete evidence arrives.",),
        missing_information=("Recent price bars.",),
        reasoning_summary="The skill cannot form a directional conclusion.",
        raw_output={},
    )

    assert uncertain.direction is SkillDirection.UNCERTAIN
