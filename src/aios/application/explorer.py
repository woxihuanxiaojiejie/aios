from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from aios.adapters.storage import Storage
from aios.kernel.base import KernelModel
from aios.kernel.decision import Decision
from aios.kernel.errors import MissingEntityError
from aios.kernel.execution import SimulatedExecution
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchSession
from aios.kernel.research_run import ResearchRun
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.kernel.trade_plan import TradePlan

SortName = Literal[
    "created_at",
    "symbol",
    "status",
    "settled_at",
]


@dataclass(frozen=True)
class ExplorerPage[T]:
    items: tuple[T, ...]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class ExecutionListItem:
    execution: SimulatedExecution
    market: str | None
    research_run_id: str | None
    settlement_id: str | None


@dataclass(frozen=True)
class SettlementListItem:
    settlement: DecisionOutcome
    market: str | None
    research_run_id: str | None


@dataclass(frozen=True)
class ExplorerDetail:
    research_run: ResearchRun | None
    research_session: ResearchSession | None
    decision: Decision | None
    trade_plan: TradePlan | None
    simulated_execution: SimulatedExecution | None
    settlement: DecisionOutcome | None
    evaluation: DecisionEvaluation | None
    review: Review | None
    learning_proposals: tuple[Learning, ...]


class ExecutionSettlementExplorer:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def list_executions(
        self,
        *,
        page: int,
        page_size: int,
        symbol: str | None = None,
        market: str | None = None,
        status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: str = "-created_at",
    ) -> ExplorerPage[ExecutionListItem]:
        context = self._context()
        rows = [
            ExecutionListItem(
                execution=execution,
                market=context.market_by_session_id.get(execution.research_session_id),
                research_run_id=context.run_id_by_session_id.get(
                    execution.research_session_id
                ),
                settlement_id=_outcome_id(
                    context.outcome_by_execution_id.get(execution.execution_id)
                ),
            )
            for execution in self._storage.list(SimulatedExecution)
        ]
        rows = [
            row
            for row in rows
            if _matches_execution(
                row,
                symbol=symbol,
                market=market,
                status=status,
                created_from=created_from,
                created_to=created_to,
            )
        ]
        rows = _sort_execution_rows(rows, sort)
        return _page(rows, page, page_size)

    def execution_detail(self, execution_id: str) -> ExplorerDetail:
        execution = self._storage.get(SimulatedExecution, execution_id)
        return self._detail_from_execution(execution)

    def list_settlements(
        self,
        *,
        page: int,
        page_size: int,
        symbol: str | None = None,
        market: str | None = None,
        status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: str = "-settled_at",
    ) -> ExplorerPage[SettlementListItem]:
        context = self._context()
        rows = [
            SettlementListItem(
                settlement=outcome,
                market=context.market_by_session_id.get(outcome.research_session_id)
                if outcome.research_session_id
                else None,
                research_run_id=context.run_id_by_session_id.get(
                    outcome.research_session_id
                )
                if outcome.research_session_id
                else None,
            )
            for outcome in self._storage.list(DecisionOutcome)
            if outcome.execution_id is not None
        ]
        rows = [
            row
            for row in rows
            if _matches_settlement(
                row,
                symbol=symbol,
                market=market,
                status=status,
                created_from=created_from,
                created_to=created_to,
            )
        ]
        rows = _sort_settlement_rows(rows, sort)
        return _page(rows, page, page_size)

    def settlement_detail(self, settlement_id: str) -> ExplorerDetail:
        outcome = self._storage.get(DecisionOutcome, settlement_id)
        return self._detail_from_outcome(outcome)

    def research_run_detail(self, run_id: str) -> ExplorerDetail:
        run = self._storage.get(ResearchRun, run_id)
        if run.research_session_id is None:
            return ExplorerDetail(
                research_run=run,
                research_session=None,
                decision=None,
                trade_plan=None,
                simulated_execution=None,
                settlement=None,
                evaluation=None,
                review=None,
                learning_proposals=(),
            )
        session = _optional_get(self._storage, ResearchSession, run.research_session_id)
        decision = _decision_by_session_id(self._storage, run.research_session_id)
        return self._detail_from_known(
            research_run=run,
            research_session=session,
            decision=decision,
        )

    def _detail_from_execution(
        self,
        execution: SimulatedExecution,
    ) -> ExplorerDetail:
        decision = _optional_get(self._storage, Decision, execution.decision_id)
        session = _optional_get(
            self._storage,
            ResearchSession,
            execution.research_session_id,
        )
        run = _run_by_session_id(self._storage, execution.research_session_id)
        plan = _optional_get(self._storage, TradePlan, execution.trade_plan_id)
        settlement = self._storage.get_settlement_outcome_by_execution_id(
            execution.execution_id
        )
        return self._detail_from_known(
            research_run=run,
            research_session=session,
            decision=decision,
            trade_plan=plan,
            simulated_execution=execution,
            settlement=settlement,
        )

    def _detail_from_outcome(self, outcome: DecisionOutcome) -> ExplorerDetail:
        execution = (
            _optional_get(self._storage, SimulatedExecution, outcome.execution_id)
            if outcome.execution_id
            else None
        )
        decision = _optional_get(self._storage, Decision, outcome.decision_id)
        session = (
            _optional_get(self._storage, ResearchSession, outcome.research_session_id)
            if outcome.research_session_id
            else None
        )
        run = (
            _run_by_session_id(self._storage, outcome.research_session_id)
            if outcome.research_session_id
            else None
        )
        plan = (
            _optional_get(self._storage, TradePlan, outcome.trade_plan_id)
            if outcome.trade_plan_id
            else None
        )
        return self._detail_from_known(
            research_run=run,
            research_session=session,
            decision=decision,
            trade_plan=plan,
            simulated_execution=execution,
            settlement=outcome,
        )

    def _detail_from_known(
        self,
        *,
        research_run: ResearchRun | None,
        research_session: ResearchSession | None,
        decision: Decision | None,
        trade_plan: TradePlan | None = None,
        simulated_execution: SimulatedExecution | None = None,
        settlement: DecisionOutcome | None = None,
    ) -> ExplorerDetail:
        if decision is not None and trade_plan is None:
            trade_plan = self._storage.get_trade_plan_by_decision_id(
                decision.decision_id
            )
        if trade_plan is not None and simulated_execution is None:
            simulated_execution = (
                self._storage.get_simulated_execution_by_trade_plan_id(
                    trade_plan.trade_plan_id
                )
            )
        if simulated_execution is not None and settlement is None:
            settlement = self._storage.get_settlement_outcome_by_execution_id(
                simulated_execution.execution_id
            )
        evaluation = (
            _evaluation_by_outcome_id(self._storage, settlement.outcome_id)
            if settlement
            else None
        )
        review = (
            self._storage.get_review_by_decision_id(decision.decision_id)
            if decision
            else None
        )
        learnings = (
            _pending_learnings_by_review_id(self._storage, review.review_id)
            if review
            else ()
        )
        return ExplorerDetail(
            research_run=research_run,
            research_session=research_session,
            decision=decision,
            trade_plan=trade_plan,
            simulated_execution=simulated_execution,
            settlement=settlement,
            evaluation=evaluation,
            review=review,
            learning_proposals=learnings,
        )

    def _context(self) -> _ExplorerContext:
        sessions = self._storage.list(ResearchSession)
        runs = self._storage.list(ResearchRun)
        outcomes = self._storage.list(DecisionOutcome)
        return _ExplorerContext(
            market_by_session_id={
                session.research_session_id: session.scope.market
                for session in sessions
            },
            run_id_by_session_id={
                run.research_session_id: run.run_id
                for run in runs
                if run.research_session_id is not None
            },
            outcome_by_execution_id={
                outcome.execution_id: outcome
                for outcome in outcomes
                if outcome.execution_id is not None
            },
        )


@dataclass(frozen=True)
class _ExplorerContext:
    market_by_session_id: dict[str, str]
    run_id_by_session_id: dict[str, str]
    outcome_by_execution_id: dict[str, DecisionOutcome]


def _matches_execution(
    row: ExecutionListItem,
    *,
    symbol: str | None,
    market: str | None,
    status: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
) -> bool:
    execution = row.execution
    return (
        (symbol is None or execution.symbol == symbol)
        and (market is None or row.market == market)
        and (status is None or execution.execution_status.value == status)
        and (created_from is None or execution.created_at >= created_from)
        and (created_to is None or execution.created_at <= created_to)
    )


def _matches_settlement(
    row: SettlementListItem,
    *,
    symbol: str | None,
    market: str | None,
    status: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
) -> bool:
    settlement = row.settlement
    return (
        (symbol is None or settlement.symbol == symbol)
        and (market is None or row.market == market)
        and (status is None or settlement.status.value == status)
        and (created_from is None or settlement.created_at >= created_from)
        and (created_to is None or settlement.created_at <= created_to)
    )


def _sort_execution_rows(
    rows: list[ExecutionListItem],
    sort: str,
) -> list[ExecutionListItem]:
    descending = sort.startswith("-")
    field = sort.removeprefix("-")
    if field == "symbol":
        return sorted(
            rows,
            key=lambda row: (row.execution.symbol, row.execution.execution_id),
            reverse=descending,
        )
    elif field == "status":
        return sorted(
            rows,
            key=lambda row: (
                row.execution.execution_status.value,
                row.execution.execution_id,
            ),
            reverse=descending,
        )
    return sorted(
        rows,
        key=lambda row: (row.execution.created_at, row.execution.execution_id),
        reverse=descending,
    )


def _sort_settlement_rows(
    rows: list[SettlementListItem],
    sort: str,
) -> list[SettlementListItem]:
    descending = sort.startswith("-")
    field = sort.removeprefix("-")
    if field == "symbol":
        return sorted(
            rows,
            key=lambda row: (row.settlement.symbol, row.settlement.outcome_id),
            reverse=descending,
        )
    elif field == "status":
        return sorted(
            rows,
            key=lambda row: (
                row.settlement.status.value,
                row.settlement.outcome_id,
            ),
            reverse=descending,
        )
    elif field == "created_at":
        return sorted(
            rows,
            key=lambda row: (row.settlement.created_at, row.settlement.outcome_id),
            reverse=descending,
        )
    return sorted(
        rows,
        key=lambda row: (row.settlement.settled_at, row.settlement.outcome_id),
        reverse=descending,
    )


def _page[T](items: list[T], page: int, page_size: int) -> ExplorerPage[T]:
    start = (page - 1) * page_size
    return ExplorerPage(
        items=tuple(items[start : start + page_size]),
        total=len(items),
        page=page,
        page_size=page_size,
    )


def _optional_get[TEntity: KernelModel](
    storage: Storage,
    entity_type: type[TEntity],
    entity_id: str,
) -> TEntity | None:
    try:
        return storage.get(entity_type, entity_id)
    except MissingEntityError:
        return None


def _decision_by_session_id(
    storage: Storage,
    research_session_id: str,
) -> Decision | None:
    decisions = [
        decision
        for decision in storage.list(Decision)
        if decision.research_session_id == research_session_id
    ]
    return decisions[-1] if decisions else None


def _run_by_session_id(
    storage: Storage,
    research_session_id: str,
) -> ResearchRun | None:
    for run in storage.list(ResearchRun):
        if run.research_session_id == research_session_id:
            return run
    return None


def _evaluation_by_outcome_id(
    storage: Storage,
    outcome_id: str,
) -> DecisionEvaluation | None:
    for evaluation in storage.list(DecisionEvaluation):
        if evaluation.outcome_id == outcome_id:
            return evaluation
    return None


def _pending_learnings_by_review_id(
    storage: Storage,
    review_id: str,
) -> tuple[Learning, ...]:
    return tuple(
        learning
        for learning in storage.list(Learning)
        if learning.review_id == review_id
        and learning.approval_status.value == "pending"
    )


def _outcome_id(outcome: DecisionOutcome | None) -> str | None:
    return outcome.outcome_id if outcome is not None else None
