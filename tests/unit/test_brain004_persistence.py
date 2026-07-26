from datetime import UTC, datetime, timedelta

from tests.unit.test_brain004_models import valid_payload

from aios.kernel.brain004 import DecisionExecution, DecisionResult
from aios.kernel.enums import SkillExecutionStatus
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres.mapper import model_to_entity, to_model


def now() -> datetime:
    return datetime.now(UTC)


def decision_execution() -> DecisionExecution:
    started_at = now()
    return DecisionExecution(
        task_id="at_example",
        discussion_result_id="dr_example",
        skill_result_ids=("sr_technical", "sr_announcement"),
        evidence_ids=("ev_price", "ev_announcement"),
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=15),
        status=SkillExecutionStatus.SUCCEEDED,
        provider="deepseek",
        model="deepseek/deepseek-v4-flash",
        prompt_version="decision_v1",
        latency_ms=15,
        retry_count=1,
        raw_response='{"direction":"bullish"}',
        parsed_response=valid_payload(),
    )


def decision_result(execution_id: str) -> DecisionResult:
    return DecisionResult(
        decision_execution_id=execution_id,
        task_id="at_example",
        discussion_result_id="dr_example",
        skill_result_ids=("sr_technical", "sr_announcement"),
        **valid_payload(),
    )


def test_memory_storage_persists_brain004_entities() -> None:
    storage = InMemoryStorage()
    execution = decision_execution()
    result = decision_result(execution.decision_execution_id)

    storage.save(execution)
    storage.save(result)

    assert storage.get(DecisionExecution, execution.decision_execution_id) == execution
    assert storage.get(DecisionResult, result.decision_result_id) == result


def test_postgres_mapper_round_trips_brain004_entities() -> None:
    execution = decision_execution()
    result = decision_result(execution.decision_execution_id)

    for entity in (execution, result):
        assert model_to_entity(to_model(entity)) == entity
