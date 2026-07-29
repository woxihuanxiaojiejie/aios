from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from aios.adapters.storage import Storage
from aios.application.explorer import ExecutionSettlementExplorer, ExplorerDetail
from aios.application.test_data_filter import should_include_test_data
from aios.kernel.decision import Decision
from aios.kernel.execution import SimulatedExecution
from aios.kernel.learning import Learning
from aios.kernel.research_run import ResearchRun
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.kernel.trade_plan import TradePlan


@dataclass(frozen=True)
class DashboardCounts:
    research_runs: int
    completed_research_runs: int
    failed_or_resumable_research_runs: int
    decisions: int
    trade_plans: int
    simulated_executions: int
    settlements: int
    pending_learning_proposals: int
    positive_settlements: int
    negative_settlements: int


@dataclass(frozen=True)
class DashboardPerformance:
    average_return: Decimal | None


@dataclass(frozen=True)
class AttentionRequiredItem:
    type: str
    symbol: str | None
    market: str | None
    current_stage: str
    missing_stage: str
    created_at: datetime
    detail_path: str
    detail_id: str


@dataclass(frozen=True)
class RecentResearchItem:
    run_id: str
    created_at: datetime
    symbol: str | None
    market: str | None
    research_status: str
    decision_action: str | None
    confidence: float | None
    trade_plan_status: str | None
    current_loop_stage: str


@dataclass(frozen=True)
class RecentSettlementItem:
    settlement_id: str
    settled_at: datetime
    symbol: str
    market: str | None
    decision_action: str | None
    entry_price: Decimal | None
    exit_price: Decimal | None
    return_rate: Decimal | None
    pnl: Decimal | None
    evaluation_summary: str | None
    review_status: str | None


@dataclass(frozen=True)
class DashboardSummary:
    generated_at: datetime
    counts: DashboardCounts
    performance: DashboardPerformance
    attention_required: tuple[AttentionRequiredItem, ...]
    recent_research: tuple[RecentResearchItem, ...]
    recent_settlements: tuple[RecentSettlementItem, ...]


class DashboardSummaryService:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage
        self._explorer = ExecutionSettlementExplorer(storage)

    def summary(
        self,
        *,
        generated_at: datetime,
        include_test_data: bool = False,
    ) -> DashboardSummary:
        runs = [
            run
            for run in self._storage.list(ResearchRun)
            if should_include_test_data(run, include_test_data=include_test_data)
        ]
        visible_session_ids = {
            run.research_session_id for run in runs if run.research_session_id
        }
        decisions = [
            decision
            for decision in self._storage.list(Decision)
            if _has_visible_session(decision.research_session_id, visible_session_ids)
            or should_include_test_data(
                decision,
                include_test_data=include_test_data,
            )
        ]
        visible_decision_ids = {decision.decision_id for decision in decisions}
        trade_plans = [
            plan
            for plan in self._storage.list(TradePlan)
            if plan.decision_id in visible_decision_ids
            or _has_visible_session(plan.research_session_id, visible_session_ids)
        ]
        visible_trade_plan_ids = {plan.trade_plan_id for plan in trade_plans}
        executions = [
            execution
            for execution in self._storage.list(SimulatedExecution)
            if execution.decision_id in visible_decision_ids
            or execution.trade_plan_id in visible_trade_plan_ids
            or _has_visible_session(execution.research_session_id, visible_session_ids)
        ]
        visible_execution_ids = {execution.execution_id for execution in executions}
        settlements = [
            settlement
            for settlement in self._storage.list(DecisionOutcome)
            if settlement.decision_id in visible_decision_ids
            or (
                settlement.execution_id is not None
                and settlement.execution_id in visible_execution_ids
            )
            or _has_visible_session(settlement.research_session_id, visible_session_ids)
            or should_include_test_data(
                settlement,
                include_test_data=include_test_data,
            )
        ]
        visible_outcome_ids = {settlement.outcome_id for settlement in settlements}
        evaluations = self._storage.list(DecisionEvaluation)
        visible_evaluations = [
            evaluation
            for evaluation in evaluations
            if evaluation.outcome_id in visible_outcome_ids
        ]
        visible_review_ids = {
            review.review_id
            for review in self._storage.list(Review)
            if review.decision_id in visible_decision_ids
        }
        learnings = [
            learning
            for learning in self._storage.list(Learning)
            if learning.review_id in visible_review_ids
            or should_include_test_data(
                learning,
                include_test_data=include_test_data,
            )
        ]

        evaluated_outcome_ids = {
            evaluation.outcome_id for evaluation in visible_evaluations
        }
        evaluated_returns = [
            settlement.return_rate
            for settlement in settlements
            if settlement.outcome_id in evaluated_outcome_ids
            and settlement.return_rate is not None
        ]
        counts = DashboardCounts(
            research_runs=len(runs),
            completed_research_runs=sum(1 for run in runs if run.status == "completed"),
            failed_or_resumable_research_runs=sum(
                1 for run in runs if run.status in {"failed", "running"}
            ),
            decisions=len(decisions),
            trade_plans=len(trade_plans),
            simulated_executions=len(executions),
            settlements=len(settlements),
            pending_learning_proposals=sum(
                1
                for learning in learnings
                if learning.approval_status.value == "pending"
            ),
            positive_settlements=sum(
                1
                for settlement in settlements
                if settlement.return_rate is not None and settlement.return_rate > 0
            ),
            negative_settlements=sum(
                1
                for settlement in settlements
                if settlement.return_rate is not None and settlement.return_rate < 0
            ),
        )
        return DashboardSummary(
            generated_at=generated_at,
            counts=counts,
            performance=DashboardPerformance(
                average_return=_average(evaluated_returns),
            ),
            attention_required=tuple(self._attention_required(runs)[:20]),
            recent_research=tuple(self._recent_research(runs)[:10]),
            recent_settlements=tuple(self._recent_settlements(settlements)[:10]),
        )

    def _attention_required(
        self,
        runs: list[ResearchRun],
    ) -> list[AttentionRequiredItem]:
        items: list[AttentionRequiredItem] = []
        for run in sorted(runs, key=lambda item: item.created_at, reverse=True):
            detail = self._explorer.research_run_detail(run.run_id)
            market = (
                detail.research_session.scope.market
                if detail.research_session
                else None
            )
            if run.status == "failed":
                items.append(
                    AttentionRequiredItem(
                        type="research_run_failed",
                        symbol=run.symbol,
                        market=market,
                        current_stage=run.failed_stage or run.current_stage,
                        missing_stage="resume",
                        created_at=run.created_at,
                        detail_path=f"/research/{run.run_id}",
                        detail_id=run.run_id,
                    )
                )
                continue
            if run.status == "running":
                items.append(
                    AttentionRequiredItem(
                        type="research_run_needs_resume",
                        symbol=run.symbol,
                        market=market,
                        current_stage=run.current_stage,
                        missing_stage="resume",
                        created_at=run.created_at,
                        detail_path=f"/research/{run.run_id}",
                        detail_id=run.run_id,
                    )
                )
                continue
            if detail.decision and not detail.trade_plan:
                items.append(
                    _missing(
                        run,
                        market,
                        "missing_trade_plan",
                        "Decision 已生成",
                        "Trade Plan",
                    )
                )
            elif detail.trade_plan and not detail.simulated_execution:
                items.append(
                    _missing(
                        run,
                        market,
                        "missing_simulated_execution",
                        "Trade Plan 已生成",
                        "Simulated Execution",
                    )
                )
            elif detail.simulated_execution and not detail.settlement:
                items.append(
                    AttentionRequiredItem(
                        type="missing_settlement",
                        symbol=run.symbol,
                        market=market,
                        current_stage="Simulated Execution 已生成",
                        missing_stage="Settlement",
                        created_at=detail.simulated_execution.created_at,
                        detail_path=(
                            f"/executions/{detail.simulated_execution.execution_id}"
                        ),
                        detail_id=detail.simulated_execution.execution_id,
                    )
                )
            elif detail.settlement and not detail.evaluation:
                items.append(
                    _missing_settlement(
                        run,
                        market,
                        detail.settlement,
                        "missing_evaluation",
                        "Evaluation",
                    )
                )
            elif detail.evaluation and not detail.review:
                items.append(
                    _missing_settlement(
                        run, market, detail.settlement, "missing_review", "Review"
                    )
                )
            elif detail.review and not detail.learning_proposals:
                items.append(
                    AttentionRequiredItem(
                        type="missing_learning_proposal",
                        symbol=run.symbol,
                        market=market,
                        current_stage="Review 已生成",
                        missing_stage="Learning Proposal",
                        created_at=detail.review.created_at,
                        detail_path=f"/research/{run.run_id}",
                        detail_id=run.run_id,
                    )
                )
        return items

    def _recent_research(self, runs: list[ResearchRun]) -> list[RecentResearchItem]:
        rows: list[RecentResearchItem] = []
        for run in sorted(runs, key=lambda item: item.created_at, reverse=True):
            detail = self._explorer.research_run_detail(run.run_id)
            rows.append(
                RecentResearchItem(
                    run_id=run.run_id,
                    created_at=run.created_at,
                    symbol=run.symbol,
                    market=detail.research_session.scope.market
                    if detail.research_session
                    else None,
                    research_status=run.status,
                    decision_action=detail.decision.action.value
                    if detail.decision
                    else None,
                    confidence=detail.decision.confidence if detail.decision else None,
                    trade_plan_status=detail.trade_plan.status.value
                    if detail.trade_plan
                    else None,
                    current_loop_stage=_loop_stage(detail),
                )
            )
        return rows

    def _recent_settlements(
        self,
        settlements: list[DecisionOutcome],
    ) -> list[RecentSettlementItem]:
        rows: list[RecentSettlementItem] = []
        for settlement in sorted(
            settlements,
            key=lambda item: item.settled_at,
            reverse=True,
        ):
            detail = self._explorer.settlement_detail(settlement.outcome_id)
            rows.append(
                RecentSettlementItem(
                    settlement_id=settlement.outcome_id,
                    settled_at=settlement.settled_at,
                    symbol=settlement.symbol,
                    market=detail.research_session.scope.market
                    if detail.research_session
                    else None,
                    decision_action=detail.decision.action.value
                    if detail.decision
                    else None,
                    entry_price=settlement.entry_price,
                    exit_price=settlement.exit_price,
                    return_rate=settlement.return_rate,
                    pnl=settlement.pnl,
                    evaluation_summary=detail.evaluation.explanation
                    if detail.evaluation
                    else None,
                    review_status=detail.review.outcome.value
                    if detail.review
                    else None,
                )
            )
        return rows


def _average(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values) / Decimal(len(values))


def _has_visible_session(
    session_id: str | None,
    visible_session_ids: set[str],
) -> bool:
    return session_id is not None and session_id in visible_session_ids


def _missing(
    run: ResearchRun,
    market: str | None,
    item_type: str,
    current_stage: str,
    missing_stage: str,
) -> AttentionRequiredItem:
    return AttentionRequiredItem(
        type=item_type,
        symbol=run.symbol,
        market=market,
        current_stage=current_stage,
        missing_stage=missing_stage,
        created_at=run.created_at,
        detail_path=f"/research/{run.run_id}",
        detail_id=run.run_id,
    )


def _missing_settlement(
    run: ResearchRun,
    market: str | None,
    settlement: DecisionOutcome | None,
    item_type: str,
    missing_stage: str,
) -> AttentionRequiredItem:
    detail_id = settlement.outcome_id if settlement else run.run_id
    return AttentionRequiredItem(
        type=item_type,
        symbol=run.symbol,
        market=market,
        current_stage="Settlement 已生成",
        missing_stage=missing_stage,
        created_at=settlement.settled_at if settlement else run.created_at,
        detail_path=f"/settlements/{detail_id}"
        if settlement
        else f"/research/{run.run_id}",
        detail_id=detail_id,
    )


def _loop_stage(detail: ExplorerDetail) -> str:
    if detail.learning_proposals:
        return "Learning Proposal"
    if detail.review:
        return "Review"
    if detail.evaluation:
        return "Evaluation"
    if detail.settlement:
        return "Settlement"
    if detail.simulated_execution:
        return "Simulated Execution"
    if detail.trade_plan:
        return "Trade Plan"
    if detail.decision:
        return "Decision"
    return "Research"
