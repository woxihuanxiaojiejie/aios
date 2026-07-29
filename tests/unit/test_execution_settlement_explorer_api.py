from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from tests.factories import (
    fixed_now,
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


def test_execution_list_filters_paginates_sorts_and_preserves_real_links() -> None:
    api, _storage, first, second = _client_with_two_chains()

    default_page = api.get("/api/v1/simulated-executions")
    paged = api.get(
        "/api/v1/simulated-executions",
        params={"page": 2, "page_size": 1, "sort": "created_at"},
    )
    symbol = api.get("/api/v1/simulated-executions", params={"symbol": "600519"})
    market = api.get("/api/v1/simulated-executions", params={"market": "HK"})
    status_filter = api.get(
        "/api/v1/simulated-executions",
        params={"status": "waiting_settlement"},
    )
    created = api.get(
        "/api/v1/simulated-executions",
        params={
            "created_from": first["execution"].created_at.isoformat(),
            "created_to": first["execution"].created_at.isoformat(),
        },
    )

    assert default_page.status_code == 200
    assert default_page.json()["total"] == 2
    assert paged.json()["items"][0]["execution_id"] == second["execution"].execution_id
    assert symbol.json()["total"] == 2
    assert market.json()["items"][0]["execution_id"] == second["execution"].execution_id
    assert status_filter.json()["total"] == 2
    assert {item["status"] for item in status_filter.json()["items"]} == {
        "waiting_settlement"
    }
    assert created.json()["items"][0]["execution_id"] == first["execution"].execution_id
    row = next(
        item
        for item in default_page.json()["items"]
        if item["execution_id"] == first["execution"].execution_id
    )
    assert row["market"] == "CN"
    assert row["research_run_id"] == first["run"].run_id
    assert row["trade_plan_id"] == first["plan"].trade_plan_id
    assert row["settlement_id"] == first["outcome"].outcome_id


def test_execution_detail_returns_complete_and_partial_chain_by_real_ids() -> None:
    api, _storage, first, second = _client_with_two_chains(
        include_second_settlement=False
    )

    complete = api.get(
        f"/api/v1/simulated-executions/{first['execution'].execution_id}",
    )
    partial = api.get(
        f"/api/v1/simulated-executions/{second['execution'].execution_id}",
    )
    missing = api.get("/api/v1/simulated-executions/sx_missing")

    assert complete.status_code == 200
    body = complete.json()
    assert body["research_run"]["run_id"] == first["run"].run_id
    assert (
        body["research_session"]["research_session_id"]
        == first["session"].research_session_id
    )
    assert body["decision"]["decision_id"] == first["decision"].decision_id
    assert body["trade_plan"]["trade_plan_id"] == first["plan"].trade_plan_id
    assert (
        body["simulated_execution"]["execution_id"] == first["execution"].execution_id
    )
    assert body["settlement"]["outcome_id"] == first["outcome"].outcome_id
    assert body["evaluation"]["outcome_id"] == first["outcome"].outcome_id
    assert body["review"]["review_id"] == first["review"].review_id
    assert [item["review_id"] for item in body["learning_proposals"]] == [
        first["learning"].review_id,
    ]

    partial_body = partial.json()
    assert partial.status_code == 200
    assert partial_body["research_run"]["run_id"] == second["run"].run_id
    assert partial_body["settlement"] is None
    assert partial_body["evaluation"] is None
    assert partial_body["review"] is None
    assert partial_body["learning_proposals"] == []
    assert missing.status_code == 404


def test_settlement_list_and_detail_use_decision_outcome_ids() -> None:
    api, _storage, _first, second = _client_with_two_chains()

    response = api.get(
        "/api/v1/settlements",
        params={"market": "HK", "status": "settled", "sort": "-settled_at"},
    )
    detail = api.get(f"/api/v1/settlements/{second['outcome'].outcome_id}")
    missing = api.get("/api/v1/settlements/oc_missing")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    row = response.json()["items"][0]
    assert row["settlement_id"] == second["outcome"].outcome_id
    assert row["execution_id"] == second["execution"].execution_id
    assert row["market"] == "HK"
    assert row["research_run_id"] == second["run"].run_id

    assert detail.status_code == 200
    body = detail.json()
    assert body["research_run"]["run_id"] == second["run"].run_id
    assert (
        body["simulated_execution"]["execution_id"] == second["execution"].execution_id
    )
    assert body["settlement"]["outcome_id"] == second["outcome"].outcome_id
    assert body["evaluation"]["outcome_id"] == second["outcome"].outcome_id
    assert body["review"]["decision_id"] == second["decision"].decision_id
    assert body["learning_proposals"][0]["review_id"] == second["review"].review_id
    assert missing.status_code == 404


def test_research_run_detail_includes_downstream_nodes_and_empty_states() -> None:
    api, storage, first, _second = _client_with_two_chains()
    empty_item = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000099",
        symbol="600519",
        market="CN",
    )
    empty_run = _run(
        "run_00000000-0000-0000-0000-000000000099",
        empty_item.watchlist_item_id,
        None,
        "600519",
        fixed_now() + timedelta(hours=4),
    )
    storage.save(empty_item)
    storage.save(empty_run)

    complete = api.get(f"/api/v1/research/runs/{first['run'].run_id}/detail")
    empty = api.get(f"/api/v1/research/runs/{empty_run.run_id}/detail")

    assert complete.status_code == 200
    body = complete.json()
    assert (
        body["simulated_execution"]["execution_id"] == first["execution"].execution_id
    )
    assert body["settlement"]["outcome_id"] == first["outcome"].outcome_id
    assert body["evaluation"]["outcome_id"] == first["outcome"].outcome_id
    assert body["review"]["review_id"] == first["review"].review_id
    assert body["learning_proposals"][0]["review_id"] == first["review"].review_id

    assert empty.status_code == 200
    empty_body = empty.json()
    assert empty_body["simulated_execution"] is None
    assert empty_body["settlement"] is None
    assert empty_body["evaluation"] is None
    assert empty_body["review"] is None
    assert empty_body["learning_proposals"] == []


def _client_with_two_chains(
    *,
    include_second_settlement: bool = True,
) -> tuple[TestClient, InMemoryStorage, dict[str, object], dict[str, object]]:
    storage = InMemoryStorage()
    first = _chain(
        suffix="001",
        symbol="600519",
        market="CN",
        created_at=datetime(2026, 7, 28, 8, tzinfo=UTC),
        include_settlement=True,
    )
    second = _chain(
        suffix="002",
        symbol="600519",
        market="HK",
        created_at=datetime(2026, 7, 28, 9, tzinfo=UTC),
        include_settlement=include_second_settlement,
    )
    for entity in (*first["entities"], *second["entities"]):
        storage.save(entity)
    return TestClient(create_app(storage=storage)), storage, first, second


def _chain(
    *,
    suffix: str,
    symbol: str,
    market: str,
    created_at: datetime,
    include_settlement: bool,
) -> dict[str, object]:
    ids = f"00000000-0000-0000-0000-000000000{suffix}"
    watchlist = make_watchlist_item(
        watchlist_item_id=f"wl_{ids}",
        symbol=symbol,
        market=market,
        created_at=created_at,
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
        symbol=symbol,
        market=market,
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
            "symbol": symbol,
            "research_session_id": session.research_session_id,
            "direction": DecisionDirection.BULLISH,
            "target_range": (10.0, 12.0),
            "entry_conditions": ("10.00",),
            "stop_loss": 9.5,
            "invalidation_conditions": ("close below 9.50",),
            "position_suggestion": 0.25,
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
        created_at=created_at + timedelta(minutes=2),
        updated_at=created_at + timedelta(minutes=2),
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
        created_at=created_at + timedelta(minutes=3),
        updated_at=created_at + timedelta(minutes=3),
    )
    run = _run(
        f"run_{ids}",
        watchlist.watchlist_item_id,
        session.research_session_id,
        symbol,
        created_at,
    )
    entities: list[object] = [
        watchlist,
        evidence,
        experiment,
        session,
        decision,
        plan,
        execution,
        run,
    ]
    result: dict[str, object] = {
        "entities": entities,
        "watchlist": watchlist,
        "evidence": evidence,
        "experiment": experiment,
        "session": session,
        "decision": decision,
        "plan": plan,
        "execution": execution,
        "run": run,
    }
    if include_settlement:
        outcome = make_outcome(
            decision.decision_id,
            experiment.experiment_id,
            outcome_id=f"oc_{ids}",
            created_at=created_at + timedelta(minutes=4),
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
            created_at=created_at + timedelta(minutes=5),
        )
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
        wrong_learning = make_learning(
            "rv_00000000-0000-0000-0000-000000000999",
            learning_id=f"lr_99900000-0000-0000-0000-000000000{suffix}",
            created_at=created_at + timedelta(minutes=8),
        )
        entities.extend([outcome, evaluation, review, learning, wrong_learning])
        result.update(
            {
                "outcome": outcome,
                "evaluation": evaluation,
                "review": review,
                "learning": learning,
            }
        )
    return result


def _run(
    run_id: str,
    watchlist_item_id: str,
    research_session_id: str | None,
    symbol: str,
    created_at: datetime,
) -> ResearchRun:
    return ResearchRun(
        run_id=run_id,
        research_session_id=research_session_id,
        watchlist_item_id=watchlist_item_id,
        symbol=symbol,
        research_window_key=f"{symbol}:2026-07-28:3",
        current_stage="completed",
        status="completed",
        workflow="investment_committee",
        input_params={"trigger_method": "manual"},
        created_at=created_at,
        updated_at=created_at,
        finished_at=created_at + timedelta(minutes=10),
    )
