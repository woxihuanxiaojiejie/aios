from __future__ import annotations

from aios.application.brain002 import SkillResponseParser
from aios.kernel.enums import SkillDirection


def valid_payload_json(**overrides: object) -> str:
    payload: dict[str, object] = {
        "conclusion": "Trend is constructive.",
        "direction": "bullish",
        "confidence": 0.7,
        "supporting_evidence_ids": ["ev_price"],
        "contradicting_evidence_ids": [],
        "assumptions": ["Liquidity remains normal."],
        "risk_factors": ["Trend may reverse."],
        "invalid_conditions": ["Support breaks."],
        "missing_information": ["Intraday flow."],
        "reasoning_summary": "Price evidence supports the conclusion.",
    }
    payload.update(overrides)
    import json

    return json.dumps(payload)


def test_skill_response_parser_accepts_pure_json() -> None:
    parsed = SkillResponseParser().parse(valid_payload_json())

    assert parsed.payload is not None
    assert parsed.payload.direction is SkillDirection.BULLISH
    assert parsed.extracted_payload["supporting_evidence_ids"] == ["ev_price"]
    assert parsed.validation_error is None


def test_skill_response_parser_accepts_markdown_json_code_fence() -> None:
    parsed = SkillResponseParser().parse(
        f"```json\n{valid_payload_json(confidence='0.65')}\n```"
    )

    assert parsed.payload is not None
    assert parsed.payload.confidence == 0.65


def test_skill_response_parser_accepts_json_with_surrounding_text() -> None:
    parsed = SkillResponseParser().parse(
        f"Here is the JSON:\n{valid_payload_json()}\nDone."
    )

    assert parsed.payload is not None
    assert parsed.payload.conclusion == "Trend is constructive."


def test_skill_response_parser_rejects_illegal_direction() -> None:
    parsed = SkillResponseParser().parse(valid_payload_json(direction="up"))

    assert parsed.payload is None
    assert parsed.validation_error is not None
    assert "direction" in str(parsed.validation_error)


def test_skill_response_parser_rejects_bad_confidence_type() -> None:
    parsed = SkillResponseParser().parse(valid_payload_json(confidence="high"))

    assert parsed.payload is None
    assert parsed.validation_error is not None
    assert "confidence" in str(parsed.validation_error)


def test_skill_response_parser_rejects_missing_required_field() -> None:
    import json

    payload = json.loads(valid_payload_json())
    del payload["reasoning_summary"]

    parsed = SkillResponseParser().parse(json.dumps(payload))

    assert parsed.payload is None
    assert parsed.validation_error is not None
    assert "reasoning_summary" in str(parsed.validation_error)
