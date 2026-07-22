from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient
from tests.integration.conftest import table_count

from aios.adapters.market_data import Adjustment, MarketBar
from aios.api.app import create_app
from aios.kernel.debate import (
    DebateRecord,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.decision import Decision
from aios.kernel.evidence import Evidence
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.review import Review
from aios.kernel.settlement import (
    DecisionEvaluation,
    DecisionOutcome,
    ResearchSettlementRecord,
)
from aios.kernel.watchlist import WatchlistItem
from aios.storage.postgres.storage import PostgresStorage


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


def client(database_url: str, adapter: FixtureMarketDataAdapter) -> TestClient:
    return TestClient(
        create_app(
            storage=PostgresStorage(database_url),
            market_data_adapter=adapter,
        )
    )


def test_research_lifecycle_e2e_success_replay_and_reverse_traceability(
    migrated_postgres_url: str,
) -> None:
    as_of = datetime.now(UTC) + timedelta(hours=1)
    valid_until = as_of + timedelta(days=3)
    adapter = FixtureMarketDataAdapter(
        [
            market_bar(datetime.now(UTC).date(), "10.00"),
            market_bar(valid_until.date() + timedelta(days=1), "10.60"),
        ]
    )
    api = client(migrated_postgres_url, adapter)

    watchlist = _post(
        api,
        "/api/v1/research/watchlist",
        {"symbol": "600519", "market": "CN", "note": "fixture e2e"},
    )
    evidence = _post(
        api,
        "/api/v1/evidence",
        {
            "evidence_type": "market_fixture",
            "source": "fixture-test",
            "symbols": ["600519"],
            "published_at": (as_of - timedelta(days=1)).isoformat(),
            "available_at": (as_of - timedelta(days=1)).isoformat(),
            "summary": "fixture evidence for e2e lifecycle",
            "reliability": 0.9,
            "content_hash": "e2e-fixture-evidence-001",
            "metadata": {"fixture": True},
        },
    )
    session = _post(
        api,
        "/api/v1/research/sessions",
        {
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": as_of.isoformat(),
            "evidence_ids": [evidence["evidence_id"]],
        },
    )
    report = _post(
        api,
        f"/api/v1/research/sessions/{session['research_session_id']}/agent-reports",
        {
            "role": "technical",
            "summary": "fixture trend supports upside",
            "stance": "buy",
            "confidence": 0.75,
            "evidence_ids": [evidence["evidence_id"]],
            "source": "manual-fixture",
        },
    )
    hypothesis = _post(
        api,
        f"/api/v1/research/sessions/{session['research_session_id']}/hypotheses",
        {
            "statement": "fixture upside continues",
            "rationale": "report and fixture evidence agree",
            "direction": "bullish",
            "horizon_days": 3,
            "confidence": 0.7,
            "supporting_report_ids": [report["report_id"]],
            "supporting_evidence_ids": [evidence["evidence_id"]],
        },
    )
    debate = _post(
        api,
        f"/api/v1/research/sessions/{session['research_session_id']}/debates",
        {},
    )
    _post(
        api,
        f"/api/v1/research/debates/{debate['debate_id']}/statements",
        {
            "agent_report_id": report["report_id"],
            "hypothesis_id": hypothesis["hypothesis_id"],
            "stance": "support",
            "reasoning": "fixture statement supports the hypothesis",
            "evidence_ids": [evidence["evidence_id"]],
            "confidence_before": 0.5,
            "confidence_after": 0.7,
        },
    )
    proposal = _post(
        api,
        f"/api/v1/research/debates/{debate['debate_id']}/proposal",
        {
            "conclusion": "buy",
            "confidence": 0.7,
            "thesis": "fixture buy thesis",
            "supporting_hypothesis_ids": [hypothesis["hypothesis_id"]],
            "rejected_hypothesis_ids": [],
            "evidence_ids": [evidence["evidence_id"]],
            "risk_notes": ["fixture risk bounded"],
        },
    )
    risk = _post(
        api,
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        {
            "verdict": "approve",
            "final_conclusion": "buy",
            "final_confidence": 0.7,
            "reasons": ["fixture risk accepted"],
        },
    )
    assembly = _post(
        api,
        f"/api/v1/research/proposals/{proposal['proposal_id']}/finalize",
        {},
    )
    settlement = _post(
        api,
        f"/api/v1/research/assemblies/{assembly['assembly_id']}/settlement",
        {"as_of": (valid_until + timedelta(days=1)).isoformat()},
    )
    replay_settlement = _post(
        api,
        f"/api/v1/research/assemblies/{assembly['assembly_id']}/settlement",
        {"as_of": (valid_until + timedelta(days=2)).isoformat()},
    )

    assert (
        replay_settlement["record"]["research_settlement_id"]
        == settlement["record"]["research_settlement_id"]
    )
    assert (
        replay_settlement["outcome"]["outcome_id"]
        == settlement["outcome"]["outcome_id"]
    )
    assert (
        replay_settlement["evaluation"]["evaluation_id"]
        == settlement["evaluation"]["evaluation_id"]
    )
    assert replay_settlement["review"]["review_id"] == settlement["review"]["review_id"]
    assert [item["learning_id"] for item in replay_settlement["learnings"]] == [
        item["learning_id"] for item in settlement["learnings"]
    ]
    assert adapter.calls == 1
    assert _conflict(
        api,
        f"/api/v1/research/debates/{debate['debate_id']}/proposal",
        {
            "conclusion": "watch",
            "confidence": 0.5,
            "thesis": "duplicate proposal",
            "supporting_hypothesis_ids": [hypothesis["hypothesis_id"]],
            "rejected_hypothesis_ids": [],
            "evidence_ids": [evidence["evidence_id"]],
            "risk_notes": [],
        },
    )
    assert _conflict(
        api,
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        {
            "verdict": "approve",
            "final_conclusion": "buy",
            "final_confidence": 0.7,
            "reasons": ["duplicate review"],
        },
    )
    assert (
        _post(
            api,
            f"/api/v1/research/proposals/{proposal['proposal_id']}/finalize",
            {},
        )
        == assembly
    )

    storage = PostgresStorage(migrated_postgres_url)
    _assert_counts(migrated_postgres_url)
    _assert_reverse_trace(
        storage,
        learning_id=settlement["learnings"][0]["learning_id"],
        watchlist_id=watchlist["watchlist_item_id"],
        session_id=session["research_session_id"],
        evidence_id=evidence["evidence_id"],
        report_id=report["report_id"],
        hypothesis_id=hypothesis["hypothesis_id"],
        debate_id=debate["debate_id"],
        proposal_id=proposal["proposal_id"],
        risk_review_id=risk["risk_review_id"],
        assembly_id=assembly["assembly_id"],
        decision_id=assembly["decision_id"],
    )


def test_research_lifecycle_e2e_rejects_cancelled_session_without_dirty_data(
    migrated_postgres_url: str,
) -> None:
    now = datetime.now(UTC)
    adapter = FixtureMarketDataAdapter([])
    api = client(migrated_postgres_url, adapter)
    watchlist = _post(
        api,
        "/api/v1/research/watchlist",
        {"symbol": "600519", "market": "CN"},
    )
    evidence = _post(
        api,
        "/api/v1/evidence",
        {
            "evidence_type": "market_fixture",
            "source": "fixture-test",
            "symbols": ["600519"],
            "published_at": (now - timedelta(days=1)).isoformat(),
            "available_at": (now - timedelta(days=1)).isoformat(),
            "summary": "fixture evidence for cancelled session",
            "reliability": 0.9,
            "content_hash": "e2e-fixture-evidence-cancelled",
            "metadata": {"fixture": True},
        },
    )
    session = _post(
        api,
        "/api/v1/research/sessions",
        {
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": (now + timedelta(hours=1)).isoformat(),
            "evidence_ids": [evidence["evidence_id"]],
        },
    )
    _post(
        api,
        f"/api/v1/research/sessions/{session['research_session_id']}/agent-reports",
        {
            "role": "technical",
            "summary": "fixture report",
            "stance": "watch",
            "confidence": 0.6,
            "evidence_ids": [evidence["evidence_id"]],
            "source": "manual-fixture",
        },
    )
    _post(api, f"/api/v1/research/sessions/{session['research_session_id']}/cancel", {})

    failed = api.post(
        f"/api/v1/research/sessions/{session['research_session_id']}/debates"
    )

    assert failed.status_code == 409
    assert failed.json()["error"]["code"] == "invalid_state_transition"
    assert table_count(migrated_postgres_url, "debate_records") == 0
    assert table_count(migrated_postgres_url, "decision_proposals") == 0
    assert table_count(migrated_postgres_url, "risk_reviews") == 0
    assert table_count(migrated_postgres_url, "decisions") == 0
    assert table_count(migrated_postgres_url, "decision_outcomes") == 0
    assert table_count(migrated_postgres_url, "decision_evaluations") == 0
    assert table_count(migrated_postgres_url, "reviews") == 0
    assert table_count(migrated_postgres_url, "learnings") == 0


def test_research_lifecycle_e2e_rejects_not_ready_settlement_without_dirty_data(
    migrated_postgres_url: str,
) -> None:
    now = datetime.now(UTC)
    valid_until = now + timedelta(days=3, hours=1)
    adapter = FixtureMarketDataAdapter(
        [
            market_bar(now.date(), "10.00"),
            market_bar(valid_until.date() + timedelta(days=1), "10.60"),
        ]
    )
    api = client(migrated_postgres_url, adapter)
    assembly = _finalized_fixture_chain(
        api,
        as_of=now + timedelta(hours=1),
        valid_until=valid_until,
    )

    failed = api.post(
        f"/api/v1/research/assemblies/{assembly['assembly_id']}/settlement",
        json={"as_of": (valid_until - timedelta(seconds=1)).isoformat()},
    )

    assert failed.status_code == 409
    assert failed.json()["error"]["code"] == "invalid_state_transition"
    assert table_count(migrated_postgres_url, "decision_outcomes") == 0
    assert table_count(migrated_postgres_url, "decision_evaluations") == 0
    assert table_count(migrated_postgres_url, "reviews") == 0
    assert table_count(migrated_postgres_url, "learnings") == 0
    assert table_count(migrated_postgres_url, "research_settlement_records") == 0


def _finalized_fixture_chain(
    api: TestClient,
    *,
    as_of: datetime,
    valid_until: datetime,
) -> dict[str, Any]:
    watchlist = _post(
        api,
        "/api/v1/research/watchlist",
        {"symbol": "600519", "market": "CN"},
    )
    evidence = _post(
        api,
        "/api/v1/evidence",
        {
            "evidence_type": "market_fixture",
            "source": "fixture-test",
            "symbols": ["600519"],
            "published_at": (as_of - timedelta(days=1)).isoformat(),
            "available_at": (as_of - timedelta(days=1)).isoformat(),
            "summary": "fixture evidence",
            "reliability": 0.9,
            "content_hash": f"fixture-{as_of.timestamp()}",
            "metadata": {"fixture": True},
        },
    )
    session = _post(
        api,
        "/api/v1/research/sessions",
        {
            "watchlist_item_id": watchlist["watchlist_item_id"],
            "horizon_days": 3,
            "as_of": as_of.isoformat(),
            "evidence_ids": [evidence["evidence_id"]],
        },
    )
    assert session["scope"]["valid_until"] == valid_until.isoformat().replace(
        "+00:00", "Z"
    )
    report = _post(
        api,
        f"/api/v1/research/sessions/{session['research_session_id']}/agent-reports",
        {
            "role": "technical",
            "summary": "fixture report",
            "stance": "buy",
            "confidence": 0.7,
            "evidence_ids": [evidence["evidence_id"]],
            "source": "manual-fixture",
        },
    )
    hypothesis = _post(
        api,
        f"/api/v1/research/sessions/{session['research_session_id']}/hypotheses",
        {
            "statement": "fixture hypothesis",
            "rationale": "fixture report",
            "direction": "bullish",
            "horizon_days": 3,
            "confidence": 0.7,
            "supporting_report_ids": [report["report_id"]],
            "supporting_evidence_ids": [evidence["evidence_id"]],
        },
    )
    debate = _post(
        api,
        f"/api/v1/research/sessions/{session['research_session_id']}/debates",
        {},
    )
    proposal = _post(
        api,
        f"/api/v1/research/debates/{debate['debate_id']}/proposal",
        {
            "conclusion": "buy",
            "confidence": 0.7,
            "thesis": "fixture thesis",
            "supporting_hypothesis_ids": [hypothesis["hypothesis_id"]],
            "rejected_hypothesis_ids": [],
            "evidence_ids": [evidence["evidence_id"]],
            "risk_notes": [],
        },
    )
    _post(
        api,
        f"/api/v1/research/proposals/{proposal['proposal_id']}/risk-review",
        {
            "verdict": "approve",
            "final_conclusion": "buy",
            "final_confidence": 0.7,
            "reasons": ["fixture risk accepted"],
        },
    )
    return _post(
        api,
        f"/api/v1/research/proposals/{proposal['proposal_id']}/finalize",
        {},
    )


def _assert_counts(database_url: str) -> None:
    expected = {
        "watchlist_items": 1,
        "evidence": 1,
        "research_sessions": 1,
        "agent_reports": 1,
        "hypotheses": 1,
        "debate_records": 1,
        "decision_proposals": 1,
        "risk_reviews": 1,
        "decisions": 1,
        "decision_outcomes": 1,
        "decision_evaluations": 1,
        "reviews": 1,
        "learnings": 2,
        "research_settlement_records": 1,
    }
    for table, count in expected.items():
        assert table_count(database_url, table) == count


def _assert_reverse_trace(
    storage: PostgresStorage,
    *,
    learning_id: str,
    watchlist_id: str,
    session_id: str,
    evidence_id: str,
    report_id: str,
    hypothesis_id: str,
    debate_id: str,
    proposal_id: str,
    risk_review_id: str,
    assembly_id: str,
    decision_id: str,
) -> None:
    learning = storage.get(Learning, learning_id)
    review = storage.get(Review, learning.review_id)
    settlement = storage.list(ResearchSettlementRecord)[0]
    evaluation = storage.get(DecisionEvaluation, settlement.evaluation_id)
    outcome = storage.get(DecisionOutcome, settlement.outcome_id)
    decision = storage.get(Decision, settlement.decision_id)
    assembly = storage.get(DecisionAssemblyRecord, settlement.assembly_id)
    risk = storage.get(RiskReview, settlement.risk_review_id)
    proposal = storage.get(DecisionProposal, settlement.proposal_id)
    debate = storage.get(DebateRecord, settlement.debate_id)
    hypothesis = storage.get(Hypothesis, settlement.hypothesis_ids[0])
    report = storage.get(AgentReport, settlement.report_ids[0])
    evidence = storage.get(Evidence, settlement.evidence_ids[0])
    session = storage.get(ResearchSession, settlement.research_session_id)
    watchlist = storage.get(WatchlistItem, session.scope.watchlist_item_id)

    assert review.review_id == settlement.review_id
    assert evaluation.decision_id == decision_id
    assert outcome.decision_id == decision_id
    assert decision.decision_id == decision_id
    assert assembly.assembly_id == assembly_id
    assert risk.risk_review_id == risk_review_id
    assert proposal.proposal_id == proposal_id
    assert debate.debate_id == debate_id
    assert hypothesis.hypothesis_id == hypothesis_id
    assert report.report_id == report_id
    assert evidence.evidence_id == evidence_id
    assert session.research_session_id == session_id
    assert watchlist.watchlist_item_id == watchlist_id


def _post(api: TestClient, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = api.post(path, json=payload)
    assert response.status_code in {200, 201}, response.text
    return response.json()


def _conflict(api: TestClient, path: str, payload: dict[str, Any]) -> bool:
    response = api.post(path, json=payload)
    return (
        response.status_code == 409
        and response.json()["error"]["code"] == "entity_conflict"
    )
