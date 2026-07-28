from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from tests.factories import (
    make_decision,
    make_evaluation,
    make_evidence,
    make_experiment,
    make_learning,
    make_outcome,
    make_research_session,
    make_review,
    make_watchlist_item,
)

from aios.api.app import create_app
from aios.kernel.enums import DecisionDirection, ExecutionExitReason, ExecutionStatus
from aios.kernel.execution import SimulatedExecution
from aios.kernel.research_run import ResearchRun
from aios.kernel.trade_plan import TradePlan
from aios.storage.memory import InMemoryStorage


def test_dashboard_summary_returns_empty_database() -> None:
    api = TestClient(create_app(storage=InMemoryStorage()))

    response = api.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["counts"] == {
        "research_runs": 0,
        "completed_research_runs": 0,
        "failed_or_resumable_research_runs": 0,
        "decisions": 0,
        "trade_plans": 0,
        "simulated_executions": 0,
        "settlements": 0,
        "pending_learning_proposals": 0,
        "positive_settlements": 0,
        "negative_settlements": 0,
    }
    assert body["performance"]["average_return"] is None
    assert body["attention_required"] == []
    assert body["recent_research"] == []
    assert body["recent_settlements"] == []


def test_dashboard_counts_sorting_attention_and_real_id_linkage() -> None:
    storage = InMemoryStorage()
    complete = _chain("001", datetime(2026, 7, 28, 8, tzinfo=UTC), include="complete")
    no_plan = _chain("002", datetime(2026, 7, 28, 9, tzinfo=UTC), include="decision")
    no_settlement = _chain(
        "003",
        datetime(2026, 7, 28, 10, tzinfo=UTC),
        include="execution",
    )
    no_review = _chain(
        "004",
        datetime(2026, 7, 28, 11, tzinfo=UTC),
        include="evaluation",
    )
    failed = _failed_run("005", datetime(2026, 7, 28, 12, tzinfo=UTC))
    for entity in (
        *complete["entities"],
        *no_plan["entities"],
        *no_settlement["entities"],
        *no_review["entities"],
        *failed["entities"],
    ):
        storage.save(entity)
    api = TestClient(create_app(storage=storage))

    response = api.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["research_runs"] == 5
    assert body["counts"]["completed_research_runs"] == 4
    assert body["counts"]["failed_or_resumable_research_runs"] == 1
    assert body["counts"]["decisions"] == 4
    assert body["counts"]["trade_plans"] == 3
    assert body["counts"]["simulated_executions"] == 3
    assert body["counts"]["settlements"] == 2
    assert body["counts"]["pending_learning_proposals"] == 1
    assert body["counts"]["positive_settlements"] == 2
    assert body["counts"]["negative_settlements"] == 0
    assert body["performance"]["average_return"] == "0.049"
    assert [row["run_id"] for row in body["recent_research"][:3]] == [
        failed["run"].run_id,
        no_review["run"].run_id,
        no_settlement["run"].run_id,
    ]
    assert [row["settlement_id"] for row in body["recent_settlements"]] == [
        no_review["outcome"].outcome_id,
        complete["outcome"].outcome_id,
    ]
    attention_types = {item["type"]: item for item in body["attention_required"]}
    assert attention_types["research_run_failed"]["detail_id"] == failed["run"].run_id
    assert attention_types["missing_trade_plan"]["detail_id"] == no_plan["run"].run_id
    assert (
        attention_types["missing_settlement"]["detail_id"]
        == no_settlement["execution"].execution_id
    )
    assert (
        attention_types["missing_review"]["detail_id"]
        == no_review["outcome"].outcome_id
    )
    assert all(item["symbol"] == "600519" for item in body["attention_required"])


def test_dashboard_is_read_only() -> None:
    api = TestClient(create_app(storage=InMemoryStorage()))

    response = api.post("/api/v1/dashboard/summary")

    assert response.status_code == 405


def _chain(
    suffix: str,
    created_at: datetime,
    *,
    include: str,
) -> dict[str, object]:
    ids = f"00000000-0000-0000-0000-000000000{suffix}"
    watchlist = make_watchlist_item(
        watchlist_item_id=f"wl_{ids}",
        symbol="600519",
        market="CN",
        created_at=created_at,
        updated_at=created_at,
    )
    evidence = make_evidence(evidence_id=f"ev_{ids}", created_at=created_at)
    experiment = make_experiment(
        evidence.evidence_id,
        experiment_id=f"ex_{ids}",
        created_at=created_at,
    )
    session = make_research_session(
        research_session_id=f"rs_{ids}",
        watchlist_item_id=watchlist.watchlist_item_id,
        symbol="600519",
        market="CN",
        evidence_ids=(evidence.evidence_id,),
        as_of=created_at,
    )
    decision = make_decision(
        experiment.experiment_id,
        evidence.evidence_id,
        decision_id=f"dc_{ids}",
        created_at=created_at + timedelta(minutes=1),
    ).model_copy(
        update={
            "symbol": "600519",
            "research_session_id": session.research_session_id,
            "direction": DecisionDirection.BULLISH,
        }
    )
    run = ResearchRun(
        run_id=f"run_{ids}",
        research_session_id=session.research_session_id,
        watchlist_item_id=watchlist.watchlist_item_id,
        symbol="600519",
        current_stage="completed",
        status="completed",
        workflow="investment_committee",
        input_params={"trigger_method": "manual"},
        finished_at=created_at + timedelta(minutes=8),
        created_at=created_at,
        updated_at=created_at + timedelta(minutes=8),
    )
    entities: list[object] = [watchlist, evidence, experiment, session, decision, run]
    result: dict[str, object] = {
        "entities": entities,
        "run": run,
        "decision": decision,
    }
    if include == "decision":
        return result
    plan = TradePlan(
        trade_plan_id=f"tp_{ids}",
        decision_id=decision.decision_id,
        research_session_id=session.research_session_id,
        symbol="600519",
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
        created_at=created_at + timedelta(minutes=2),
        updated_at=created_at + timedelta(minutes=2),
    )
    entities.append(plan)
    result["plan"] = plan
    if include == "plan":
        return result
    execution = SimulatedExecution(
        execution_id=f"sx_{ids}",
        trade_plan_id=plan.trade_plan_id,
        decision_id=decision.decision_id,
        research_session_id=session.research_session_id,
        symbol="600519",
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
        created_at=created_at + timedelta(minutes=3),
        updated_at=created_at + timedelta(minutes=3),
    )
    entities.append(execution)
    result["execution"] = execution
    if include == "execution":
        return result
    outcome = make_outcome(
        decision.decision_id,
        experiment.experiment_id,
        outcome_id=f"oc_{ids}",
        created_at=created_at + timedelta(minutes=4),
    ).model_copy(
        update={
            "symbol": "600519",
            "execution_id": execution.execution_id,
            "trade_plan_id": plan.trade_plan_id,
            "research_session_id": session.research_session_id,
            "return_rate": Decimal("0.049"),
            "pnl": Decimal("0.01225"),
        }
    )
    entities.append(outcome)
    result["outcome"] = outcome
    if include == "settlement":
        return result
    evaluation = make_evaluation(
        decision.decision_id,
        outcome.outcome_id,
        experiment.experiment_id,
        evaluation_id=f"de_{ids}",
        created_at=created_at + timedelta(minutes=5),
    )
    entities.append(evaluation)
    result["evaluation"] = evaluation
    if include == "evaluation":
        return result
    review = make_review(
        decision.decision_id,
        review_id=f"rv_{ids}",
        created_at=created_at + timedelta(minutes=6),
    )
    learning = make_learning(
        review.review_id,
        learning_id=f"lr_{ids}",
        created_at=created_at + timedelta(minutes=7),
    )
    entities.extend([review, learning])
    result.update({"review": review, "learning": learning})
    return result


def _failed_run(suffix: str, created_at: datetime) -> dict[str, object]:
    ids = f"00000000-0000-0000-0000-000000000{suffix}"
    watchlist = make_watchlist_item(
        watchlist_item_id=f"wl_{ids}",
        symbol="600519",
        market="CN",
        created_at=created_at,
        updated_at=created_at,
    )
    run = ResearchRun(
        run_id=f"run_{ids}",
        research_session_id=None,
        watchlist_item_id=watchlist.watchlist_item_id,
        symbol="600519",
        current_stage="failed",
        status="failed",
        failed_stage="decision",
        error_type="provider_error",
        error="provider failed",
        workflow="investment_committee",
        input_params={"trigger_method": "manual"},
        created_at=created_at,
        updated_at=created_at,
        finished_at=created_at + timedelta(minutes=1),
    )
    return {"entities": [watchlist, run], "run": run}
