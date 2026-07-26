from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from aios.kernel.brain004 import (
    DecisionExecution,
    DecisionResult,
    DecisionResultPayload,
    DirectionRejection,
    ReferencedReason,
    RiskNote,
)
from aios.kernel.enums import DecisionDirection, SkillExecutionStatus


def now() -> datetime:
    return datetime.now(UTC)


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "direction": "bullish",
        "confidence": 0.74,
        "action": "observe",
        "reasoning": [
            {
                "reason": "Technical evidence remains stronger after discussion.",
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
                "reason": "Announcement risk is not strong enough to outweigh trend.",
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
        "decision_summary": "Bullish is selected, with moderated confidence.",
    }
    payload.update(overrides)
    return payload


def test_decision_payload_validates_auditable_final_decision() -> None:
    payload = DecisionResultPayload.model_validate(valid_payload())

    assert payload.direction is DecisionDirection.BULLISH
    assert payload.confidence == 0.74
    assert isinstance(payload.reasoning[0], ReferencedReason)
    assert isinstance(payload.risks[0], RiskNote)
    assert isinstance(payload.rejected_directions[0], DirectionRejection)
    assert payload.supporting_skills == ("technical_trend",)
    assert payload.opposing_skills == ("announcement_risk",)


def test_decision_payload_requires_traceable_reasoning_and_rejections() -> None:
    with pytest.raises(ValidationError, match="reasoning must reference"):
        DecisionResultPayload.model_validate(
            valid_payload(
                reasoning=[
                    {
                        "reason": "Unsupported narrative.",
                        "skill_ids": [],
                        "discussion_refs": [],
                        "evidence_ids": [],
                    }
                ]
            )
        )

    with pytest.raises(ValidationError, match="rejected_directions"):
        DecisionResultPayload.model_validate(valid_payload(rejected_directions=[]))

    with pytest.raises(ValidationError, match="must not include selected direction"):
        DecisionResultPayload.model_validate(
            valid_payload(
                rejected_directions=[
                    {
                        "direction": "bullish",
                        "reason": "Bad rejection.",
                        "skill_ids": ["technical_trend"],
                        "discussion_refs": ["discussion_summary"],
                        "evidence_ids": ["ev_price"],
                    }
                ]
            )
        )


def test_decision_payload_normalizes_direction_rejection_map() -> None:
    payload = DecisionResultPayload.model_validate(
        valid_payload(
            direction="no_trade",
            rejected_directions={
                "bullish": "Bullish rejected because announcement risk offsets trend.",
                "bearish": (
                    "Bearish rejected because technical evidence is constructive."
                ),
            },
        )
    )

    assert payload.rejected_directions[0].direction is DecisionDirection.BULLISH
    assert payload.rejected_directions[0].discussion_refs == ("discussion_summary",)
    assert payload.rejected_directions[1].direction is DecisionDirection.BEARISH


def test_decision_records_validate_timestamps_and_audit_payloads() -> None:
    started_at = now()
    execution = DecisionExecution(
        task_id="at_example",
        discussion_result_id="dr_example",
        skill_result_ids=("sr_technical", "sr_announcement"),
        evidence_ids=("ev_price", "ev_announcement"),
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=30),
        status=SkillExecutionStatus.SUCCEEDED,
        provider="deepseek",
        model="deepseek/deepseek-chat",
        prompt_version="decision_v1",
        latency_ms=30,
        retry_count=1,
        raw_response='{"direction":"bullish"}',
        parsed_response=valid_payload(),
    )
    result = DecisionResult(
        decision_execution_id=execution.decision_execution_id,
        task_id="at_example",
        discussion_result_id="dr_example",
        skill_result_ids=("sr_technical", "sr_announcement"),
        **valid_payload(),
    )

    assert execution.decision_execution_id.startswith("de_")
    assert result.decision_result_id.startswith("ds_")

    with pytest.raises(ValidationError):
        DecisionExecution(
            task_id="at_example",
            discussion_result_id="dr_example",
            skill_result_ids=("sr_technical",),
            evidence_ids=("ev_price",),
            started_at=started_at,
            finished_at=started_at - timedelta(milliseconds=1),
            status=SkillExecutionStatus.SUCCEEDED,
        )
