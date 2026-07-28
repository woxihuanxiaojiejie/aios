from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from tests.factories import (
    fixed_now,
    make_agent_report,
    make_debate,
    make_debate_statement,
    make_decision,
    make_decision_proposal,
    make_evidence,
    make_experiment,
    make_hypothesis,
    make_research_session,
    make_risk_review,
    make_watchlist_item,
)

from aios.api.app import create_app
from aios.kernel.debate import DecisionAssemblyRecord
from aios.kernel.enums import DecisionDirection, TradePlanStatus
from aios.kernel.research_run import ResearchRun
from aios.kernel.trade_plan import TradePlan
from aios.storage.memory import InMemoryStorage


def client() -> tuple[TestClient, InMemoryStorage]:
    storage = InMemoryStorage()
    return TestClient(create_app(storage=storage)), storage


def test_list_research_runs_supports_pagination_and_real_filters() -> None:
    api, storage = client()
    first_item = make_watchlist_item(symbol="600519", market="CN")
    second_item = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000002",
        symbol="000001",
        market="CN",
    )
    first_run = make_run(
        watchlist_item_id=first_item.watchlist_item_id,
        symbol=first_item.symbol,
        status="completed",
        created_at=fixed_now(),
    )
    second_run = make_run(
        run_id="run_00000000-0000-0000-0000-000000000002",
        watchlist_item_id=second_item.watchlist_item_id,
        symbol=second_item.symbol,
        status="running",
        created_at=fixed_now() + timedelta(minutes=1),
    )
    for entity in (first_item, second_item, first_run, second_run):
        storage.save(entity)

    response = api.get(
        "/api/v1/research/runs",
        params={"symbol": "000001", "status": "running", "limit": 1, "offset": 0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["count"] == 1
    assert body["items"][0]["run_id"] == second_run.run_id
    assert body["items"][0]["symbol"] == "000001"
    assert body["items"][0]["market"] == "CN"
    assert body["items"][0]["final_decision"] is None
    assert body["items"][0]["confidence"] is None


def test_research_run_detail_returns_persisted_chain_and_empty_nodes() -> None:
    api, storage = client()
    item = make_watchlist_item(symbol="600519", market="CN")
    evidence = make_evidence().model_copy(
        update={
            "symbols": ("600519",),
            "title": "Quarterly update",
            "source_url": "https://example.test/filing",
        }
    )
    session = make_research_session(
        watchlist_item_id=item.watchlist_item_id,
        symbol=item.symbol,
        market=item.market,
        evidence_ids=(evidence.evidence_id,),
    )
    report = make_agent_report(
        research_session_id=session.research_session_id,
        evidence_ids=(evidence.evidence_id,),
    )
    failed_report = make_agent_report(
        report_id="ar_00000000-0000-0000-0000-000000000002",
        research_session_id=session.research_session_id,
    ).model_copy(
        update={
            "role": "sentiment",
            "summary": "parser failed before summary extraction",
            "stance": "unknown",
            "confidence": 0.0,
            "source": "brain002",
            "raw_reference": "validation_error: missing confidence",
        }
    )
    hypothesis = make_hypothesis(
        research_session_id=session.research_session_id,
        report_ids=(report.report_id,),
        evidence_ids=(evidence.evidence_id,),
    )
    debate = make_debate(
        research_session_id=session.research_session_id,
        report_ids=(report.report_id, failed_report.report_id),
        hypothesis_ids=(hypothesis.hypothesis_id,),
    )
    statement = make_debate_statement(
        debate_id=debate.debate_id,
        report_id=report.report_id,
        hypothesis_id=hypothesis.hypothesis_id,
        evidence_ids=(evidence.evidence_id,),
    )
    proposal = make_decision_proposal(
        debate_id=debate.debate_id,
        hypothesis_ids=(hypothesis.hypothesis_id,),
        evidence_ids=(evidence.evidence_id,),
    )
    risk_review = make_risk_review(proposal_id=proposal.proposal_id)
    experiment = make_experiment(evidence.evidence_id)
    decision = make_decision(
        experiment.experiment_id,
        evidence.evidence_id,
    ).model_copy(
        update={
            "research_session_id": session.research_session_id,
            "direction": DecisionDirection.BULLISH,
            "entry_conditions": ("breakout confirmation",),
            "invalidation_conditions": ("policy reversal",),
            "risk_factors": ("liquidity",),
        }
    )
    assembly = DecisionAssemblyRecord(
        research_session_id=session.research_session_id,
        debate_id=debate.debate_id,
        proposal_id=proposal.proposal_id,
        risk_review_id=risk_review.risk_review_id,
        decision_id=decision.decision_id,
        conclusion="buy",
        report_ids=(report.report_id, failed_report.report_id),
        hypothesis_ids=(hypothesis.hypothesis_id,),
        evidence_ids=(evidence.evidence_id,),
    )
    trade_plan = TradePlan(
        decision_id=decision.decision_id,
        research_session_id=session.research_session_id,
        symbol=item.symbol,
        direction=DecisionDirection.BULLISH,
        status=TradePlanStatus.READY,
        planned_entry=("breakout confirmation",),
        target=(10.0, 12.0),
        stop_loss=8.5,
        invalidation_conditions=("policy reversal",),
        planned_position=0.2,
        horizon="3d",
        expiry=fixed_now() + timedelta(days=3),
    )
    run = make_run(
        watchlist_item_id=item.watchlist_item_id,
        symbol=item.symbol,
        research_session_id=session.research_session_id,
        status="completed",
    )
    for entity in (
        item,
        evidence,
        session,
        report,
        failed_report,
        hypothesis,
        debate,
        statement,
        proposal,
        risk_review,
        experiment,
        decision,
        assembly,
        trade_plan,
        run,
    ):
        storage.save(entity)

    response = api.get(f"/api/v1/research/runs/{run.run_id}/detail")

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["run_id"] == run.run_id
    assert body["watchlist_item"]["market"] == "CN"
    assert body["session"]["research_session_id"] == session.research_session_id
    assert body["evidence"][0]["evidence_id"] == evidence.evidence_id
    assert body["evidence"][0]["source_url"] == "https://example.test/filing"
    assert {item["role"] for item in body["skill_reports"]} == {
        "technical",
        "sentiment",
    }
    assert body["hypotheses"][0]["hypothesis_id"] == hypothesis.hypothesis_id
    assert body["discussion"]["debates"][0]["debate_id"] == debate.debate_id
    assert body["discussion"]["statements"][0]["statement_id"] == statement.statement_id
    assert body["discussion"]["proposal"]["proposal_id"] == proposal.proposal_id
    assert (
        body["discussion"]["risk_review"]["risk_review_id"]
        == risk_review.risk_review_id
    )
    assert body["discussion"]["assembly"]["assembly_id"] == assembly.assembly_id
    assert body["decision"]["decision_id"] == decision.decision_id
    assert body["trade_plan"]["trade_plan_id"] == trade_plan.trade_plan_id
    assert "api_key" not in str(body).lower()
    assert "database_url" not in str(body).lower()


def test_research_run_detail_404_and_empty_nodes() -> None:
    api, storage = client()
    run = make_run()
    storage.save(make_watchlist_item())
    storage.save(run)

    missing = api.get("/api/v1/research/runs/run_missing/detail")
    detail = api.get(f"/api/v1/research/runs/{run.run_id}/detail")

    assert missing.status_code == 404
    body = detail.json()
    assert body["session"] is None
    assert body["evidence"] == []
    assert body["skill_reports"] == []
    assert body["hypotheses"] == []
    assert body["discussion"]["debates"] == []
    assert body["decision"] is None
    assert body["trade_plan"] is None


def make_run(
    *,
    run_id: str = "run_00000000-0000-0000-0000-000000000001",
    watchlist_item_id: str = "wl_00000000-0000-0000-0000-000000000001",
    symbol: str = "600519",
    research_session_id: str | None = None,
    status: str = "running",
    created_at: datetime | None = None,
) -> ResearchRun:
    now = created_at or fixed_now()
    return ResearchRun(
        run_id=run_id,
        research_session_id=research_session_id,
        watchlist_item_id=watchlist_item_id,
        symbol=symbol,
        research_window_key=f"{symbol}:2026-07-28:3",
        current_stage="completed" if status == "completed" else "session",
        status=status,
        vibe_run_id=None,
        workflow="investment_committee",
        input_params={"horizon_days": 3, "as_of": now.isoformat()},
        raw_output_reference=None,
        failed_stage=None,
        error_type=None,
        error=None,
        finished_at=now + timedelta(minutes=5) if status == "completed" else None,
        created_at=now,
        updated_at=now,
    )
