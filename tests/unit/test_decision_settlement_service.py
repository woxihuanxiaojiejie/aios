from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from aios.adapters.market_data import Adjustment, MarketBar
from aios.adapters.market_errors import UpstreamMarketDataError
from aios.application.decision_settlement import (
    DECISION_EVALUATION_V1,
    DecisionSettlementService,
)
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
    ExperimentNotFoundError,
    InsufficientMarketDataError,
)
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService

CREATED_AT = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)


class DeterministicMarketDataAdapter:
    def __init__(
        self,
        bars: list[MarketBar],
        error: Exception | None = None,
    ) -> None:
        self.bars = bars
        self.error = error
        self.calls: list[dict[str, object]] = []

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        self.calls.append(
            {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "adjustment": adjustment,
            }
        )
        if self.error is not None:
            raise self.error
        return [
            bar
            for bar in self.bars
            if bar.symbol == symbol and start_date <= bar.trade_date <= end_date
        ]


class ForbiddenLLM:
    def generate_structured(self, **_kwargs: object) -> object:
        raise AssertionError("settlement must not call an LLM")


def market_bar(
    trade_date: date,
    close: str,
    *,
    open_price: str | None = None,
    high: str | None = None,
    low: str | None = None,
    symbol: str = "000001.SZ",
) -> MarketBar:
    close_decimal = Decimal(close)
    open_decimal = Decimal(open_price or close)
    high_decimal = Decimal(high or str(max(open_decimal, close_decimal)))
    low_decimal = Decimal(low or str(min(open_decimal, close_decimal)))
    return MarketBar(
        symbol=symbol,
        market="CN_A",
        trade_date=trade_date,
        open=open_decimal,
        high=high_decimal,
        low=low_decimal,
        close=close_decimal,
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        adjustment=Adjustment.NONE,
        source="deterministic-test",
        fetched_at=datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
    )


def seed_lifecycle(
    *,
    action: Action = Action.BUY,
    horizon: str = "1d",
    expected_return: float = 0.02,
    max_expected_loss: float = 0.05,
    decision_status: DecisionStatus = DecisionStatus.PROPOSED,
) -> tuple[DecisionLifecycleService, Decision]:
    storage = InMemoryStorage()
    lifecycle = DecisionLifecycleService(storage)
    evidence = lifecycle.register_evidence(
        Evidence(
            evidence_id="ev_00000000-0000-0000-0000-000000000001",
            evidence_type="market_data",
            source="deterministic-test",
            symbols=["000001.SZ"],
            published_at=CREATED_AT - timedelta(days=1),
            available_at=CREATED_AT - timedelta(days=1),
            summary="historical bar",
            reliability=0.9,
            content_hash="hash-market-bar",
            created_at=CREATED_AT - timedelta(days=1),
        )
    )
    experiment = lifecycle.start_experiment(
        Experiment(
            experiment_id="ex_00000000-0000-0000-0000-000000000001",
            name="settlement-test",
            model="model-v1",
            prompt_version="decision-v1",
            agent_config_version="agent-v1",
            dataset_snapshot="snapshot-v1",
            evidence_ids=[evidence.evidence_id],
            parameters={"temperature": 0},
            started_at=CREATED_AT - timedelta(minutes=10),
            finished_at=CREATED_AT - timedelta(minutes=1),
            created_at=CREATED_AT - timedelta(minutes=10),
        )
    )
    decision = lifecycle.create_decision(
        Decision(
            decision_id="dc_00000000-0000-0000-0000-000000000001",
            experiment_id=experiment.experiment_id,
            symbol="000001.SZ",
            action=action,
            horizon=horizon,
            confidence=0.7,
            expected_return=expected_return,
            max_expected_loss=max_expected_loss,
            evidence_ids=[evidence.evidence_id],
            reasoning_summary="deterministic settlement test",
            status=decision_status,
            created_at=CREATED_AT,
            valid_until=CREATED_AT + _horizon_delta(horizon),
        )
    )
    return lifecycle, decision


def _horizon_delta(horizon: str) -> timedelta:
    return timedelta(days=int(horizon.removesuffix("d")))


def settle(
    *,
    action: Action,
    bars: list[MarketBar],
    horizon: str = "1d",
    expected_return: float = 0.02,
    max_expected_loss: float = 0.05,
    as_of: datetime = datetime(2026, 7, 20, tzinfo=UTC),
) -> tuple[DecisionOutcome, DecisionEvaluation, DeterministicMarketDataAdapter]:
    lifecycle, decision = seed_lifecycle(
        action=action,
        horizon=horizon,
        expected_return=expected_return,
        max_expected_loss=max_expected_loss,
    )
    adapter = DeterministicMarketDataAdapter(bars)
    result = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
    ).settle(decision_id=decision.decision_id, as_of=as_of)
    return result.outcome, result.evaluation, adapter


def test_bullish_direction_correct_and_return_passes() -> None:
    outcome, evaluation, _adapter = settle(
        action=Action.BUY,
        bars=[
            market_bar(date(2026, 7, 1), "10.00", high="10.20", low="9.90"),
            market_bar(date(2026, 7, 2), "10.50", high="10.60", low="10.10"),
        ],
        expected_return=0.04,
    )

    assert outcome.status is OutcomeStatus.SETTLED
    assert outcome.horizon_semantics == "natural_time"
    assert outcome.entry_price == Decimal("10.00")
    assert outcome.exit_price == Decimal("10.50")
    assert outcome.realized_return == Decimal("0.05")
    assert evaluation.directional_result is DirectionalResult.CORRECT
    assert evaluation.return_result is ReturnResult.MET
    assert evaluation.risk_result is RiskResult.WITHIN_LIMIT
    assert evaluation.final_result is EvaluationFinalResult.PASS


def test_bullish_direction_incorrect_fails() -> None:
    _outcome, evaluation, _adapter = settle(
        action=Action.BUY,
        bars=[
            market_bar(date(2026, 7, 1), "10.00"),
            market_bar(date(2026, 7, 2), "9.70", high="10.10", low="9.60"),
        ],
        expected_return=0.01,
    )

    assert evaluation.directional_result is DirectionalResult.INCORRECT
    assert evaluation.return_result is ReturnResult.MISSED
    assert evaluation.final_result is EvaluationFinalResult.FAIL


def test_bearish_direction_correct() -> None:
    outcome, evaluation, _adapter = settle(
        action=Action.SELL,
        bars=[
            market_bar(date(2026, 7, 1), "10.00"),
            market_bar(date(2026, 7, 2), "9.50", high="10.10", low="9.40"),
        ],
        expected_return=-0.04,
    )

    assert outcome.realized_return == Decimal("-0.05")
    assert evaluation.directional_result is DirectionalResult.CORRECT
    assert evaluation.return_result is ReturnResult.MET
    assert evaluation.final_result is EvaluationFinalResult.PASS


def test_bearish_direction_incorrect() -> None:
    _outcome, evaluation, _adapter = settle(
        action=Action.SELL,
        bars=[
            market_bar(date(2026, 7, 1), "10.00"),
            market_bar(date(2026, 7, 2), "10.40"),
        ],
        expected_return=-0.01,
    )

    assert evaluation.directional_result is DirectionalResult.INCORRECT
    assert evaluation.return_result is ReturnResult.MISSED
    assert evaluation.final_result is EvaluationFinalResult.FAIL


@pytest.mark.parametrize("action", [Action.HOLD, Action.OBSERVE, Action.NO_TRADE])
def test_neutral_or_abstain_actions_are_not_directionally_scored(
    action: Action,
) -> None:
    _outcome, evaluation, _adapter = settle(
        action=action,
        bars=[
            market_bar(date(2026, 7, 1), "10.00"),
            market_bar(date(2026, 7, 2), "10.20"),
        ],
        expected_return=0,
    )

    assert evaluation.directional_result is DirectionalResult.NEUTRAL
    assert evaluation.return_result is ReturnResult.NOT_APPLICABLE
    assert evaluation.final_result is EvaluationFinalResult.INCONCLUSIVE


@pytest.mark.parametrize(
    ("horizon", "exit_date"),
    [
        ("1d", date(2026, 7, 2)),
        ("3d", date(2026, 7, 4)),
        ("7d", date(2026, 7, 8)),
    ],
)
def test_supported_natural_time_horizons_select_exit_on_or_after_expiry(
    horizon: str,
    exit_date: date,
) -> None:
    outcome, _evaluation, adapter = settle(
        action=Action.BUY,
        horizon=horizon,
        bars=[
            market_bar(date(2026, 7, 1), "10.00"),
            market_bar(exit_date, "10.30"),
        ],
    )

    assert outcome.observation_ended_at == CREATED_AT + _horizon_delta(horizon)
    assert outcome.market_data_snapshot["exit_trade_date"] == exit_date.isoformat()
    assert adapter.calls[0]["start_date"] == date(2026, 7, 1)


def test_non_trading_day_expiry_uses_first_later_valid_market_observation() -> None:
    outcome, _evaluation, _adapter = settle(
        action=Action.BUY,
        horizon="3d",
        bars=[
            market_bar(date(2026, 7, 1), "10.00"),
            market_bar(date(2026, 7, 6), "10.30"),
        ],
    )

    assert outcome.observation_ended_at == datetime(2026, 7, 4, 9, 30, tzinfo=UTC)
    assert outcome.market_data_snapshot["exit_trade_date"] == "2026-07-06"
    assert outcome.exit_price == Decimal("10.30")


def test_insufficient_market_data_saves_inconclusive_outcome_and_evaluation() -> None:
    outcome, evaluation, _adapter = settle(
        action=Action.BUY,
        bars=[market_bar(date(2026, 7, 1), "10.00")],
    )

    assert outcome.status is OutcomeStatus.INSUFFICIENT_DATA
    assert outcome.entry_price is None
    assert outcome.exit_price is None
    assert evaluation.final_result is EvaluationFinalResult.INCONCLUSIVE
    assert "insufficient market data" in evaluation.explanation


def test_invalid_entry_price_saves_insufficient_data_outcome() -> None:
    outcome, evaluation, _adapter = settle(
        action=Action.BUY,
        bars=[
            market_bar(date(2026, 7, 1), "0"),
            market_bar(date(2026, 7, 2), "10.00"),
        ],
    )

    assert outcome.status is OutcomeStatus.INSUFFICIENT_DATA
    assert evaluation.final_result is EvaluationFinalResult.INCONCLUSIVE


def test_repeat_settlement_is_idempotent_for_outcome_and_evaluation() -> None:
    lifecycle, decision = seed_lifecycle(action=Action.BUY)
    adapter = DeterministicMarketDataAdapter(
        [
            market_bar(date(2026, 7, 1), "10.00"),
            market_bar(date(2026, 7, 2), "10.40"),
        ]
    )
    service = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
    )

    first = service.settle(decision_id=decision.decision_id)
    second = service.settle(decision_id=decision.decision_id)

    assert first.outcome == second.outcome
    assert first.evaluation == second.evaluation
    assert len(lifecycle.list_entities(DecisionOutcome)) == 1
    assert len(lifecycle.list_entities(DecisionEvaluation)) == 1
    assert len(adapter.calls) == 1


def test_missing_decision_raises_domain_error() -> None:
    lifecycle, _decision = seed_lifecycle(action=Action.BUY)
    service = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=DeterministicMarketDataAdapter([]),
    )

    with pytest.raises(DecisionNotFoundError):
        service.settle(decision_id="dc_missing")


def test_missing_experiment_raises_domain_error() -> None:
    storage = InMemoryStorage()
    lifecycle = DecisionLifecycleService(storage)
    decision = Decision(
        decision_id="dc_00000000-0000-0000-0000-000000000999",
        experiment_id="ex_missing",
        symbol="000001.SZ",
        action=Action.BUY,
        horizon="1d",
        confidence=0.7,
        expected_return=0.01,
        max_expected_loss=0.02,
        evidence_ids=["ev_missing"],
        reasoning_summary="orphan decision for test",
        created_at=CREATED_AT,
        valid_until=CREATED_AT + timedelta(days=1),
    )
    storage.save(decision)
    service = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=DeterministicMarketDataAdapter([]),
    )

    with pytest.raises(ExperimentNotFoundError):
        service.settle(decision_id=decision.decision_id)


def test_max_expected_loss_not_triggered() -> None:
    _outcome, evaluation, _adapter = settle(
        action=Action.BUY,
        bars=[
            market_bar(date(2026, 7, 1), "10.00", low="9.90"),
            market_bar(date(2026, 7, 2), "10.30", low="9.80"),
        ],
        max_expected_loss=0.03,
    )

    assert evaluation.risk_result is RiskResult.WITHIN_LIMIT
    assert evaluation.final_result is EvaluationFinalResult.PASS


def test_max_expected_loss_triggered_fails() -> None:
    outcome, evaluation, _adapter = settle(
        action=Action.BUY,
        bars=[
            market_bar(date(2026, 7, 1), "10.00", low="9.40"),
            market_bar(date(2026, 7, 2), "10.30", low="9.60"),
        ],
        max_expected_loss=0.05,
    )

    assert outcome.maximum_adverse_excursion == Decimal("-0.06")
    assert evaluation.risk_result is RiskResult.BREACHED
    assert evaluation.final_result is EvaluationFinalResult.FAIL


def test_storage_can_query_outcome_and_evaluation_by_decision_id() -> None:
    lifecycle, decision = seed_lifecycle(action=Action.BUY)
    result = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=DeterministicMarketDataAdapter(
            [
                market_bar(date(2026, 7, 1), "10.00"),
                market_bar(date(2026, 7, 2), "10.30"),
            ]
        ),
    ).settle(decision_id=decision.decision_id)

    assert lifecycle.get_decision_outcome(decision.decision_id) == result.outcome
    assert (
        lifecycle.get_decision_evaluation(
            decision.decision_id,
            DECISION_EVALUATION_V1,
        )
        == result.evaluation
    )


def test_outcome_and_evaluation_serialization_is_stable() -> None:
    outcome, evaluation, _adapter = settle(
        action=Action.BUY,
        bars=[
            market_bar(date(2026, 7, 1), "10.00"),
            market_bar(date(2026, 7, 2), "10.50"),
        ],
    )

    outcome_dump = outcome.model_dump(mode="json")
    evaluation_dump = evaluation.model_dump(mode="json")

    assert outcome_dump["realized_return"] == "0.05"
    assert outcome_dump["status"] == "settled"
    assert evaluation_dump["final_result"] == "pass"
    assert evaluation_dump["evaluation_rules_version"] == DECISION_EVALUATION_V1


def test_settlement_does_not_call_llm_for_evaluation() -> None:
    lifecycle, decision = seed_lifecycle(action=Action.BUY)
    service = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=DeterministicMarketDataAdapter(
            [
                market_bar(date(2026, 7, 1), "10.00"),
                market_bar(date(2026, 7, 2), "10.20"),
            ]
        ),
        llm_adapter=ForbiddenLLM(),
    )

    result = service.settle(decision_id=decision.decision_id)

    assert result.evaluation.evaluation_rules_version == DECISION_EVALUATION_V1


def test_external_market_data_errors_are_mapped_to_aios_error() -> None:
    lifecycle, decision = seed_lifecycle(action=Action.BUY)
    service = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=DeterministicMarketDataAdapter(
            [],
            error=UpstreamMarketDataError("provider secret details"),
        ),
    )

    with pytest.raises(InsufficientMarketDataError, match="market data unavailable"):
        service.settle(decision_id=decision.decision_id)


def test_decision_not_ready_for_settlement_is_rejected() -> None:
    lifecycle, decision = seed_lifecycle(action=Action.BUY)
    service = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=DeterministicMarketDataAdapter([]),
    )

    with pytest.raises(DecisionNotReadyForSettlementError):
        service.settle(
            decision_id=decision.decision_id,
            as_of=decision.valid_until - timedelta(seconds=1),
        )


def test_invalidated_decision_saves_invalidated_outcome_and_evaluation() -> None:
    lifecycle, decision = seed_lifecycle(
        action=Action.BUY,
        decision_status=DecisionStatus.INVALID,
    )
    service = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=DeterministicMarketDataAdapter([]),
    )

    result = service.settle(decision_id=decision.decision_id)

    assert result.outcome.status is OutcomeStatus.INVALIDATED
    assert result.evaluation.final_result is EvaluationFinalResult.INVALID
