from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from aios.adapters.llm import LLMStructuredResult
from aios.adapters.market_data import Adjustment, MarketBar
from aios.api.routes.brain002 import default_brain002_registry
from aios.application.research_runner import ResearchRunner
from aios.application.research_settlement import ResearchSettlementService
from aios.application.watchlist import WatchlistService
from aios.integrations.evidence import Evidence as BrainEvidence
from aios.integrations.provider_records import (
    AnnouncementIntakeRecord,
    RSSIntakeRecord,
    WebpageIntakeRecord,
)
from aios.kernel.brain002 import SkillExecution, SkillResult, SkillResultPayload
from aios.kernel.brain003 import DiscussionResult, DiscussionResultPayload
from aios.kernel.brain004 import DecisionResult, DecisionResultPayload
from aios.kernel.debate import DebateRecord, DecisionAssemblyRecord, DecisionProposal
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    ApprovalStatus,
    DecisionDirection,
    LearningType,
    SkillDirection,
)
from aios.kernel.learning import Learning
from aios.kernel.research_records import Hypothesis
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService

AS_OF = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)


class FakeBrainEvidenceRepository:
    def __init__(self, evidence: tuple[BrainEvidence, ...]) -> None:
        self.evidence = evidence

    def query(self, **kwargs: Any) -> tuple[list[BrainEvidence], int]:
        available_before = kwargs.get("available_before")
        items = [
            item
            for item in self.evidence
            if available_before is None or item.available_at <= available_before
        ]
        return items, len(items)


class CountingBrainLLM:
    def __init__(self) -> None:
        self.schemas: list[type[BaseModel]] = []

    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        self.schemas.append(response_schema)
        parsed = self._payload(response_schema, user_prompt)
        return LLMStructuredResult(
            parsed=parsed,
            provider="fake",
            model=model,
            request_id=f"req-{len(self.schemas)}",
            prompt_tokens=20,
            completion_tokens=10,
            total_tokens=30,
            extracted_payload=parsed.model_dump(mode="json"),
            raw_response=parsed.model_dump_json(),
            latency_ms=5,
            raw_finish_reason="stop",
        )

    def _payload(self, response_schema: type[BaseModel], user_prompt: str) -> BaseModel:
        payload = json.loads(user_prompt)
        evidence_id = payload["evidence"][0]["evidence_id"]
        if response_schema is SkillResultPayload:
            return SkillResultPayload(
                conclusion="Evidence supports a cautiously bullish view.",
                direction=SkillDirection.BULLISH,
                confidence=0.64,
                supporting_evidence_ids=(evidence_id,),
                risk_factors=("external evidence may be revised",),
                invalid_conditions=("official denial or adverse follow-up",),
                missing_information=("intraday liquidity confirmation",),
                reasoning_summary="The supplied evidence supports the skill thesis.",
            )
        if response_schema is DiscussionResultPayload:
            skill_id = payload["skill_results"][0]["skill_id"]
            return DiscussionResultPayload(
                conflicts=(),
                evidence_reviews=(
                    {
                        "skill_id": skill_id,
                        "sufficiency": "sufficient for a bounded test",
                        "challenge": "evidence breadth remains limited",
                        "referenced_evidence_ids": [evidence_id],
                        "missing_evidence_categories": ["more follow-up coverage"],
                    },
                ),
                counter_arguments=(
                    {
                        "skill_id": skill_id,
                        "argument": (
                            "the signal can fail if the event is already priced"
                        ),
                        "failure_mode": "priced in",
                        "evidence_ids": [evidence_id],
                    },
                ),
                revision_suggestions=(
                    {
                        "skill_id": skill_id,
                        "original_confidence": 0.64,
                        "suggested_confidence": 0.60,
                        "reason": "limited breadth warrants modest caution",
                    },
                ),
                discussion_summary=(
                    "Discussion preserved the evidence-first hypothesis."
                ),
                discussion_confidence=0.60,
            )
        if response_schema is DecisionResultPayload:
            skill_id = payload["skill_results"][0]["skill_id"]
            return DecisionResultPayload(
                direction=DecisionDirection.BULLISH,
                confidence=0.60,
                action=Action.BUY,
                reasoning=(
                    {
                        "reason": "skill and discussion support the hypothesis",
                        "skill_ids": [skill_id],
                        "discussion_refs": ["discussion_summary"],
                        "evidence_ids": [evidence_id],
                    },
                ),
                supporting_skills=(skill_id,),
                opposing_skills=(),
                discussion_refs=("discussion_summary",),
                evidence_refs=(evidence_id,),
                risks=(
                    {
                        "risk": "event already priced",
                        "uncertainty": "limited follow-up evidence",
                        "invalid_condition": "price fails to confirm",
                        "evidence_ids": [evidence_id],
                    },
                ),
                rejected_directions=(
                    {
                        "direction": DecisionDirection.BEARISH,
                        "reason": "no supplied evidence supports the bearish case",
                        "skill_ids": [skill_id],
                        "discussion_refs": ["discussion_summary"],
                        "evidence_ids": [evidence_id],
                    },
                ),
                decision_summary="Final decision follows the Brain discussion.",
            )
        raise AssertionError(f"unexpected response schema {response_schema}")


class FixtureMarketDataAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        self.calls += 1
        bars = [
            MarketBar(
                symbol=symbol,
                market="CN_A",
                trade_date=AS_OF.date(),
                open=Decimal("10.00"),
                high=Decimal("10.00"),
                low=Decimal("10.00"),
                close=Decimal("10.00"),
                volume=Decimal("1000"),
                amount=Decimal("10000"),
                adjustment=adjustment,
                source="fixture-test",
                fetched_at=AS_OF + timedelta(hours=1),
            ),
            MarketBar(
                symbol=symbol,
                market="CN_A",
                trade_date=(AS_OF + timedelta(days=3)).date(),
                open=Decimal("11.00"),
                high=Decimal("11.00"),
                low=Decimal("11.00"),
                close=Decimal("11.00"),
                volume=Decimal("1000"),
                amount=Decimal("11000"),
                adjustment=adjustment,
                source="fixture-test",
                fetched_at=AS_OF + timedelta(days=4),
            ),
        ]
        return [bar for bar in bars if start_date <= bar.trade_date <= end_date]


class FailingVibeAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, **kwargs: Any) -> object:
        self.calls += 1
        raise AssertionError("default Brain workflow must not call Vibe")


def test_default_research_runner_executes_brain_lifecycle_and_settles() -> None:
    storage = InMemoryStorage()
    lifecycle = DecisionLifecycleService(storage)
    watchlist = WatchlistService(storage).add_item(symbol="600519", market="CN")
    llm = CountingBrainLLM()
    market = FixtureMarketDataAdapter()
    vibe = FailingVibeAdapter()
    runner = ResearchRunner(
        lifecycle=lifecycle,
        market_data_adapter=market,
        vibe_trading_adapter=vibe,
        llm_adapter=llm,
        brain002_registry=default_brain002_registry(),
        brain_evidence_repository=FakeBrainEvidenceRepository(_brain_evidence()),
    )

    run = runner.run_research(
        watchlist_item_id=watchlist.watchlist_item_id,
        horizon_days=3,
        as_of=AS_OF + timedelta(hours=2),
        workflow="investment_committee",
        provider="fake",
        model="fake/model",
    )
    replay = runner.run_research(
        watchlist_item_id=watchlist.watchlist_item_id,
        horizon_days=3,
        as_of=AS_OF + timedelta(hours=2),
        workflow="investment_committee",
        provider="fake",
        model="fake/model",
    )

    assert run.status == "completed"
    assert replay.run_id == run.run_id
    assert vibe.calls == 0
    assert storage.list(DebateRecord) == []
    assert storage.list(DecisionProposal) == []
    hypotheses = storage.list(Hypothesis)
    assert hypotheses
    assert storage.list(SkillExecution)
    skill_results = storage.list(SkillResult)
    assert skill_results
    assert all(
        result.result_id not in set(hypothesis.supporting_report_ids)
        for hypothesis in hypotheses
        for result in skill_results
    )
    assert storage.list(DiscussionResult)
    assert storage.list(DecisionResult)
    decisions = storage.list(Decision)
    assert decisions
    assemblies = storage.list(DecisionAssemblyRecord)
    assert len(assemblies) == 1
    assert assemblies[0].debate_id is None
    assert assemblies[0].proposal_id is None
    assert assemblies[0].risk_review_id is None
    assert set(decisions[0].evidence_ids).issubset(set(assemblies[0].evidence_ids))

    first = ResearchSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=market,
    ).settle_due(as_of=AS_OF + timedelta(days=5))
    second = ResearchSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=market,
    ).settle_due(as_of=AS_OF + timedelta(days=6))

    assert len(first) == 1
    assert second == ()
    assert storage.list(DecisionOutcome)
    assert storage.list(DecisionEvaluation)
    learnings = storage.list(Learning)
    assert learnings
    assert all(
        learning.approval_status is ApprovalStatus.PENDING for learning in learnings
    )
    weight_learning = next(
        learning
        for learning in learnings
        if learning.learning_type is LearningType.AGENT_WEIGHT_UPDATE
    )
    assert weight_learning.after["application_mode"] == "proposal_only"
    assert len(storage.list(DecisionAssemblyRecord)) == 1


def _brain_evidence() -> tuple[BrainEvidence, ...]:
    return (
        _evidence_from_record(
            RSSIntakeRecord(
                source="policy-rss",
                source_url="https://example.test/rss.xml",
                published_at=AS_OF,
                collected_at=AS_OF + timedelta(minutes=1),
                raw_artifact_path=Path("rss.json"),
                title="Policy support for premium spirits consumption",
                summary="Policy news supports consumption recovery.",
                content="Policy support for premium spirits consumption recovery.",
                fingerprint=_fingerprint("rss"),
            ),
            metadata={"source_domain": "policy"},
        ),
        _evidence_from_record(
            WebpageIntakeRecord(
                source="market-web",
                source_url="https://example.test/news.html",
                published_at=AS_OF,
                collected_at=AS_OF + timedelta(minutes=2),
                raw_artifact_path=Path("web.html"),
                title="Retail channel checks improve",
                summary="Web report says channel checks improved.",
                content="Retail channel checks improved across distributors.",
                fingerprint=_fingerprint("web"),
            )
        ),
        _evidence_from_record(
            AnnouncementIntakeRecord(
                source="cninfo",
                source_identifier="600519-20260720",
                published_at=AS_OF,
                collected_at=AS_OF + timedelta(minutes=3),
                raw_artifact_path=Path("announcement.json"),
                title="Company announces stable quarterly operations",
                summary="Announcement reports stable operations.",
                content="Company announces stable quarterly operations.",
                fingerprint=_fingerprint("announcement"),
            )
        ),
    )


def _evidence_from_record(
    record: RSSIntakeRecord | WebpageIntakeRecord | AnnouncementIntakeRecord,
    *,
    metadata: dict[str, Any] | None = None,
) -> BrainEvidence:
    return BrainEvidence.from_provider_record(
        record,
        available_at=record.collected_at,
        metadata={
            "symbols": ["600519"],
            **(metadata or {}),
        },
    )


def _fingerprint(label: str) -> str:
    return uuid4().hex + uuid4().hex[:32]
