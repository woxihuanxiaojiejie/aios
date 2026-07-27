from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from aios.adapters.llm import LLMStructuredResult
from aios.adapters.market_data import Adjustment, MarketBar
from aios.application.brain002 import SkillRegistry
from aios.application.brain_research_pipeline import BrainResearchPipeline
from aios.application.watchlist import WatchlistService
from aios.integrations.evidence import Evidence as BrainEvidence
from aios.integrations.provider_records import RSSIntakeRecord
from aios.kernel.brain002 import SkillDefinition
from aios.kernel.settlement import DecisionOutcome
from aios.kernel.trade_plan import TradePlan
from aios.skills.brain002 import TechnicalTrendSkill
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService

AS_OF = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)


class FakeBrainEvidenceRepository:
    def __init__(self, evidence: BrainEvidence) -> None:
        self.evidence = evidence

    def query(self, **kwargs: Any) -> tuple[list[BrainEvidence], int]:
        return [self.evidence], 1


class FakeMarketDataAdapter:
    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        return [
            MarketBar(
                symbol=symbol,
                market="CN_A",
                trade_date=end_date,
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("95"),
                close=Decimal("108"),
                volume=Decimal("10000"),
                amount=Decimal("1080000"),
                adjustment=adjustment,
                source="fixture",
                fetched_at=AS_OF + timedelta(days=1),
            )
        ]


class FakeLLMAdapter:
    def __init__(self) -> None:
        self._evidence_ids: list[str] = []

    def generate_structured(
        self,
        *,
        response_schema,
        **kwargs: Any,
    ) -> LLMStructuredResult:
        evidence_ids = _evidence_ids_from_prompt(str(kwargs["user_prompt"]))
        if evidence_ids:
            self._evidence_ids = evidence_ids
        parsed = _payload_for_schema(
            response_schema,
            self._evidence_ids,
        )
        return LLMStructuredResult(
            provider="fake",
            model=str(kwargs["model"]),
            parsed=response_schema.model_validate(parsed),
            raw_response="{}",
            extracted_payload=parsed,
            latency_ms=1,
        )


def _payload_for_schema(response_schema, evidence_ids: list[str]) -> dict[str, Any]:
    name = response_schema.__name__
    evidence_id = evidence_ids[0]
    if name == "SkillResultPayload":
        return {
            "conclusion": "Trend remains constructive.",
            "direction": "bullish",
            "confidence": 0.7,
            "supporting_evidence_ids": [evidence_id],
            "contradicting_evidence_ids": [],
            "assumptions": [],
            "risk_factors": ["fixture risk"],
            "invalid_conditions": ["close below support"],
            "missing_information": ["fixture missing context"],
            "reasoning_summary": "Fixture reasoning",
        }
    if name == "DiscussionResultPayload":
        return {
            "conflicts": [],
            "evidence_reviews": [],
            "counter_arguments": [],
            "revision_suggestions": [],
            "discussion_summary": "Skills agree.",
            "discussion_confidence": 0.7,
        }
    if name == "DecisionResultPayload":
        return {
            "direction": "bullish",
            "confidence": 0.7,
            "action": "observe",
            "reasoning": [
                {
                    "reason": "Traceable fixture reason.",
                    "skill_ids": ["technical_trend"],
                    "discussion_refs": ["discussion_summary"],
                    "evidence_ids": [evidence_id],
                }
            ],
            "supporting_skills": ["technical_trend"],
            "opposing_skills": [],
            "discussion_refs": ["discussion_summary"],
            "evidence_refs": [evidence_id],
            "risks": [
                {
                    "risk": "fixture decision risk",
                    "uncertainty": "fixture uncertainty",
                    "invalid_condition": "close below support",
                    "evidence_ids": [evidence_id],
                }
            ],
            "rejected_directions": [
                {
                    "direction": "bearish",
                    "reason": "No bearish evidence.",
                    "skill_ids": ["technical_trend"],
                    "discussion_refs": ["discussion_summary"],
                    "evidence_ids": [evidence_id],
                }
            ],
            "decision_summary": "Observe with bullish bias.",
        }
    raise AssertionError(f"unexpected schema {name}")


def _evidence_ids_from_prompt(user_prompt: str) -> list[str]:
    payload = json.loads(user_prompt)
    return [item["evidence_id"] for item in payload.get("evidence", ())]


def test_brain_pipeline_uses_bridged_core_evidence() -> None:
    from aios.application.evidence_bridge import CoreEvidenceBridge

    storage = InMemoryStorage()
    watchlist = WatchlistService(storage).add_item(symbol="600519", market="CN")
    from aios.application.research_session import ResearchSessionService

    research_session = ResearchSessionService(storage).create_session(
        watchlist_item_id=watchlist.watchlist_item_id,
        horizon_days=3,
        as_of=AS_OF + timedelta(days=1),
    )
    legacy = BrainEvidence.from_provider_record(
        RSSIntakeRecord(
            source="source-a",
            source_type="rss",
            source_url="https://example.test/feed.xml",
            source_identifier="article-1",
            published_at=AS_OF,
            collected_at=AS_OF,
            raw_artifact_path=Path("results/raw.xml"),
            title="Legacy title",
            summary="Legacy summary",
            content="Legacy full content",
            fingerprint="b" * 64,
        ),
        metadata={"symbols": ["600519"]},
    )
    registry = SkillRegistry()
    registry.register(_technical_definition())

    result = BrainResearchPipeline(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FakeMarketDataAdapter(),
        llm_adapter=FakeLLMAdapter(),
        brain002_registry=registry,
        brain_evidence_repository=FakeBrainEvidenceRepository(legacy),
    ).run(session=research_session, model="fake-model", provider="fake")

    bridged = CoreEvidenceBridge(storage).find_by_legacy_brain_evidence_id(
        str(legacy.evidence_id)
    )
    assert bridged is not None
    assert bridged.evidence_id in result.evidence_ids
    assert bridged.legacy_brain_evidence_id == str(legacy.evidence_id)
    assert bridged.title == "Legacy title"
    assert all(evidence_id.startswith("ev_") for evidence_id in result.evidence_ids)

    trade_plan = storage.get(TradePlan, result.trade_plan_id)
    assert trade_plan.decision_id == result.decision_id
    assert trade_plan.status.value == "no_trade"
    assert storage.list(DecisionOutcome) == []

    persisted_session = storage.get(type(research_session), research_session.entity_id)
    assert persisted_session.status.value == "trade_plan_ready"
    states = [event.to_state.value for event in persisted_session.transition_log]
    assert states == [
        "collecting_evidence",
        "evidence_ready",
        "hypothesis_ready",
        "skills_running",
        "discussion_ready",
        "risk_review",
        "decision_ready",
        "trade_plan_ready",
    ]
    assert "waiting_execution" not in states


def _technical_definition() -> SkillDefinition:
    definition = TechnicalTrendSkill().definition
    return definition.model_copy(
        update={
            "required_evidence_types": (),
            "trigger_conditions": {},
        }
    )
