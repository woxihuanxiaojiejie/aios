from __future__ import annotations

from datetime import timedelta

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from tests.factories import (
    fixed_now,
    make_agent_report,
    make_decision,
    make_evaluation,
    make_evidence,
    make_experiment,
    make_hypothesis,
    make_learning,
    make_outcome,
    make_research_session,
    make_review,
    make_risk_review,
    make_watchlist_item,
)
from tests.integration.conftest import alembic_config, table_count
from tests.unit.test_brain004_persistence import decision_execution, decision_result
from tests.unit.test_formal_decision_persistence import rich_decision

from aios.application.debate import DebateService
from aios.kernel.brain004 import DecisionExecution, DecisionResult
from aios.kernel.debate import DecisionAssemblyRecord, RiskReview
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    AgentReportStatus,
    AgentRole,
    DecisionDirection,
    ExecutionExitReason,
    ExecutionStatus,
    HypothesisStatus,
    ResearchConclusion,
    ResearchSessionStatus,
    RiskVerdict,
    TradePlanStatus,
)
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    StorageOperationError,
)
from aios.kernel.evidence import Evidence
from aios.kernel.execution import SimulatedExecution
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.research_run import ResearchRun
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.kernel.trade_plan import TradePlan
from aios.kernel.watchlist import WatchlistItem, WatchlistStatus
from aios.storage.postgres.storage import PostgresStorage


def seed_lifecycle(
    storage: PostgresStorage,
) -> tuple[Evidence, Experiment, Decision, Review, Learning]:
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    decision = make_decision(experiment.experiment_id, evidence.evidence_id)
    review = make_review(decision.decision_id)
    learning = make_learning(review.review_id)
    for entity in [evidence, experiment, decision, review, learning]:
        storage.save(entity)
    return evidence, experiment, decision, review, learning


def test_save_and_read_all_core_entities(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, review, learning = seed_lifecycle(storage)

    assert storage.get(Evidence, evidence.evidence_id) == evidence
    assert storage.get(Experiment, experiment.experiment_id) == experiment
    assert storage.get(Decision, decision.decision_id) == decision
    assert storage.get(Review, review.review_id) == review
    assert storage.get(Learning, learning.learning_id) == learning


def test_list_exists_duplicate_and_missing(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    first = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000201",
        created_at=fixed_now() + timedelta(minutes=1),
    )
    second = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000200",
        created_at=fixed_now(),
    )

    storage.save(first)
    storage.save(second)

    assert storage.exists(Evidence, first.evidence_id)
    assert [item.evidence_id for item in storage.list(Evidence)] == [
        second.evidence_id,
        first.evidence_id,
    ]

    with pytest.raises(DuplicateEntityError):
        storage.save(first)

    with pytest.raises(MissingEntityError):
        storage.get(Evidence, "ev_missing")


def test_jsonb_fields_round_trip(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, review, learning = seed_lifecycle(storage)

    assert storage.get(Evidence, evidence.evidence_id).metadata["nested"] == {"page": 3}
    assert storage.get(Experiment, experiment.experiment_id).parameters == {
        "temperature": 0,
        "weights": [1, 2],
    }
    assert storage.get(Decision, decision.decision_id).evidence_ids == (
        evidence.evidence_id,
    )
    assert storage.get(Review, review.review_id).cause_tags == (
        "guidance",
        "momentum",
    )
    assert storage.get(Learning, learning.learning_id).after == {
        "weight": 0.45,
        "tags": ["guidance"],
    }


def test_rich_decision_postgres_round_trip(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    decision = rich_decision().model_copy(
        update={"experiment_id": experiment.experiment_id}
    )
    storage.save(evidence)
    storage.save(experiment)

    storage.save(decision)

    assert storage.get(Decision, decision.decision_id) == decision
    assert (
        storage.get_decision_by_decision_result_id(decision.decision_result_id or "")
        == decision
    )


def test_legacy_decision_without_rich_fields_still_reads(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, _review, _learning = seed_lifecycle(storage)

    persisted = storage.get(Decision, decision.decision_id)

    assert persisted.experiment_id == experiment.experiment_id
    assert persisted.evidence_ids == (evidence.evidence_id,)
    assert persisted.decision_result_id is None
    assert persisted.direction is None
    assert persisted.unavailable_fields == ()


def test_brain_risk_review_postgres_round_trip(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    review = RiskReview(
        proposal_id=None,
        verdict=RiskVerdict.MODIFY_CONDITIONS,
        final_conclusion=ResearchConclusion.BUY,
        final_confidence=0.55,
        reasons=("risk reviewed",),
        confidence_delta=-0.1,
        adjusted_position=0.25,
        condition_changes=("wait for confirmation",),
        converted_to_no_trade=False,
        research_session_id="rs_00000000-0000-0000-0000-000000000001",
        decision_result_id="ds_00000000-0000-0000-0000-000000000001",
        discussion_result_id="dr_00000000-0000-0000-0000-000000000001",
        skill_result_ids=("sr_00000000-0000-0000-0000-000000000001",),
        evidence_ids=("ev_00000000-0000-0000-0000-000000000001",),
        supporting_arguments=("support",),
        opposing_arguments=("oppose",),
        created_at=fixed_now(),
    )

    storage.save(review)

    persisted = storage.get(RiskReview, review.risk_review_id)
    assert persisted == review
    assert (
        storage.get_risk_review_by_decision_result_id(review.decision_result_id or "")
        == review
    )


def test_all_risk_review_verdicts_persist(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)

    for index, verdict in enumerate(
        (
            RiskVerdict.APPROVE,
            RiskVerdict.REDUCE_CONFIDENCE,
            RiskVerdict.REDUCE_POSITION,
            RiskVerdict.MODIFY_CONDITIONS,
            RiskVerdict.VETO,
        ),
        start=1,
    ):
        review = make_risk_review(
            risk_review_id=(f"rr_00000000-0000-0000-0000-00000000010{index}"),
            proposal_id=None,
        ).model_copy(
            update={
                "verdict": verdict,
                "final_conclusion": ResearchConclusion.NO_TRADE
                if verdict is RiskVerdict.VETO
                else ResearchConclusion.BUY,
                "final_confidence": 0.0 if verdict is RiskVerdict.VETO else 0.5,
                "converted_to_no_trade": verdict is RiskVerdict.VETO,
                "decision_result_id": (
                    f"ds_00000000-0000-0000-0000-00000000010{index}"
                ),
            }
        )
        storage.save(review)

    assert {review.verdict for review in storage.list(RiskReview)} == {
        RiskVerdict.APPROVE,
        RiskVerdict.REDUCE_CONFIDENCE,
        RiskVerdict.REDUCE_POSITION,
        RiskVerdict.MODIFY_CONDITIONS,
        RiskVerdict.VETO,
    }


def test_decision_settlement_query_methods(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, _review, _learning = seed_lifecycle(storage)
    created = fixed_now()
    plan = TradePlan(
        decision_id=decision.decision_id,
        research_session_id="rs_00000000-0000-0000-0000-000000000001",
        symbol=decision.symbol,
        direction=DecisionDirection.BULLISH,
        status=TradePlanStatus.READY,
        planned_entry=("10.00",),
        entry_conditions=("10.00",),
        target=(12.0, 13.0),
        stop_loss=9.5,
        invalidation_conditions=("close below 9.50",),
        planned_position=0.25,
        horizon="3d",
        expiry=created + timedelta(days=3),
        fee_model={"type": "not_specified"},
        slippage_model={"type": "not_specified"},
        created_at=created,
        updated_at=created,
    )
    execution = SimulatedExecution(
        trade_plan_id=plan.trade_plan_id,
        decision_id=decision.decision_id,
        research_session_id=plan.research_session_id,
        symbol=decision.symbol,
        direction=DecisionDirection.BULLISH,
        execution_status=ExecutionStatus.WAITING_SETTLEMENT,
        execution_date=created.date(),
        market_bar_id="akshare.stock_zh_a_hist:NVDA:2026-08-01:none",
        market_data_source="akshare.stock_zh_a_hist",
        planned_entry="10.00",
        executed_entry="10.00",
        executed_exit="9.50",
        position_size="0.25",
        fee="0.0010",
        slippage="0",
        realized_return="-0.0510",
        exit_reason=ExecutionExitReason.STOP,
        created_at=created,
        updated_at=created,
    )
    outcome = make_outcome(decision.decision_id, experiment.experiment_id)
    evaluation = make_evaluation(
        decision.decision_id,
        outcome.outcome_id,
        experiment.experiment_id,
    )

    storage.save(plan)
    storage.save(execution)
    storage.save(outcome)
    storage.save(evaluation)

    assert storage.get(TradePlan, plan.trade_plan_id) == plan
    assert storage.get(SimulatedExecution, execution.execution_id) == execution
    assert (
        storage.get_simulated_execution_by_trade_plan_id(plan.trade_plan_id)
        == execution
    )
    assert storage.get(DecisionOutcome, outcome.outcome_id) == outcome
    assert storage.get(DecisionEvaluation, evaluation.evaluation_id) == evaluation
    assert storage.get_decision_outcome_by_decision_id(decision.decision_id) == outcome
    assert (
        storage.get_decision_evaluation_by_decision_id(
            decision.decision_id,
            evaluation.evaluation_rules_version,
        )
        == evaluation
    )
    assert storage.get_decision_outcome_by_decision_id("dc_missing") is None
    assert (
        storage.get_decision_evaluation_by_decision_id(
            decision.decision_id,
            "missing-rules",
        )
        is None
    )
    assert storage.get(Evidence, evidence.evidence_id) == evidence


def test_write_failure_rolls_back(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    invalid = make_decision("ex_missing", "ev_missing")

    with pytest.raises(StorageOperationError):
        storage.save(invalid)

    assert table_count(migrated_postgres_url, "decisions") == 0


def test_review_decision_id_unique_constraint(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, experiment, decision, _review, _learning = seed_lifecycle(storage)
    duplicate_review = make_review(
        decision.decision_id,
        review_id="rv_00000000-0000-0000-0000-000000000002",
    )

    with pytest.raises(StorageOperationError):
        storage.save(duplicate_review)

    assert storage.get(Evidence, evidence.evidence_id) == evidence
    assert storage.get(Experiment, experiment.experiment_id) == experiment


def test_foreign_keys_and_delete_restrict(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    decision = make_decision(experiment.experiment_id, evidence.evidence_id)

    storage.save(evidence)
    with pytest.raises(StorageOperationError):
        storage.save(decision)

    storage.save(experiment)
    storage.save(decision)

    engine = create_engine(migrated_postgres_url)
    try:
        with engine.begin() as connection, pytest.raises(IntegrityError):
            connection.execute(
                text("delete from experiments where experiment_id = :id"),
                {"id": experiment.experiment_id},
            )
    finally:
        engine.dispose()


def test_migration_upgrade_downgrade_upgrade(postgres_url: str) -> None:
    config = alembic_config(postgres_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(postgres_url)
    try:
        inspector = inspect(engine)
        assert {
            "evidence",
            "experiments",
            "decisions",
            "reviews",
            "learnings",
            "llm_generation_records",
            "decision_outcomes",
            "decision_evaluations",
            "watchlist_items",
            "research_sessions",
            "research_session_evidence",
            "agent_reports",
            "agent_report_evidence",
            "hypotheses",
            "hypothesis_reports",
            "hypothesis_evidence",
            "debate_records",
            "debate_record_reports",
            "debate_record_hypotheses",
            "debate_statements",
            "debate_statement_evidence",
            "decision_proposals",
            "decision_proposal_hypotheses",
            "decision_proposal_evidence",
            "risk_reviews",
            "decision_assembly_records",
            "decision_executions",
            "decision_results",
            "trade_plans",
            "simulated_executions",
        } <= set(inspector.get_table_names())
        review_columns = {
            column["name"]: column for column in inspector.get_columns("reviews")
        }
        assert review_columns["actual_return"]["nullable"] is True
        assert review_columns["direction_correct"]["nullable"] is True
        assert review_columns["risk_limit_breached"]["nullable"] is True
        watchlist_indexes = {
            index["name"]: index for index in inspector.get_indexes("watchlist_items")
        }
        assert "uq_watchlist_active_symbol_market" in watchlist_indexes
        research_indexes = {
            index["name"]: index for index in inspector.get_indexes("research_sessions")
        }
        assert "uq_research_sessions_active_scope" in research_indexes
        report_indexes = {
            index["name"]: index for index in inspector.get_indexes("agent_reports")
        }
        assert "uq_agent_reports_active_session_role" in report_indexes
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(postgres_url)
    try:
        inspector = inspect(engine)
        assert "evidence" not in inspector.get_table_names()
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(postgres_url)
    try:
        inspector = inspect(engine)
        assert "decision_evaluations" in inspector.get_table_names()
    finally:
        engine.dispose()


def test_brain004_decision_storage_round_trip(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    execution = decision_execution()
    result = decision_result(execution.decision_execution_id)

    storage.save(execution)
    storage.save(result)

    assert storage.get(DecisionExecution, execution.decision_execution_id) == execution
    assert storage.get(DecisionResult, result.decision_result_id) == result
    assert storage.list(DecisionResult) == [result]


def test_watchlist_storage_filters_and_active_uniqueness(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    active = make_watchlist_item(symbol="600519", market="CN")
    archived = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000002",
        status=WatchlistStatus.ARCHIVED,
    )
    hk = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000003",
        symbol="0700",
        market="HK",
    )

    storage.save(active)
    storage.save(archived)
    storage.save(hk)

    assert storage.get(WatchlistItem, active.watchlist_item_id) == active
    assert storage.find_active_watchlist_item("CN", "600519") == active
    assert storage.list_watchlist_items(status=WatchlistStatus.ARCHIVED) == [archived]
    assert storage.list_watchlist_items(market="HK") == [hk]
    assert storage.list_watchlist_items(symbol="0700") == [hk]

    duplicate_active = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000004",
        symbol="600519",
        market="CN",
    )
    with pytest.raises(StorageOperationError):
        storage.save(duplicate_active)


def test_research_session_storage_filters_and_active_uniqueness(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000301",
    )
    watchlist = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000301",
    )
    session = make_research_session(
        research_session_id="rs_00000000-0000-0000-0000-000000000301",
        watchlist_item_id=watchlist.watchlist_item_id,
        evidence_ids=(evidence.evidence_id,),
    )
    duplicate_scope = make_research_session(
        research_session_id="rs_00000000-0000-0000-0000-000000000302",
        watchlist_item_id=watchlist.watchlist_item_id,
        evidence_ids=(),
    )

    storage.save(evidence)
    storage.save(watchlist)
    storage.save(session)

    assert storage.get(ResearchSession, session.research_session_id) == session
    assert (
        storage.find_active_research_session(
            watchlist.watchlist_item_id,
            session.scope.as_of,
            session.scope.horizon_days,
        )
        == session
    )
    assert storage.list_research_sessions(
        watchlist_item_id=watchlist.watchlist_item_id
    ) == [session]
    assert storage.list_research_sessions(symbol="600519") == [session]
    assert storage.list_research_sessions(market="CN") == [session]
    assert storage.list_research_sessions(horizon_days=3) == [session]

    with pytest.raises(StorageOperationError):
        storage.save(duplicate_scope)

    cancelled = session.model_copy(
        update={
            "status": ResearchSessionStatus.CANCELLED,
            "cancelled_at": session.scope.as_of + timedelta(minutes=10),
        },
    )
    storage.replace(cancelled)
    storage.save(duplicate_scope)

    assert (
        storage.find_active_research_session(
            watchlist.watchlist_item_id,
            session.scope.as_of,
            session.scope.horizon_days,
        )
        == duplicate_scope
    )


def test_research_run_storage_round_trip_and_filters(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    watchlist = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000350",
    )
    run = ResearchRun(
        run_id="run_00000000-0000-0000-0000-000000000350",
        watchlist_item_id=watchlist.watchlist_item_id,
        workflow="investment_committee",
        input_params={
            "as_of": fixed_now().isoformat(),
            "horizon_days": 3,
            "model": "fake",
            "provider": "fake",
            "symbol": watchlist.symbol,
            "workflow": "investment_committee",
        },
    )

    storage.save(watchlist)
    storage.save(run)

    assert storage.get(ResearchRun, run.run_id) == run
    assert storage.list_research_runs(
        watchlist_item_id=watchlist.watchlist_item_id
    ) == [run]
    assert storage.list_research_runs(status="running") == [run]


def test_agent_report_and_hypothesis_storage_filters_and_uniqueness(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000401",
    )
    watchlist = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000401",
    )
    session = make_research_session(
        research_session_id="rs_00000000-0000-0000-0000-000000000401",
        watchlist_item_id=watchlist.watchlist_item_id,
        evidence_ids=(evidence.evidence_id,),
    )
    report = make_agent_report(
        report_id="ar_00000000-0000-0000-0000-000000000401",
        research_session_id=session.research_session_id,
        evidence_ids=(evidence.evidence_id,),
    )
    duplicate_report = make_agent_report(
        report_id="ar_00000000-0000-0000-0000-000000000402",
        research_session_id=session.research_session_id,
    )
    hypothesis = make_hypothesis(
        hypothesis_id="hp_00000000-0000-0000-0000-000000000401",
        research_session_id=session.research_session_id,
        report_ids=(report.report_id,),
        evidence_ids=(evidence.evidence_id,),
    )

    for entity in [evidence, watchlist, session, report, hypothesis]:
        storage.save(entity)

    assert storage.get(AgentReport, report.report_id) == report
    assert storage.get(Hypothesis, hypothesis.hypothesis_id) == hypothesis
    assert (
        storage.find_active_agent_report(
            session.research_session_id,
            AgentRole.TECHNICAL,
        )
        == report
    )
    assert storage.list_agent_reports(
        research_session_id=session.research_session_id
    ) == [report]
    assert storage.list_agent_reports(role=AgentRole.TECHNICAL) == [report]
    assert storage.list_hypotheses(research_session_id=session.research_session_id) == [
        hypothesis
    ]
    assert storage.list_hypotheses(status=HypothesisStatus.PROPOSED) == [hypothesis]

    with pytest.raises(StorageOperationError):
        storage.save(duplicate_report)

    archived = report.model_copy(
        update={
            "status": AgentReportStatus.ARCHIVED,
            "archived_at": fixed_now() + timedelta(minutes=10),
        },
    )
    storage.replace(archived)
    storage.save(duplicate_report)

    assert (
        storage.find_active_agent_report(
            session.research_session_id,
            AgentRole.TECHNICAL,
        )
        == duplicate_report
    )


def test_debate_decision_assembly_postgres_round_trip(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000501",
    )
    watchlist = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000501",
    )
    session = make_research_session(
        research_session_id="rs_00000000-0000-0000-0000-000000000501",
        watchlist_item_id=watchlist.watchlist_item_id,
        evidence_ids=(evidence.evidence_id,),
    )
    report = make_agent_report(
        report_id="ar_00000000-0000-0000-0000-000000000501",
        research_session_id=session.research_session_id,
        evidence_ids=(evidence.evidence_id,),
    )
    hypothesis = make_hypothesis(
        hypothesis_id="hp_00000000-0000-0000-0000-000000000501",
        research_session_id=session.research_session_id,
        report_ids=(report.report_id,),
        evidence_ids=(evidence.evidence_id,),
    )
    for entity in [evidence, watchlist, session, report, hypothesis]:
        storage.save(entity)

    service = DebateService(storage)
    debate = service.create_debate(research_session_id=session.research_session_id)
    service.add_debate_statement(
        debate_id=debate.debate_id,
        agent_report_id=report.report_id,
        hypothesis_id=hypothesis.hypothesis_id,
        stance="support",
        reasoning="supported by report",
        evidence_ids=[evidence.evidence_id],
        confidence_before=0.5,
        confidence_after=0.6,
    )
    proposal = service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.BUY,
        confidence=0.7,
        thesis="buy thesis",
        supporting_hypothesis_ids=[hypothesis.hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence.evidence_id],
        risk_notes=["watch size"],
    )
    service.submit_risk_review(
        proposal_id=proposal.proposal_id,
        verdict=RiskVerdict.DOWNGRADE,
        final_conclusion=ResearchConclusion.WATCH,
        final_confidence=0.5,
        reasons=["risk downgrade"],
    )
    assembly = service.finalize_decision(proposal.proposal_id)

    assert isinstance(assembly, DecisionAssemblyRecord)
    assert storage.get(Decision, assembly.decision_id).action.value == "observe"
    assert service.finalize_decision(proposal.proposal_id) == assembly


def test_legacy_nullable_assembly_still_reads(migrated_postgres_url: str) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence, _experiment, decision, _review, _learning = seed_lifecycle(storage)
    session = make_research_session(
        research_session_id="rs_00000000-0000-0000-0000-000000000601",
        evidence_ids=(evidence.evidence_id,),
    )
    storage.save(make_watchlist_item(watchlist_item_id=session.scope.watchlist_item_id))
    storage.save(session)
    assembly = DecisionAssemblyRecord(
        research_session_id=session.research_session_id,
        debate_id=None,
        proposal_id=None,
        risk_review_id=None,
        decision_id=decision.decision_id,
        conclusion=ResearchConclusion.BUY,
        report_ids=(),
        hypothesis_ids=(),
        evidence_ids=(evidence.evidence_id,),
        created_at=fixed_now(),
    )

    storage.save(assembly)

    assert storage.get(DecisionAssemblyRecord, assembly.assembly_id) == assembly
