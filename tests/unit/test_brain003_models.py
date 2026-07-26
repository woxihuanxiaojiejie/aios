from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from aios.kernel.brain003 import (
    ConflictReview,
    CounterArgument,
    DiscussionExecution,
    DiscussionResult,
    DiscussionResultPayload,
    EvidenceReview,
    RevisionSuggestion,
)
from aios.kernel.enums import SkillExecutionStatus


def now() -> datetime:
    return datetime.now(UTC)


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "conflicts": [
            {
                "skill_ids": ["technical_trend", "announcement_risk"],
                "conflict_type": "direction",
                "description": (
                    "Technical is bullish while announcement risk is bearish."
                ),
                "reason": "Trend evidence conflicts with announcement risk.",
                "evidence_ids": ["ev_price", "ev_announcement"],
            }
        ],
        "evidence_reviews": [
            {
                "skill_id": "technical_trend",
                "sufficiency": "partial",
                "challenge": "Trend cites MA20 and MACD but lacks volume confirmation.",
                "referenced_evidence_ids": ["ev_price"],
                "missing_evidence_categories": ["volume", "capital_flow"],
            }
        ],
        "counter_arguments": [
            {
                "skill_id": "technical_trend",
                "argument": "The bullish read may fail if announcement risk dominates.",
                "failure_mode": "Announcement risk invalidates trend continuation.",
                "evidence_ids": ["ev_announcement"],
            }
        ],
        "revision_suggestions": [
            {
                "skill_id": "technical_trend",
                "original_confidence": 0.82,
                "suggested_confidence": 0.7,
                "reason": "Announcement risk reduces confidence in trend evidence.",
            }
        ],
        "discussion_summary": "Skills disagree; confidence should be moderated.",
        "discussion_confidence": 0.68,
    }
    payload.update(overrides)
    return payload


def test_discussion_payload_validates_all_four_outputs() -> None:
    payload = DiscussionResultPayload.model_validate(valid_payload())

    assert isinstance(payload.conflicts[0], ConflictReview)
    assert isinstance(payload.evidence_reviews[0], EvidenceReview)
    assert isinstance(payload.counter_arguments[0], CounterArgument)
    assert isinstance(payload.revision_suggestions[0], RevisionSuggestion)
    assert payload.discussion_confidence == 0.68


def test_discussion_payload_rejects_decision_language_and_weight_mutation() -> None:
    with pytest.raises(ValidationError, match="decision language"):
        DiscussionResultPayload.model_validate(
            valid_payload(discussion_summary="Buy the stock with a 20% position.")
        )

    with pytest.raises(ValidationError, match="weight mutation"):
        DiscussionResultPayload.model_validate(
            valid_payload(
                revision_suggestions=[
                    {
                        "skill_id": "technical_trend",
                        "original_confidence": 0.82,
                        "suggested_confidence": 0.7,
                        "reason": "Update the long-term skill weight to reflect risk.",
                    }
                ]
            )
        )


def test_discussion_records_validate_timestamps_and_audit_payloads() -> None:
    started_at = now()
    execution = DiscussionExecution(
        task_id="at_example",
        skill_result_ids=("sr_technical", "sr_announcement"),
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=25),
        status=SkillExecutionStatus.SUCCEEDED,
        provider="deepseek",
        model="deepseek/deepseek-chat",
        prompt_version="discussion_v1",
        latency_ms=25,
        retry_count=1,
        raw_response='{"discussion_summary":"ok"}',
        parsed_response=valid_payload(),
        error=None,
    )
    result = DiscussionResult(
        discussion_execution_id=execution.discussion_execution_id,
        task_id="at_example",
        skill_result_ids=("sr_technical", "sr_announcement"),
        **valid_payload(),
    )

    assert execution.discussion_execution_id.startswith("dx_")
    assert result.discussion_result_id.startswith("dr_")

    with pytest.raises(ValidationError):
        DiscussionExecution(
            task_id="at_example",
            skill_result_ids=("sr_technical",),
            started_at=started_at,
            finished_at=started_at - timedelta(milliseconds=1),
            status=SkillExecutionStatus.SUCCEEDED,
        )
