from __future__ import annotations

import pytest
from pydantic import ValidationError

from aios.integrations.litellm.schemas import DecisionDraft
from aios.kernel.enums import Action


def valid_payload() -> dict[str, object]:
    return {
        "action": "hold",
        "confidence": 0.62,
        "expected_return": 0.008,
        "max_expected_loss": 0.015,
        "horizon": "1d",
        "reasoning_summary": "Evidence supports waiting for confirmation.",
        "supporting_evidence_ids": ["ev_1"],
        "risk_factors": ["thin evidence set"],
        "invalidation_conditions": ["new adverse filing"],
    }


def test_decision_draft_accepts_valid_payload() -> None:
    draft = DecisionDraft.model_validate(valid_payload())

    assert draft.action is Action.HOLD
    assert draft.supporting_evidence_ids == ("ev_1",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("action", "avoid"),
        ("confidence", 1.1),
        ("max_expected_loss", -0.01),
        ("supporting_evidence_ids", []),
        ("reasoning_summary", ""),
    ],
)
def test_decision_draft_rejects_invalid_fields(field: str, value: object) -> None:
    payload = valid_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        DecisionDraft.model_validate(payload)


def test_decision_draft_rejects_duplicate_evidence_ids() -> None:
    payload = valid_payload()
    payload["supporting_evidence_ids"] = ["ev_1", "ev_1"]

    with pytest.raises(ValidationError):
        DecisionDraft.model_validate(payload)


def test_decision_draft_limits_reasoning_summary_length() -> None:
    payload = valid_payload()
    payload["reasoning_summary"] = "x" * 1201

    with pytest.raises(ValidationError):
        DecisionDraft.model_validate(payload)
