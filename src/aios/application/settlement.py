from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from aios.adapters.market_data import Adjustment, MarketBar, MarketDataAdapter
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    DecisionDirection,
    DirectionalResult,
    EvaluationFinalResult,
    EvaluationScore,
    ExecutionExitReason,
    ExecutionStatus,
    LearningType,
    Outcome,
    OutcomeStatus,
    ResearchSessionStatus,
    ReturnResult,
    RiskResult,
)
from aios.kernel.execution import SimulatedExecution
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.kernel.trade_plan import TradePlan

EXECUTION_EVALUATION_V1 = "simulated-execution-evaluation-v1"


@dataclass(frozen=True)
class SettlementResult:
    outcome: DecisionOutcome
    evaluation: DecisionEvaluation
    review: Review
    learning_proposal: Learning


class SettlementService:
    def __init__(
        self,
        *,
        lifecycle: ResearchLifecycleService,
        market_data_adapter: MarketDataAdapter,
        adjustment: Adjustment = Adjustment.NONE,
    ) -> None:
        self._lifecycle = lifecycle
        self._storage = lifecycle.storage
        self._market_data_adapter = market_data_adapter
        self._adjustment = adjustment

    def settle_execution(self, execution_id: str) -> SettlementResult:
        existing = self._storage.get_settlement_outcome_by_execution_id(execution_id)
        if existing is not None:
            return self._existing_result(existing)

        execution = self._storage.get(SimulatedExecution, execution_id)
        plan = self._storage.get(TradePlan, execution.trade_plan_id)
        decision = self._storage.get(Decision, execution.decision_id)
        outcome = self._build_outcome(execution, plan, decision)
        self._storage.save(outcome)
        self._transition(
            execution.research_session_id,
            ResearchSessionStatus.SETTLED,
            "execution settled",
        )
        evaluation = self._build_evaluation(execution, outcome, decision)
        self._storage.save(evaluation)
        review = self._build_review(execution, outcome, evaluation, decision)
        self._storage.save(review)
        self._transition(
            execution.research_session_id,
            ResearchSessionStatus.REVIEWED,
            "execution reviewed",
        )
        learning = self._build_learning(review)
        self._storage.save(learning)
        self._transition(
            execution.research_session_id,
            ResearchSessionStatus.LEARNING_PROPOSED,
            "learning proposal generated",
        )
        self._transition(
            execution.research_session_id,
            ResearchSessionStatus.COMPLETED,
            "research lifecycle completed",
        )
        return SettlementResult(outcome, evaluation, review, learning)

    def _existing_result(self, outcome: DecisionOutcome) -> SettlementResult:
        evaluation = self._storage.get_decision_evaluation_by_decision_id(
            outcome.decision_id,
            EXECUTION_EVALUATION_V1,
        )
        if evaluation is None:
            msg = "settlement evaluation missing for existing execution outcome"
            raise ValueError(msg)
        review = self._storage.get_review_by_decision_id(outcome.decision_id)
        if review is None:
            msg = "review missing for existing execution outcome"
            raise ValueError(msg)
        learning = next(
            item
            for item in self._storage.list(Learning)
            if item.review_id == review.review_id
        )
        return SettlementResult(outcome, evaluation, review, learning)

    def _build_outcome(
        self,
        execution: SimulatedExecution,
        plan: TradePlan,
        decision: Decision,
    ) -> DecisionOutcome:
        now = datetime.now(plan.created_at.tzinfo)
        start = plan.created_at
        end = plan.expiry
        bars = self._bars(plan)
        entry = execution.executed_entry
        exit_price = execution.executed_exit
        realized = execution.realized_return
        if (
            execution.execution_status is ExecutionStatus.NOT_FILLED
            or entry is None
            or exit_price is None
            or realized is None
        ):
            entry = exit_price = None
            realized = None
            pnl = None
            holding_days = 0
            adverse = favorable = max_drawdown = None
            status = OutcomeStatus.INSUFFICIENT_DATA
        else:
            execution_date = execution.execution_date
            if execution_date is None:
                msg = "filled execution requires execution_date"
                raise ValueError(msg)
            window = [
                bar for bar in bars if execution_date <= bar.trade_date <= end.date()
            ]
            adverse, favorable = _excursions(execution.direction, entry, window)
            max_drawdown = _q(adverse - execution.fee - execution.slippage, "0.0001")
            favorable = _q(favorable - execution.fee - execution.slippage, "0.0001")
            pnl = _q(realized * execution.position_size, "0.000001")
            holding_days = (execution_date - execution_date).days
            status = OutcomeStatus.SETTLED
        return DecisionOutcome(
            decision_id=execution.decision_id,
            experiment_id=decision.experiment_id,
            symbol=execution.symbol,
            horizon=plan.horizon,
            horizon_semantics="trade_plan_expiry",
            observation_started_at=start,
            observation_ended_at=end,
            entry_price=entry,
            exit_price=exit_price,
            realized_return=realized,
            maximum_adverse_excursion=adverse,
            maximum_favorable_excursion=favorable,
            market_data_source=execution.market_data_source or "MarketDataAdapter",
            market_data_snapshot={
                "source": execution.market_data_source,
                "market_bar_id": execution.market_bar_id,
                "trade_dates": [bar.trade_date.isoformat() for bar in bars],
            },
            settled_at=now,
            status=status,
            execution_id=execution.execution_id,
            trade_plan_id=execution.trade_plan_id,
            research_session_id=execution.research_session_id,
            pnl=pnl,
            return_rate=realized,
            holding_days=holding_days,
            exit_reason=execution.exit_reason,
            max_drawdown=max_drawdown,
            created_at=now,
        )

    def _build_evaluation(
        self,
        execution: SimulatedExecution,
        outcome: DecisionOutcome,
        decision: Decision,
    ) -> DecisionEvaluation:
        prediction = _prediction_score(execution.direction, outcome.return_rate)
        timing = (
            EvaluationScore.GOOD
            if execution.execution_status is ExecutionStatus.WAITING_SETTLEMENT
            else EvaluationScore.POOR
        )
        risk = (
            EvaluationScore.GOOD
            if execution.exit_reason
            in {ExecutionExitReason.STOP, ExecutionExitReason.TARGET}
            else EvaluationScore.FAIR
        )
        quality = (
            EvaluationScore.GOOD
            if execution.market_data_source and execution.market_bar_id
            else EvaluationScore.POOR
        )
        final = (
            EvaluationFinalResult.PASS
            if prediction is EvaluationScore.GOOD and risk is EvaluationScore.GOOD
            else EvaluationFinalResult.FAIL
        )
        return DecisionEvaluation(
            decision_id=execution.decision_id,
            outcome_id=outcome.outcome_id,
            experiment_id=decision.experiment_id,
            directional_result=(
                DirectionalResult.CORRECT
                if prediction is EvaluationScore.GOOD
                else DirectionalResult.INCORRECT
            ),
            return_result=(
                ReturnResult.MET
                if outcome.return_rate is not None
                and decision.expected_return is not None
                and outcome.return_rate >= Decimal(str(decision.expected_return))
                else ReturnResult.MISSED
            ),
            risk_result=RiskResult.WITHIN_LIMIT,
            final_result=final,
            evaluation_rules_version=EXECUTION_EVALUATION_V1,
            evaluated_at=outcome.settled_at,
            explanation="fixed deterministic execution evaluation",
            prediction_accuracy=prediction,
            timing_accuracy=timing,
            risk_control=risk,
            execution_quality=quality,
            created_at=outcome.settled_at,
        )

    def _build_review(
        self,
        execution: SimulatedExecution,
        outcome: DecisionOutcome,
        evaluation: DecisionEvaluation,
        decision: Decision,
    ) -> Review:
        success = []
        failure = []
        if outcome.return_rate is not None and outcome.return_rate > 0:
            success.append("positive realized return")
        else:
            failure.append("negative or unavailable realized return")
        if execution.exit_reason is ExecutionExitReason.STOP:
            success.append("stop-loss rule limited loss")
            failure.append("target thesis failed before expiry")
        refs = {
            "evidence": list(decision.evidence_ids),
            "skill_result": list(decision.supporting_skill_ids),
            "discussion": (
                [decision.decision_result_id] if decision.decision_result_id else []
            ),
            "decision": [decision.decision_id],
            "risk_review": [decision.risk_review_id] if decision.risk_review_id else [],
            "trade_plan": [execution.trade_plan_id],
            "execution": [execution.execution_id],
            "settlement": [outcome.outcome_id],
            "evaluation": [evaluation.evaluation_id],
        }
        return Review(
            decision_id=decision.decision_id,
            actual_return=outcome.return_rate,
            direction_correct=(
                evaluation.directional_result is DirectionalResult.CORRECT
            ),
            risk_limit_breached=evaluation.risk_result is RiskResult.BREACHED,
            outcome=(
                Outcome.PROFIT
                if outcome.return_rate is not None and outcome.return_rate > 0
                else Outcome.LOSS
            ),
            cause_tags=("simulated_execution", execution.exit_reason.value),
            review_summary="deterministic simulated execution review",
            success_reasons=tuple(success),
            failure_reasons=tuple(failure),
            effective_evidence_ids=tuple(decision.evidence_ids),
            effective_skill_ids=tuple(decision.supporting_skill_ids),
            mistaken_judgement_ids=(decision.decision_id,)
            if evaluation.directional_result is DirectionalResult.INCORRECT
            else (),
            reference_ids=refs,
            created_at=evaluation.evaluated_at,
        )

    def _build_learning(self, review: Review) -> Learning:
        return Learning(
            review_id=review.review_id,
            learning_type=LearningType.SKILL_WEIGHT_UPDATE,
            target="simulated_execution_review",
            before={"status": "current"},
            after={"status": "proposal_only"},
            reason="proposal only; no Skill, Prompt, or Weight is modified",
            created_at=review.created_at,
        )

    def _transition(
        self,
        session_id: str,
        state: ResearchSessionStatus,
        reason: str,
    ) -> None:
        self._lifecycle.transition(
            session_id,
            state,
            reason=reason,
            allow_future_state=True,
        )

    def _bars(self, plan: TradePlan) -> list[MarketBar]:
        return sorted(
            self._market_data_adapter.fetch_daily_bars(
                plan.symbol,
                plan.created_at.date(),
                plan.expiry.date(),
                self._adjustment,
            ),
            key=lambda bar: bar.trade_date,
        )


def _prediction_score(
    direction: DecisionDirection,
    return_rate: Decimal | None,
) -> EvaluationScore:
    if return_rate is None:
        return EvaluationScore.POOR
    if direction is DecisionDirection.BULLISH:
        return EvaluationScore.GOOD if return_rate > 0 else EvaluationScore.POOR
    if direction is DecisionDirection.BEARISH:
        return EvaluationScore.GOOD if return_rate > 0 else EvaluationScore.POOR
    return EvaluationScore.FAIR


def _excursions(
    direction: DecisionDirection,
    entry: Decimal,
    bars: list[MarketBar],
) -> tuple[Decimal, Decimal]:
    values: list[Decimal] = []
    for bar in bars:
        if direction is DecisionDirection.BEARISH:
            values.extend(((entry - bar.high) / entry, (entry - bar.low) / entry))
        else:
            values.extend(((bar.low - entry) / entry, (bar.high - entry) / entry))
    if not values:
        return Decimal("0"), Decimal("0")
    return min(values), max(values)


def _q(value: Decimal, unit: str) -> Decimal:
    return value.quantize(Decimal(unit), rounding=ROUND_HALF_UP)
