from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from tests.factories import (
    make_agent_report,
    make_evidence,
    make_hypothesis,
    make_research_session,
    make_watchlist_item,
)

from aios.adapters.market_data import Adjustment, MarketBar
from aios.application.debate import DebateService
from aios.application.research_settlement import ResearchSettlementService
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    ApprovalStatus,
    DebateStance,
    EvaluationFinalResult,
    LearningType,
    ResearchConclusion,
    RiskVerdict,
)
from aios.kernel.errors import DecisionNotReadyForSettlementError
from aios.kernel.learning import Learning
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


class FixtureMarketDataAdapter:
    def __init__(self, bars: list[MarketBar]) -> None:
        self.bars = bars
        self.calls = 0

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        self.calls += 1
        return [
            bar
            for bar in self.bars
            if bar.symbol == symbol and start_date <= bar.trade_date <= end_date
        ]


def market_bar(trade_date: date, close: str, *, symbol: str = "600519") -> MarketBar:
    price = Decimal(close)
    return MarketBar(
        symbol=symbol,
        market="CN_A",
        trade_date=trade_date,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        adjustment=Adjustment.NONE,
        source="fixture-test",
        fetched_at=datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
    )


def seed_finalized_research_decision() -> tuple[InMemoryStorage, str, Decision]:
    storage = InMemoryStorage()
    evidence = make_evidence().model_copy(update={"symbols": ("600519",)})
    watchlist = make_watchlist_item()
    session = make_research_session(
        evidence_ids=(evidence.evidence_id,),
        as_of=datetime.now(UTC) + timedelta(hours=1),
    )
    report = make_agent_report(
        research_session_id=session.research_session_id,
        evidence_ids=(evidence.evidence_id,),
    )
    hypothesis = make_hypothesis(
        research_session_id=session.research_session_id,
        report_ids=(report.report_id,),
        evidence_ids=(evidence.evidence_id,),
    )
    for entity in (evidence, watchlist, session, report, hypothesis):
        storage.save(entity)
    debate_service = DebateService(storage)
    debate = debate_service.create_debate(
        research_session_id=session.research_session_id
    )
    debate_service.add_debate_statement(
        debate_id=debate.debate_id,
        agent_report_id=report.report_id,
        hypothesis_id=hypothesis.hypothesis_id,
        stance=DebateStance.SUPPORT,
        reasoning="report supports hypothesis",
        evidence_ids=[evidence.evidence_id],
        confidence_before=0.5,
        confidence_after=0.7,
    )
    proposal = debate_service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.BUY,
        confidence=0.7,
        thesis="buy with risk controls",
        supporting_hypothesis_ids=[hypothesis.hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence.evidence_id],
        risk_notes=["size small"],
    )
    debate_service.submit_risk_review(
        proposal_id=proposal.proposal_id,
        verdict=RiskVerdict.APPROVE,
        final_conclusion=ResearchConclusion.BUY,
        final_confidence=0.7,
        reasons=["risk accepted"],
    )
    assembly = debate_service.finalize_decision(proposal.proposal_id)
    decision = storage.get(Decision, assembly.decision_id)
    return storage, assembly.assembly_id, decision


def test_research_settlement_links_existing_lifecycle_and_proposes_learning() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    adapter = FixtureMarketDataAdapter(
        [
            market_bar(decision.created_at.date(), "10.00"),
            market_bar(decision.valid_until.date() + timedelta(days=1), "10.50"),
        ]
    )
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=adapter,
    )

    result = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=1),
    )
    second = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=2),
    )

    assert second.record == result.record
    assert second.outcome == result.outcome
    assert adapter.calls == 1
    assert len(storage.list(DecisionOutcome)) == 1
    assert len(storage.list(DecisionEvaluation)) == 1
    assert len(storage.list(Learning)) == 2
    assert result.record.research_session_id == (
        "rs_00000000-0000-0000-0000-000000000001"
    )
    assert result.record.assembly_id == assembly_id
    assert result.record.decision_id == decision.decision_id
    assert result.record.outcome_id == result.outcome.outcome_id
    assert result.record.evaluation_id == result.evaluation.evaluation_id
    assert result.record.review_id == result.review.review_id
    assert result.record.evidence_ids == decision.evidence_ids
    assert result.record.report_ids == ("ar_00000000-0000-0000-0000-000000000001",)
    assert result.record.hypothesis_ids == ("hp_00000000-0000-0000-0000-000000000001",)
    assert result.evaluation.final_result is EvaluationFinalResult.PASS
    assert "final conclusion correct" in result.review.review_summary
    assert "supported hypotheses" in result.review.review_summary
    assert "stronger reports" in result.review.review_summary
    assert "Debate/RiskReview" in result.review.review_summary
    assert {learning.learning_type for learning in result.learnings} == {
        LearningType.AGENT_WEIGHT_UPDATE,
        LearningType.RULE_UPDATE,
    }
    assert all(
        learning.approval_status is ApprovalStatus.PENDING
        for learning in result.learnings
    )


def test_research_settlement_uses_session_valid_until_for_readiness() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FixtureMarketDataAdapter([]),
    )

    with pytest.raises(DecisionNotReadyForSettlementError):
        service.settle_assembly(
            assembly_id=assembly_id,
            as_of=decision.valid_until - timedelta(seconds=1),
        )


def test_research_settlement_rejects_decision_horizon_drift() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    storage.replace(decision.model_copy(update={"horizon": "7d"}))
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FixtureMarketDataAdapter([]),
    )

    with pytest.raises(ValueError, match="ResearchSession horizon"):
        service.settle_assembly(
            assembly_id=assembly_id,
            as_of=decision.valid_until + timedelta(days=1),
        )
