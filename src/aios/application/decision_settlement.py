from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from aios.adapters.market_data import Adjustment, MarketBar, MarketDataAdapter
from aios.adapters.market_errors import MarketDataError
from aios.kernel.base import utc_now
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    DecisionStatus,
    DirectionalResult,
    EvaluationFinalResult,
    OutcomeStatus,
    ReturnResult,
    RiskResult,
)
from aios.kernel.errors import (
    DecisionNotFoundError,
    DecisionNotReadyForSettlementError,
    EvaluationConfigurationError,
    ExperimentNotFoundError,
    InsufficientMarketDataError,
    MissingEntityError,
)
from aios.kernel.experiment import Experiment
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.workflows.decision_lifecycle import DecisionLifecycleService

DECISION_EVALUATION_V1 = "decision-evaluation-v1"
HORIZON_SEMANTICS = "natural_time"
SUPPORTED_HORIZONS = {
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
}
POST_HORIZON_OBSERVATION_GRACE = timedelta(days=7)
NEUTRAL_ACTIONS = {Action.HOLD, Action.OBSERVE, Action.NO_TRADE}


@dataclass(frozen=True)
class DecisionSettlementResult:
    outcome: DecisionOutcome
    evaluation: DecisionEvaluation


class DecisionSettlementService:
    def __init__(
        self,
        *,
        lifecycle: DecisionLifecycleService,
        market_data_adapter: MarketDataAdapter,
        adjustment: Adjustment = Adjustment.NONE,
        evaluation_rules_version: str = DECISION_EVALUATION_V1,
        llm_adapter: object | None = None,
    ) -> None:
        if not evaluation_rules_version:
            msg = "evaluation_rules_version must not be empty"
            raise EvaluationConfigurationError(msg)
        self._lifecycle = lifecycle
        self._market_data_adapter = market_data_adapter
        self._adjustment = adjustment
        self._evaluation_rules_version = evaluation_rules_version
        self._llm_adapter = llm_adapter

    def settle(
        self,
        *,
        decision_id: str,
        as_of: datetime | None = None,
    ) -> DecisionSettlementResult:
        existing = self._existing_result(decision_id)
        if existing is not None:
            return existing

        decision = self._decision(decision_id)
        self._experiment(decision.experiment_id)
        now = self._as_utc(as_of or utc_now())
        self._ensure_supported_horizon(decision.horizon)
        if now < decision.valid_until:
            msg = f"Decision {decision_id} is not ready for settlement"
            raise DecisionNotReadyForSettlementError(msg)

        if decision.status is DecisionStatus.INVALID:
            outcome = self._invalidated_outcome(decision, settled_at=now)
        else:
            outcome = self._settle_with_market_data(decision, settled_at=now)

        saved_outcome = self._lifecycle.settle_decision(outcome)
        evaluation = self._evaluate(decision, saved_outcome, evaluated_at=now)
        saved_evaluation = self._lifecycle.evaluate_decision(evaluation)
        return DecisionSettlementResult(
            outcome=saved_outcome,
            evaluation=saved_evaluation,
        )

    def _existing_result(self, decision_id: str) -> DecisionSettlementResult | None:
        outcome = self._lifecycle.get_decision_outcome(decision_id)
        evaluation = self._lifecycle.get_decision_evaluation(
            decision_id,
            self._evaluation_rules_version,
        )
        if outcome is None or evaluation is None:
            return None
        return DecisionSettlementResult(outcome=outcome, evaluation=evaluation)

    def _decision(self, decision_id: str) -> Decision:
        try:
            return self._lifecycle.get_entity(Decision, decision_id)
        except MissingEntityError as exc:
            msg = f"Decision {decision_id} does not exist"
            raise DecisionNotFoundError(msg) from exc

    def _experiment(self, experiment_id: str) -> Experiment:
        try:
            return self._lifecycle.get_entity(Experiment, experiment_id)
        except MissingEntityError as exc:
            msg = f"Experiment {experiment_id} does not exist"
            raise ExperimentNotFoundError(msg) from exc

    def _ensure_supported_horizon(self, horizon: str) -> None:
        if horizon not in SUPPORTED_HORIZONS:
            msg = "settlement supports only 1d, 3d, and 7d horizons"
            raise EvaluationConfigurationError(msg)

    def _settle_with_market_data(
        self,
        decision: Decision,
        *,
        settled_at: datetime,
    ) -> DecisionOutcome:
        start_at = decision.created_at
        end_at = decision.valid_until
        fetch_end_date = (end_at + POST_HORIZON_OBSERVATION_GRACE).date()
        try:
            bars = self._market_data_adapter.fetch_daily_bars(
                decision.symbol,
                start_at.date(),
                fetch_end_date,
                self._adjustment,
            )
        except MarketDataError:
            msg = "market data unavailable for settlement"
            raise InsufficientMarketDataError(msg) from None
        except Exception:
            msg = "market data unavailable for settlement"
            raise InsufficientMarketDataError(msg) from None

        ordered = sorted(bars, key=lambda bar: bar.trade_date)
        insufficient_reason = self._insufficient_reason(ordered, start_at, end_at)
        if insufficient_reason is not None:
            return self._insufficient_outcome(
                decision,
                settled_at=settled_at,
                reason=insufficient_reason,
                bar_count=len(ordered),
            )

        entry_bar = self._entry_bar(ordered, start_at, end_at)
        exit_bar = self._exit_bar(ordered, end_at)
        if entry_bar is None or exit_bar is None:
            return self._insufficient_outcome(
                decision,
                settled_at=settled_at,
                reason="insufficient market data",
                bar_count=len(ordered),
            )

        window = [
            bar
            for bar in ordered
            if entry_bar.trade_date <= bar.trade_date <= exit_bar.trade_date
        ]
        realized_return = _return(exit_bar.close, entry_bar.close)
        adverse, favorable = self._excursions(decision.action, entry_bar, window)
        return DecisionOutcome(
            decision_id=decision.decision_id,
            experiment_id=decision.experiment_id,
            symbol=decision.symbol,
            horizon=decision.horizon,
            horizon_semantics=HORIZON_SEMANTICS,
            observation_started_at=start_at,
            observation_ended_at=end_at,
            entry_price=entry_bar.close,
            exit_price=exit_bar.close,
            realized_return=realized_return,
            maximum_adverse_excursion=adverse,
            maximum_favorable_excursion=favorable,
            market_data_source=entry_bar.source,
            market_data_snapshot={
                "adjustment": self._adjustment.value,
                "bar_count": len(ordered),
                "entry_trade_date": entry_bar.trade_date.isoformat(),
                "exit_trade_date": exit_bar.trade_date.isoformat(),
                "fetch_start_date": start_at.date().isoformat(),
                "fetch_end_date": fetch_end_date.isoformat(),
                "source": entry_bar.source,
                "trade_dates": [bar.trade_date.isoformat() for bar in window],
            },
            settled_at=settled_at,
            status=OutcomeStatus.SETTLED,
            created_at=settled_at,
        )

    def _insufficient_reason(
        self,
        bars: list[MarketBar],
        start_at: datetime,
        end_at: datetime,
    ) -> str | None:
        if not bars:
            return "insufficient market data: no bars returned"
        if any(not _valid_bar_price(bar) for bar in bars):
            return "insufficient market data: invalid price"
        if self._entry_bar(bars, start_at, end_at) is None:
            return "insufficient market data: no entry observation"
        if self._exit_bar(bars, end_at) is None:
            return "insufficient market data: no exit observation"
        return None

    def _entry_bar(
        self,
        bars: list[MarketBar],
        start_at: datetime,
        end_at: datetime,
    ) -> MarketBar | None:
        for bar in bars:
            if start_at.date() <= bar.trade_date <= end_at.date():
                return bar
        return None

    def _exit_bar(self, bars: list[MarketBar], end_at: datetime) -> MarketBar | None:
        for bar in bars:
            if bar.trade_date >= end_at.date():
                return bar
        return None

    def _excursions(
        self,
        action: Action,
        entry_bar: MarketBar,
        bars: list[MarketBar],
    ) -> tuple[Decimal, Decimal]:
        if action in NEUTRAL_ACTIONS:
            return Decimal("0"), Decimal("0")
        returns: list[Decimal] = []
        for bar in bars:
            if action is Action.SELL:
                returns.append(_return(entry_bar.close, bar.high))
                returns.append(_return(entry_bar.close, bar.low))
            else:
                returns.append(_return(bar.high, entry_bar.close))
                returns.append(_return(bar.low, entry_bar.close))
        return min(returns), max(returns)

    def _insufficient_outcome(
        self,
        decision: Decision,
        *,
        settled_at: datetime,
        reason: str,
        bar_count: int,
    ) -> DecisionOutcome:
        return DecisionOutcome(
            decision_id=decision.decision_id,
            experiment_id=decision.experiment_id,
            symbol=decision.symbol,
            horizon=decision.horizon,
            horizon_semantics=HORIZON_SEMANTICS,
            observation_started_at=decision.created_at,
            observation_ended_at=decision.valid_until,
            market_data_source="unavailable",
            market_data_snapshot={"bar_count": bar_count, "reason": reason},
            settled_at=settled_at,
            status=OutcomeStatus.INSUFFICIENT_DATA,
            created_at=settled_at,
        )

    def _invalidated_outcome(
        self,
        decision: Decision,
        *,
        settled_at: datetime,
    ) -> DecisionOutcome:
        return DecisionOutcome(
            decision_id=decision.decision_id,
            experiment_id=decision.experiment_id,
            symbol=decision.symbol,
            horizon=decision.horizon,
            horizon_semantics=HORIZON_SEMANTICS,
            observation_started_at=decision.created_at,
            observation_ended_at=decision.valid_until,
            market_data_source="not_requested",
            market_data_snapshot={"reason": "decision invalidated before settlement"},
            settled_at=settled_at,
            status=OutcomeStatus.INVALIDATED,
            created_at=settled_at,
        )

    def _evaluate(
        self,
        decision: Decision,
        outcome: DecisionOutcome,
        *,
        evaluated_at: datetime,
    ) -> DecisionEvaluation:
        if outcome.status is OutcomeStatus.INVALIDATED:
            return self._evaluation(
                decision,
                outcome,
                DirectionalResult.NOT_APPLICABLE,
                ReturnResult.NOT_APPLICABLE,
                RiskResult.NOT_APPLICABLE,
                EvaluationFinalResult.INVALID,
                "decision invalidated before settlement",
                evaluated_at,
            )
        if outcome.status is OutcomeStatus.INSUFFICIENT_DATA:
            reason = str(outcome.market_data_snapshot.get("reason", "unknown"))
            return self._evaluation(
                decision,
                outcome,
                DirectionalResult.NOT_APPLICABLE,
                ReturnResult.NOT_APPLICABLE,
                RiskResult.NOT_APPLICABLE,
                EvaluationFinalResult.INCONCLUSIVE,
                reason,
                evaluated_at,
            )
        if outcome.realized_return is None:
            msg = "settled outcome missing realized_return"
            raise EvaluationConfigurationError(msg)
        if decision.action in NEUTRAL_ACTIONS:
            return self._evaluation(
                decision,
                outcome,
                DirectionalResult.NEUTRAL,
                ReturnResult.NOT_APPLICABLE,
                RiskResult.NOT_APPLICABLE,
                EvaluationFinalResult.INCONCLUSIVE,
                "neutral or abstain action is not directionally scored",
                evaluated_at,
            )

        directional_result = self._directional_result(decision, outcome)
        return_result = self._return_result(decision, outcome)
        risk_result = self._risk_result(decision, outcome)
        final_result = (
            EvaluationFinalResult.PASS
            if (
                directional_result is DirectionalResult.CORRECT
                and return_result is ReturnResult.MET
                and risk_result is RiskResult.WITHIN_LIMIT
            )
            else EvaluationFinalResult.FAIL
        )
        explanation = (
            "deterministic v1: direction, expected return, and max expected loss "
            "evaluated from settled market bars"
        )
        return self._evaluation(
            decision,
            outcome,
            directional_result,
            return_result,
            risk_result,
            final_result,
            explanation,
            evaluated_at,
        )

    def _directional_result(
        self,
        decision: Decision,
        outcome: DecisionOutcome,
    ) -> DirectionalResult:
        realized = _required_decimal(outcome.realized_return, "realized_return")
        if realized == 0:
            return DirectionalResult.NEUTRAL
        if decision.action is Action.SELL:
            return (
                DirectionalResult.CORRECT
                if realized < 0
                else DirectionalResult.INCORRECT
            )
        return (
            DirectionalResult.CORRECT if realized > 0 else DirectionalResult.INCORRECT
        )

    def _return_result(
        self,
        decision: Decision,
        outcome: DecisionOutcome,
    ) -> ReturnResult:
        realized = _required_decimal(outcome.realized_return, "realized_return")
        expected = Decimal(str(decision.expected_return))
        if decision.action is Action.SELL and expected >= 0:
            directional_return = -realized
            if directional_return >= expected:
                return ReturnResult.MET
            return ReturnResult.MISSED
        if expected >= 0:
            return ReturnResult.MET if realized >= expected else ReturnResult.MISSED
        return ReturnResult.MET if realized <= expected else ReturnResult.MISSED

    def _risk_result(self, decision: Decision, outcome: DecisionOutcome) -> RiskResult:
        adverse = _required_decimal(
            outcome.maximum_adverse_excursion,
            "maximum_adverse_excursion",
        )
        max_loss = Decimal(str(decision.max_expected_loss))
        if max_loss < 0:
            msg = "max_expected_loss must not be negative"
            raise EvaluationConfigurationError(msg)
        return RiskResult.BREACHED if adverse < -max_loss else RiskResult.WITHIN_LIMIT

    def _evaluation(
        self,
        decision: Decision,
        outcome: DecisionOutcome,
        directional_result: DirectionalResult,
        return_result: ReturnResult,
        risk_result: RiskResult,
        final_result: EvaluationFinalResult,
        explanation: str,
        evaluated_at: datetime,
    ) -> DecisionEvaluation:
        return DecisionEvaluation(
            decision_id=decision.decision_id,
            outcome_id=outcome.outcome_id,
            experiment_id=decision.experiment_id,
            directional_result=directional_result,
            return_result=return_result,
            risk_result=risk_result,
            final_result=final_result,
            evaluation_rules_version=self._evaluation_rules_version,
            evaluated_at=evaluated_at,
            explanation=explanation,
            created_at=evaluated_at,
        )

    def _as_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "as_of must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)


def _return(price: Decimal, entry_price: Decimal) -> Decimal:
    if entry_price <= 0:
        msg = "entry_price must be positive"
        raise ValueError(msg)
    return (price - entry_price) / entry_price


def _valid_bar_price(bar: MarketBar) -> bool:
    return bar.open > 0 and bar.high > 0 and bar.low > 0 and bar.close > 0


def _required_decimal(value: Decimal | None, field_name: str) -> Decimal:
    if value is None:
        msg = f"{field_name} is required"
        raise EvaluationConfigurationError(msg)
    return value
