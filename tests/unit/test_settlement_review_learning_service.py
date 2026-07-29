from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from tests.factories import (
    make_decision,
    make_evidence,
    make_experiment,
    make_research_session,
    make_watchlist_item,
)

from aios.adapters.market_data import Adjustment, MarketBar
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.application.settlement import SettlementService
from aios.application.simulated_execution import SimulatedExecutionService
from aios.application.trade_plan import TradePlanService
from aios.kernel.enums import (
    DecisionDirection,
    EvaluationScore,
    ExecutionExitReason,
    LearningType,
    ResearchSessionStatus,
)
from aios.kernel.execution import SimulatedExecution
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres.mapper import model_to_entity, to_model


class StaticMarketDataAdapter:
    def __init__(self, bars: list[MarketBar]) -> None:
        self.bars = bars

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        return [
            bar
            for bar in self.bars
            if bar.symbol == symbol and start_date <= bar.trade_date <= end_date
        ]


def test_settlement_evaluation_review_learning_round_trip_models() -> None:
    storage, execution, adapter = _executed_stop_plan()
    result = SettlementService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=adapter,
    ).settle_execution(execution.execution_id)

    assert model_to_entity(to_model(result.outcome)) == result.outcome
    assert model_to_entity(to_model(result.evaluation)) == result.evaluation
    assert model_to_entity(to_model(result.review)) == result.review
    assert (
        model_to_entity(to_model(result.learning_proposal)) == result.learning_proposal
    )


def test_settlement_calculates_holding_days_pnl_and_excursions() -> None:
    storage, execution, adapter = _executed_stop_plan()

    result = SettlementService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=adapter,
    ).settle_execution(execution.execution_id)

    assert result.outcome.pnl == Decimal("-0.012750")
    assert result.outcome.return_rate == Decimal("-0.0510")
    assert result.outcome.holding_days == 0
    assert result.outcome.exit_reason is ExecutionExitReason.STOP
    assert result.outcome.max_drawdown == Decimal("-0.0610")
    assert result.outcome.max_favorable_excursion == Decimal("0.2490")


def test_evaluation_uses_fixed_scores() -> None:
    storage, execution, adapter = _executed_stop_plan()

    result = SettlementService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=adapter,
    ).settle_execution(execution.execution_id)

    assert result.evaluation.prediction_accuracy is EvaluationScore.POOR
    assert result.evaluation.timing_accuracy is EvaluationScore.GOOD
    assert result.evaluation.risk_control is EvaluationScore.GOOD
    assert result.evaluation.execution_quality is EvaluationScore.GOOD


def test_review_references_inputs_by_id_and_learning_is_proposal_only() -> None:
    storage, execution, adapter = _executed_stop_plan()

    result = SettlementService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=adapter,
    ).settle_execution(execution.execution_id)

    refs = result.review.reference_ids
    assert refs["evidence"] == ["ev_00000000-0000-0000-0000-000000000001"]
    assert refs["decision"] == [execution.decision_id]
    assert refs["trade_plan"] == [execution.trade_plan_id]
    assert refs["execution"] == [execution.execution_id]
    assert refs["settlement"] == [result.outcome.outcome_id]
    assert refs["evaluation"] == [result.evaluation.evaluation_id]
    assert set(refs) >= {
        "skill_result",
        "discussion",
        "risk_review",
    }
    assert result.learning_proposal.learning_type in {
        LearningType.AGENT_WEIGHT_UPDATE,
        LearningType.SKILL_WEIGHT_UPDATE,
        LearningType.PROMPT_UPDATE,
        LearningType.RULE_UPDATE,
        LearningType.HYPOTHESIS_UPDATE,
    }
    assert result.learning_proposal.approval_status.value == "pending"
    assert result.learning_proposal.after["status"] == "proposal_only"


def test_settlement_review_learning_are_idempotent_and_lifecycle_completes() -> None:
    storage, execution, adapter = _executed_stop_plan()
    service = SettlementService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=adapter,
    )

    first = service.settle_execution(execution.execution_id)
    second = service.settle_execution(execution.execution_id)

    assert second == first
    assert storage.list(DecisionOutcome) == [first.outcome]
    assert storage.list(DecisionEvaluation) == [first.evaluation]
    assert storage.list(Review) == [first.review]
    assert storage.list(Learning) == [first.learning_proposal]
    session = storage.get(
        type(make_research_session()),
        "rs_00000000-0000-0000-0000-000000000001",
    )
    assert session.status is ResearchSessionStatus.COMPLETED
    assert [event.to_state for event in session.transition_log[-4:]] == [
        ResearchSessionStatus.SETTLED,
        ResearchSessionStatus.REVIEWED,
        ResearchSessionStatus.LEARNING_PROPOSED,
        ResearchSessionStatus.COMPLETED,
    ]


def _executed_stop_plan() -> tuple[
    InMemoryStorage,
    SimulatedExecution,
    StaticMarketDataAdapter,
]:
    storage = InMemoryStorage()
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    watchlist = make_watchlist_item()
    session = make_research_session(as_of=datetime(2026, 8, 1, tzinfo=UTC))
    decision = make_decision(
        experiment.experiment_id,
        evidence.evidence_id,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    ).model_copy(
        update={
            "symbol": "600519",
            "research_session_id": session.research_session_id,
            "direction": DecisionDirection.BULLISH,
            "target_range": (12.0, 13.0),
            "entry_conditions": ("10.00",),
            "stop_loss": 9.5,
            "invalidation_conditions": ("close below 9.50",),
            "position_suggestion": 0.25,
            "horizon": "3d",
            "valid_until": datetime(2026, 8, 4, tzinfo=UTC),
            "planned_settlement_at": datetime(2026, 8, 4, tzinfo=UTC),
        }
    )
    for entity in (evidence, experiment, watchlist, session, decision):
        storage.save(entity)
    lifecycle = ResearchLifecycleService(storage)
    plan = TradePlanService(lifecycle).create_from_decision(decision.decision_id)
    _advance_to_trade_plan_ready(lifecycle, session.research_session_id)
    adapter = StaticMarketDataAdapter(
        [_bar(date(2026, 8, 1), open_="10.00", high="12.50", low="9.40")]
    )
    execution = SimulatedExecutionService(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
    ).execute_trade_plan(plan.trade_plan_id)
    return storage, execution, adapter


def _advance_to_trade_plan_ready(
    lifecycle: ResearchLifecycleService,
    session_id: str,
) -> None:
    for state in (
        ResearchSessionStatus.EVIDENCE_READY,
        ResearchSessionStatus.HYPOTHESIS_READY,
        ResearchSessionStatus.SKILLS_RUNNING,
        ResearchSessionStatus.DISCUSSION_READY,
        ResearchSessionStatus.RISK_REVIEW,
        ResearchSessionStatus.DECISION_READY,
        ResearchSessionStatus.TRADE_PLAN_READY,
    ):
        lifecycle.transition(
            session_id,
            state,
            reason=f"test fixture {state.value}",
            allow_future_state=True,
        )


def _bar(trade_date: date, *, open_: str, high: str, low: str) -> MarketBar:
    return MarketBar(
        symbol="600519",
        market="CN_A",
        trade_date=trade_date,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(open_),
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        adjustment=Adjustment.NONE,
        source="akshare.stock_zh_a_hist",
        fetched_at=datetime(2026, 7, 1, tzinfo=UTC) + timedelta(hours=8),
    )
