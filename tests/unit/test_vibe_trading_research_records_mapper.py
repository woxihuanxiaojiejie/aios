from __future__ import annotations

from datetime import UTC, datetime

from aios.kernel.enums import AgentRole
from aios.vibe_trading.output_mapper import (
    VibeTradingRawResult,
    map_vibe_trading_result_to_agent_report_inputs,
)


def test_vibe_trading_result_maps_existing_analyst_reports_only() -> None:
    result = VibeTradingRawResult(
        symbol="600519",
        market="CN",
        as_of=datetime(2026, 7, 22, 6, 0, tzinfo=UTC),
        analyst_reports={
            "market": "technical report",
            "news": "news report",
            "fundamentals": " ",
        },
        model_provider="openai",
        model_name="gpt-test",
        started_at=datetime(2026, 7, 22, 6, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 22, 6, 1, tzinfo=UTC),
    )

    payloads = map_vibe_trading_result_to_agent_report_inputs(
        result,
        default_confidence=0.5,
    )

    assert [payload.role for payload in payloads] == [
        AgentRole.TECHNICAL,
        AgentRole.NEWS,
    ]
    assert payloads[0].summary == "technical report"
    assert payloads[0].stance == "unspecified"
    assert payloads[0].confidence == 0.5
    assert payloads[0].evidence_ids == ()
    assert payloads[0].source == "vibe_trading"
    assert payloads[0].raw_reference == "analyst_reports.market"


def test_vibe_trading_mapper_does_not_invent_missing_confidence() -> None:
    result = VibeTradingRawResult(
        symbol="600519",
        market="CN",
        as_of=datetime(2026, 7, 22, 6, 0, tzinfo=UTC),
        analyst_reports={"sentiment": "sentiment report"},
        model_provider="openai",
        model_name="gpt-test",
        started_at=datetime(2026, 7, 22, 6, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 22, 6, 1, tzinfo=UTC),
    )

    payloads = map_vibe_trading_result_to_agent_report_inputs(result)

    assert len(payloads) == 1
    assert payloads[0].role is AgentRole.SENTIMENT
    assert payloads[0].confidence is None
    assert payloads[0].evidence_ids == ()
