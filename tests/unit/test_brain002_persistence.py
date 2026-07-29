from datetime import UTC, datetime, timedelta

from aios.kernel.brain002 import (
    AnalysisTask,
    SkillDefinition,
    SkillExecution,
    SkillResult,
    TokenUsage,
)
from aios.kernel.enums import SkillDirection, SkillExecutionStatus
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres.mapper import model_to_entity, to_model


def now() -> datetime:
    return datetime.now(UTC)


def skill_definition() -> SkillDefinition:
    return SkillDefinition(
        skill_id="technical_trend",
        name="Technical Trend",
        version="1.0.0",
        description="Trend-only analysis.",
        supported_markets=("cn",),
        supported_asset_types=("stock",),
        supported_horizons=("swing",),
        required_evidence_types=("price",),
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger_conditions={"metadata_equals": {"bar_type": "daily"}},
        dependencies=("base_market_context",),
        conflicts=("announcement_risk",),
    )


def analysis_task() -> AnalysisTask:
    return AnalysisTask(
        symbol="000001",
        market="cn",
        asset_type="stock",
        horizon="swing",
        as_of=now(),
        evidence_ids=("ev_price",),
        user_constraints={"max_tokens": 1000},
        requested_skill_ids=("technical_trend",),
    )


def skill_execution(task_id: str) -> SkillExecution:
    started_at = now()
    return SkillExecution(
        task_id=task_id,
        skill_id="technical_trend",
        skill_version="1.0.0",
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=20),
        status=SkillExecutionStatus.SUCCEEDED,
        provider="deepseek",
        model="deepseek/chat",
        prompt_version="technical_trend_v1",
        token_usage=TokenUsage(prompt_tokens=10, completion_tokens=7, total_tokens=17),
        latency_ms=20,
        retry_count=1,
    )


def skill_result(execution_id: str) -> SkillResult:
    return SkillResult(
        execution_id=execution_id,
        skill_id="technical_trend",
        skill_version="1.0.0",
        conclusion="Trend is constructive.",
        direction=SkillDirection.BULLISH,
        confidence=0.7,
        supporting_evidence_ids=("ev_price",),
        contradicting_evidence_ids=("ev_risk",),
        assumptions=("Liquidity holds.",),
        risk_factors=("Trend may reverse.",),
        invalid_conditions=("Support breaks.",),
        missing_information=("Intraday flow.",),
        reasoning_summary="Price evidence supports a bullish read.",
        raw_output={"parsed": {"direction": "bullish"}},
    )


def test_memory_storage_persists_brain002_entities() -> None:
    storage = InMemoryStorage()
    definition = skill_definition()
    task = analysis_task()
    execution = skill_execution(task.task_id)
    result = skill_result(execution.execution_id)

    for entity in (definition, task, execution, result):
        storage.save(entity)

    assert storage.get(SkillDefinition, definition.entity_id) == definition
    assert storage.get(AnalysisTask, task.task_id) == task
    assert storage.get(SkillExecution, execution.execution_id) == execution
    assert storage.get(SkillResult, result.result_id) == result


def test_postgres_mapper_round_trips_brain002_entities() -> None:
    definition = skill_definition()
    task = analysis_task()
    execution = skill_execution(task.task_id)
    result = skill_result(execution.execution_id)

    for entity in (definition, task, execution, result):
        assert model_to_entity(to_model(entity)) == entity
