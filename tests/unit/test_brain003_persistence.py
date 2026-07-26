from datetime import UTC, datetime, timedelta

from tests.unit.test_brain003_models import valid_payload

from aios.kernel.brain003 import DiscussionExecution, DiscussionResult
from aios.kernel.enums import SkillExecutionStatus
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres.mapper import model_to_entity, to_model


def now() -> datetime:
    return datetime.now(UTC)


def discussion_execution() -> DiscussionExecution:
    started_at = now()
    return DiscussionExecution(
        task_id="at_example",
        skill_result_ids=("sr_technical", "sr_announcement"),
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=15),
        status=SkillExecutionStatus.SUCCEEDED,
        provider="deepseek",
        model="deepseek/deepseek-chat",
        prompt_version="discussion_v1",
        latency_ms=15,
        retry_count=1,
        raw_response='{"discussion_summary":"ok"}',
        parsed_response=valid_payload(),
    )


def discussion_result(execution_id: str) -> DiscussionResult:
    return DiscussionResult(
        discussion_execution_id=execution_id,
        task_id="at_example",
        skill_result_ids=("sr_technical", "sr_announcement"),
        **valid_payload(),
    )


def test_memory_storage_persists_brain003_entities() -> None:
    storage = InMemoryStorage()
    execution = discussion_execution()
    result = discussion_result(execution.discussion_execution_id)

    storage.save(execution)
    storage.save(result)

    assert (
        storage.get(DiscussionExecution, execution.discussion_execution_id) == execution
    )
    assert storage.get(DiscussionResult, result.discussion_result_id) == result


def test_postgres_mapper_round_trips_brain003_entities() -> None:
    execution = discussion_execution()
    result = discussion_result(execution.discussion_execution_id)

    for entity in (execution, result):
        assert model_to_entity(to_model(entity)) == entity
