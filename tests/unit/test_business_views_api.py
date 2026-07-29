from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from tests.factories import (
    make_analysis_task,
    make_decision,
    make_decision_execution,
    make_decision_result,
    make_discussion_execution,
    make_discussion_result,
    make_evaluation,
    make_evidence,
    make_experiment,
    make_learning,
    make_outcome,
    make_research_session,
    make_review,
    make_skill_execution,
    make_skill_result,
    make_watchlist_item,
)

from aios.api.app import create_app
from aios.kernel.enums import DecisionDirection, ExecutionExitReason, ExecutionStatus
from aios.kernel.execution import SimulatedExecution
from aios.kernel.learning import Learning
from aios.kernel.research_run import ResearchRun
from aios.kernel.trade_plan import TradePlan
from aios.storage.memory import InMemoryStorage


def test_research_detail_includes_brain_structured_records_by_real_ids() -> None:
    api, _storage, chain = _client_with_chain()

    response = api.get(f"/api/v1/research/runs/{chain['run'].run_id}/detail")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_task"]["task_id"] == chain["analysis_task"].task_id
    assert body["skill_executions"][0]["execution_id"] == (
        chain["skill_execution"].execution_id
    )
    assert body["skill_results"][0]["result_id"] == chain["skill_result"].result_id
    assert body["discussion_result"]["discussion_result_id"] == (
        chain["discussion_result"].discussion_result_id
    )
    assert body["decision_result"]["decision_result_id"] == (
        chain["decision_result"].decision_result_id
    )


def test_decisions_summary_returns_business_rows_without_symbol_guessing() -> None:
    api, storage, first = _client_with_chain(symbol="600519", market="CN")
    _api2, _storage2, second = _client_with_chain(
        storage=storage,
        symbol="600519",
        market="HK",
        suffix="002",
    )

    response = api.get("/api/v1/decisions/summary", params={"page_size": 20})

    assert response.status_code == 200
    rows = response.json()["items"]
    by_decision = {row["decision_id"]: row for row in rows}
    assert by_decision[first["decision"].decision_id]["market"] == "CN"
    assert by_decision[first["decision"].decision_id]["research_run_id"] == (
        first["run"].run_id
    )
    assert by_decision[second["decision"].decision_id]["market"] == "HK"
    assert by_decision[second["decision"].decision_id]["research_run_id"] == (
        second["run"].run_id
    )
    assert by_decision[first["decision"].decision_id]["trade_plan_status"] == "ready"
    assert (
        by_decision[first["decision"].decision_id]["simulated_execution_status"]
        == "waiting_settlement"
    )


def test_reviews_summary_and_learning_detail_return_business_context() -> None:
    api, _storage, chain = _client_with_chain()

    reviews = api.get("/api/v1/reviews/summary")
    learning = api.get(f"/api/v1/learnings/{chain['learning'].learning_id}/detail")

    assert reviews.status_code == 200
    review_row = reviews.json()["items"][0]
    assert review_row["settlement_id"] == chain["outcome"].outcome_id
    assert review_row["research_run_id"] == chain["run"].run_id
    assert review_row["directional_result"] == "correct"
    assert review_row["risk_result"] == "within_limit"
    assert review_row["learning_proposal_status"] == "pending"

    assert learning.status_code == 200
    body = learning.json()
    assert body["learning"]["learning_id"] == chain["learning"].learning_id
    assert body["review"]["review_id"] == chain["review"].review_id
    assert body["decision"]["decision_id"] == chain["decision"].decision_id
    assert body["research_run"]["run_id"] == chain["run"].run_id
    assert "technical_details" in body
    assert body["current_value_summary"]
    assert body["proposed_value_summary"]


def test_learning_defer_changes_only_approval_status() -> None:
    api, storage, chain = _client_with_chain()
    before = storage.get(Learning, chain["learning"].learning_id)

    response = api.post(f"/api/v1/learnings/{before.learning_id}/defer")

    assert response.status_code == 200
    assert response.json()["approval_status"] == "deferred"
    after = storage.get(Learning, before.learning_id)
    assert after.before == before.before
    assert after.after == before.after
    assert after.approval_status == "deferred"


def test_default_lists_hide_marked_test_data_and_can_include_it() -> None:
    storage = InMemoryStorage()
    api, _storage, real = _client_with_chain(storage=storage, suffix="101")
    _api2, _storage2, marked = _client_with_chain(
        storage=storage,
        suffix="102",
        symbol="ACCEPT1",
        input_params={"environment": "acceptance", "test_run": True},
    )

    default_research = api.get("/api/v1/research/runs")
    all_research = api.get("/api/v1/research/runs", params={"include_test_data": True})
    default_dashboard = api.get("/api/v1/dashboard/summary")
    all_dashboard = api.get(
        "/api/v1/dashboard/summary",
        params={"include_test_data": True},
    )
    default_learnings = api.get("/api/v1/learnings")
    all_learnings = api.get("/api/v1/learnings", params={"include_test_data": True})

    assert default_research.status_code == 200
    assert [item["run_id"] for item in default_research.json()["items"]] == [
        real["run"].run_id
    ]
    assert {item["run_id"] for item in all_research.json()["items"]} == {
        real["run"].run_id,
        marked["run"].run_id,
    }
    assert default_dashboard.json()["counts"]["research_runs"] == 1
    assert all_dashboard.json()["counts"]["research_runs"] == 2
    assert [item["learning_id"] for item in default_learnings.json()["items"]] == [
        real["learning"].learning_id
    ]
    assert {item["learning_id"] for item in all_learnings.json()["items"]} == {
        real["learning"].learning_id,
        marked["learning"].learning_id,
    }


def _client_with_chain(
    *,
    storage: InMemoryStorage | None = None,
    suffix: str = "001",
    symbol: str = "600519",
    market: str = "CN",
    input_params: dict[str, object] | None = None,
) -> tuple[TestClient, InMemoryStorage, dict[str, object]]:
    resolved_storage = storage or InMemoryStorage()
    created_at = datetime(2026, 7, 28, 8, tzinfo=UTC)
    chain = _chain(
        suffix=suffix,
        symbol=symbol,
        market=market,
        created_at=created_at,
        input_params=input_params or {"trigger_method": "manual"},
    )
    for entity in chain["entities"]:
        resolved_storage.save(entity)
    return TestClient(create_app(storage=resolved_storage)), resolved_storage, chain


def _chain(
    *,
    suffix: str,
    symbol: str,
    market: str,
    created_at: datetime,
    input_params: dict[str, object],
) -> dict[str, object]:
    ids = f"10000000-0000-0000-0000-000000000{suffix}"
    watchlist = make_watchlist_item(
        watchlist_item_id=f"wl_{ids}",
        symbol=symbol,
        market=market,
        created_at=created_at,
        updated_at=created_at,
    )
    evidence = make_evidence(
        evidence_id=f"ev_{ids}",
        created_at=created_at,
    ).model_copy(update={"symbols": (symbol,), "metadata": dict(input_params)})
    experiment = make_experiment(
        evidence.evidence_id,
        experiment_id=f"ex_{ids}",
        created_at=created_at,
    )
    session = make_research_session(
        research_session_id=f"rs_{ids}",
        watchlist_item_id=watchlist.watchlist_item_id,
        symbol=symbol,
        market=market,
        evidence_ids=(evidence.evidence_id,),
        as_of=created_at,
    )
    task = make_analysis_task(
        task_id=f"at_{ids}",
        symbol=symbol,
        market=market,
        evidence_ids=(evidence.evidence_id,),
        created_at=created_at,
    )
    skill_execution = make_skill_execution(
        execution_id=f"sxn_{ids}",
        task_id=task.task_id,
        created_at=created_at + timedelta(minutes=1),
    )
    skill_result = make_skill_result(
        result_id=f"sr_{ids}",
        execution_id=skill_execution.execution_id,
        evidence_ids=(evidence.evidence_id,),
        created_at=created_at + timedelta(minutes=2),
    )
    discussion_execution = make_discussion_execution(
        discussion_execution_id=f"dx_{ids}",
        task_id=task.task_id,
        skill_result_ids=(skill_result.result_id,),
        created_at=created_at + timedelta(minutes=3),
    )
    discussion_result = make_discussion_result(
        discussion_result_id=f"dr_{ids}",
        discussion_execution_id=discussion_execution.discussion_execution_id,
        task_id=task.task_id,
        skill_result_ids=(skill_result.result_id,),
        evidence_ids=(evidence.evidence_id,),
        created_at=created_at + timedelta(minutes=4),
    )
    decision_execution = make_decision_execution(
        decision_execution_id=f"dxe_{ids}",
        task_id=task.task_id,
        discussion_result_id=discussion_result.discussion_result_id,
        skill_result_ids=(skill_result.result_id,),
        evidence_ids=(evidence.evidence_id,),
        created_at=created_at + timedelta(minutes=5),
    )
    decision_result = make_decision_result(
        decision_result_id=f"ds_{ids}",
        decision_execution_id=decision_execution.decision_execution_id,
        task_id=task.task_id,
        discussion_result_id=discussion_result.discussion_result_id,
        skill_result_ids=(skill_result.result_id,),
        evidence_ids=(evidence.evidence_id,),
        created_at=created_at + timedelta(minutes=6),
    )
    decision = make_decision(
        experiment.experiment_id,
        evidence.evidence_id,
        decision_id=f"dc_{ids}",
        created_at=created_at + timedelta(minutes=7),
    ).model_copy(
        update={
            "symbol": symbol,
            "research_session_id": session.research_session_id,
            "decision_result_id": decision_result.decision_result_id,
            "direction": DecisionDirection.BULLISH,
            "risk_review_id": None,
        }
    )
    plan = TradePlan(
        trade_plan_id=f"tp_{ids}",
        decision_id=decision.decision_id,
        research_session_id=session.research_session_id,
        symbol=symbol,
        direction=DecisionDirection.BULLISH,
        status="ready",
        planned_entry=("10.00",),
        entry_conditions=("10.00",),
        target=(10.0, 12.0),
        stop_loss=9.5,
        invalidation_conditions=("close below 9.50",),
        planned_position=0.25,
        horizon="3d",
        expiry=created_at + timedelta(days=3),
        created_at=created_at + timedelta(minutes=8),
        updated_at=created_at + timedelta(minutes=8),
    )
    execution = SimulatedExecution(
        execution_id=f"sx_{ids}",
        trade_plan_id=plan.trade_plan_id,
        decision_id=decision.decision_id,
        research_session_id=session.research_session_id,
        symbol=symbol,
        direction=DecisionDirection.BULLISH,
        execution_status=ExecutionStatus.WAITING_SETTLEMENT,
        execution_date=created_at.date(),
        market_bar_id=f"bar-{suffix}",
        market_data_source="fixture",
        planned_entry="10.00",
        executed_entry=Decimal("10.00"),
        executed_exit=Decimal("10.50"),
        position_size=Decimal("0.25"),
        fee=Decimal("0.001"),
        slippage=Decimal("0"),
        realized_return=Decimal("0.049"),
        exit_reason=ExecutionExitReason.TARGET,
        created_at=created_at + timedelta(minutes=9),
        updated_at=created_at + timedelta(minutes=9),
    )
    outcome = make_outcome(
        decision.decision_id,
        experiment.experiment_id,
        outcome_id=f"oc_{ids}",
        created_at=created_at + timedelta(minutes=10),
    ).model_copy(
        update={
            "symbol": symbol,
            "execution_id": execution.execution_id,
            "trade_plan_id": plan.trade_plan_id,
            "research_session_id": session.research_session_id,
            "return_rate": Decimal("0.049"),
            "pnl": Decimal("0.01225"),
        }
    )
    evaluation = make_evaluation(
        decision.decision_id,
        outcome.outcome_id,
        experiment.experiment_id,
        evaluation_id=f"de_{ids}",
        created_at=created_at + timedelta(minutes=11),
    )
    review = make_review(
        decision.decision_id,
        review_id=f"rv_{ids}",
        created_at=created_at + timedelta(minutes=12),
    )
    learning = make_learning(
        review.review_id,
        learning_id=f"lr_{ids}",
        created_at=created_at + timedelta(minutes=13),
    )
    if input_params:
        learning = learning.model_copy(
            update={
                "before": {**learning.before, **input_params},
                "after": {**learning.after, **input_params},
            }
        )
    run = ResearchRun(
        run_id=f"run_{ids}",
        research_session_id=session.research_session_id,
        watchlist_item_id=watchlist.watchlist_item_id,
        symbol=symbol,
        current_stage="completed",
        status="completed",
        workflow="investment_committee",
        input_params=input_params,
        finished_at=created_at + timedelta(minutes=14),
        created_at=created_at,
        updated_at=created_at + timedelta(minutes=14),
    )
    entities = [
        watchlist,
        evidence,
        experiment,
        session,
        task,
        skill_execution,
        skill_result,
        discussion_execution,
        discussion_result,
        decision_execution,
        decision_result,
        decision,
        plan,
        execution,
        outcome,
        evaluation,
        review,
        learning,
        run,
    ]
    return {
        "entities": entities,
        "watchlist": watchlist,
        "evidence": evidence,
        "experiment": experiment,
        "session": session,
        "analysis_task": task,
        "skill_execution": skill_execution,
        "skill_result": skill_result,
        "discussion_execution": discussion_execution,
        "discussion_result": discussion_result,
        "decision_execution": decision_execution,
        "decision_result": decision_result,
        "decision": decision,
        "plan": plan,
        "execution": execution,
        "outcome": outcome,
        "evaluation": evaluation,
        "review": review,
        "learning": learning,
        "run": run,
    }
