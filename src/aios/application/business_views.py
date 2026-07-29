from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from aios.adapters.storage import Storage
from aios.application.explorer import ExecutionSettlementExplorer
from aios.application.test_data_filter import should_include_test_data
from aios.kernel.base import KernelModel
from aios.kernel.brain002 import AnalysisTask, SkillExecution, SkillResult
from aios.kernel.brain003 import DiscussionResult
from aios.kernel.brain004 import DecisionResult
from aios.kernel.decision import Decision
from aios.kernel.errors import MissingEntityError
from aios.kernel.execution import SimulatedExecution
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchSession
from aios.kernel.research_run import ResearchRun
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.kernel.trade_plan import TradePlan
from aios.kernel.watchlist import WatchlistItem


class _CreatedAt(Protocol):
    created_at: datetime


@dataclass(frozen=True)
class BusinessPage[T]:
    items: tuple[T, ...]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class BrainResearchRecords:
    analysis_task: AnalysisTask | None
    skill_executions: tuple[SkillExecution, ...]
    skill_results: tuple[SkillResult, ...]
    discussion_result: DiscussionResult | None
    decision_result: DecisionResult | None


@dataclass(frozen=True)
class DecisionSummary:
    decision: Decision
    research_run: ResearchRun | None
    research_session: ResearchSession | None
    watchlist_item: WatchlistItem | None
    trade_plan: TradePlan | None
    simulated_execution: SimulatedExecution | None


@dataclass(frozen=True)
class ReviewSummary:
    settlement: DecisionOutcome
    research_run: ResearchRun | None
    research_session: ResearchSession | None
    decision: Decision | None
    trade_plan: TradePlan | None
    simulated_execution: SimulatedExecution | None
    evaluation: DecisionEvaluation | None
    review: Review | None
    learning_proposals: tuple[Learning, ...]


@dataclass(frozen=True)
class LearningDetail:
    learning: Learning
    review: Review | None
    evaluation: DecisionEvaluation | None
    settlement: DecisionOutcome | None
    simulated_execution: SimulatedExecution | None
    decision: Decision | None
    research_run: ResearchRun | None
    research_session: ResearchSession | None
    current_value_summary: str
    proposed_value_summary: str
    change_summary: str
    technical_details: dict[str, Any]


class BusinessViewService:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage
        self._explorer = ExecutionSettlementExplorer(storage)

    def brain_records_for_session(
        self,
        session: ResearchSession | None,
        decision: Decision | None,
    ) -> BrainResearchRecords:
        if session is None:
            return BrainResearchRecords(None, (), (), None, None)
        task = self._analysis_task_for_session(session)
        if task is None:
            return BrainResearchRecords(None, (), (), None, None)
        executions = tuple(
            item
            for item in self._storage.list(SkillExecution)
            if item.task_id == task.task_id
        )
        execution_ids = {item.execution_id for item in executions}
        skill_results = tuple(
            item
            for item in self._storage.list(SkillResult)
            if item.execution_id in execution_ids
        )
        skill_result_ids = {item.result_id for item in skill_results}
        discussion = _latest(
            item
            for item in self._storage.list(DiscussionResult)
            if item.task_id == task.task_id
            and set(item.skill_result_ids).issubset(skill_result_ids)
        )
        decision_result = None
        if decision and decision.decision_result_id:
            decision_result = _optional_get(
                self._storage,
                DecisionResult,
                decision.decision_result_id,
            )
        if decision_result is None and discussion is not None:
            decision_result = _latest(
                item
                for item in self._storage.list(DecisionResult)
                if item.discussion_result_id == discussion.discussion_result_id
            )
        return BrainResearchRecords(
            analysis_task=task,
            skill_executions=tuple(
                sorted(executions, key=lambda item: item.started_at)
            ),
            skill_results=tuple(
                sorted(skill_results, key=lambda item: item.created_at)
            ),
            discussion_result=discussion,
            decision_result=decision_result,
        )

    def decisions_summary(
        self,
        *,
        page: int,
        page_size: int,
        include_test_data: bool,
    ) -> BusinessPage[DecisionSummary]:
        rows = [
            self._decision_summary(decision)
            for decision in self._storage.list(Decision)
        ]
        rows = [
            row
            for row in rows
            if _include_by_run_or_entity(
                row.research_run,
                row.decision,
                include_test_data=include_test_data,
            )
        ]
        rows.sort(key=lambda item: item.decision.created_at, reverse=True)
        return _page(rows, page, page_size)

    def reviews_summary(
        self,
        *,
        page: int,
        page_size: int,
        include_test_data: bool,
    ) -> BusinessPage[ReviewSummary]:
        rows = [
            self._review_summary(outcome)
            for outcome in self._storage.list(DecisionOutcome)
            if outcome.execution_id is not None
        ]
        rows = [
            row
            for row in rows
            if _include_by_run_or_entity(
                row.research_run,
                row.settlement,
                include_test_data=include_test_data,
            )
        ]
        rows.sort(key=lambda item: item.settlement.settled_at, reverse=True)
        return _page(rows, page, page_size)

    def learning_detail(self, learning_id: str) -> LearningDetail:
        learning = self._storage.get(Learning, learning_id)
        review = _optional_get(self._storage, Review, learning.review_id)
        decision = (
            _optional_get(self._storage, Decision, review.decision_id)
            if review
            else None
        )
        settlement = (
            self._storage.get_decision_outcome_by_decision_id(decision.decision_id)
            if decision
            else None
        )
        evaluation = (
            _evaluation_by_outcome_id(self._storage, settlement.outcome_id)
            if settlement
            else None
        )
        detail = (
            self._explorer.settlement_detail(settlement.outcome_id)
            if settlement
            else None
        )
        return LearningDetail(
            learning=learning,
            review=review,
            evaluation=evaluation,
            settlement=settlement,
            simulated_execution=detail.simulated_execution if detail else None,
            decision=decision,
            research_run=detail.research_run if detail else None,
            research_session=detail.research_session if detail else None,
            current_value_summary=_summarize_value(learning.before),
            proposed_value_summary=_summarize_value(learning.after),
            change_summary=_change_summary(learning.before, learning.after),
            technical_details={
                "before": learning.before,
                "after": learning.after,
                "review_id": learning.review_id,
            },
        )

    def _decision_summary(self, decision: Decision) -> DecisionSummary:
        session = (
            _optional_get(self._storage, ResearchSession, decision.research_session_id)
            if decision.research_session_id
            else None
        )
        run = _run_by_session_id(self._storage, decision.research_session_id)
        watchlist = (
            _optional_get(self._storage, WatchlistItem, run.watchlist_item_id)
            if run
            else None
        )
        trade_plan = self._storage.get_trade_plan_by_decision_id(decision.decision_id)
        execution = (
            self._storage.get_simulated_execution_by_trade_plan_id(
                trade_plan.trade_plan_id
            )
            if trade_plan
            else None
        )
        return DecisionSummary(
            decision=decision,
            research_run=run,
            research_session=session,
            watchlist_item=watchlist,
            trade_plan=trade_plan,
            simulated_execution=execution,
        )

    def _review_summary(self, settlement: DecisionOutcome) -> ReviewSummary:
        detail = self._explorer.settlement_detail(settlement.outcome_id)
        return ReviewSummary(
            settlement=settlement,
            research_run=detail.research_run,
            research_session=detail.research_session,
            decision=detail.decision,
            trade_plan=detail.trade_plan,
            simulated_execution=detail.simulated_execution,
            evaluation=detail.evaluation,
            review=detail.review,
            learning_proposals=detail.learning_proposals,
        )

    def _analysis_task_for_session(
        self,
        session: ResearchSession,
    ) -> AnalysisTask | None:
        evidence_ids = set(session.evidence_ids)
        return _latest(
            task
            for task in self._storage.list(AnalysisTask)
            if task.symbol == session.scope.symbol
            and task.market == session.scope.market
            and evidence_ids.issubset(set(task.evidence_ids))
        )


def _include_by_run_or_entity(
    run: ResearchRun | None,
    entity: object,
    *,
    include_test_data: bool,
) -> bool:
    if run is not None:
        return should_include_test_data(run, include_test_data=include_test_data)
    return should_include_test_data(entity, include_test_data=include_test_data)


def _optional_get[EntityT: KernelModel](
    storage: Storage,
    entity_type: type[EntityT],
    entity_id: str,
) -> EntityT | None:
    try:
        return storage.get(entity_type, entity_id)
    except MissingEntityError:
        return None


def _run_by_session_id(storage: Storage, session_id: str | None) -> ResearchRun | None:
    if session_id is None:
        return None
    for run in storage.list(ResearchRun):
        if run.research_session_id == session_id:
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


def _latest[ItemT: _CreatedAt](items: Iterable[ItemT]) -> ItemT | None:
    rows = list(items)
    if not rows:
        return None
    return max(rows, key=lambda item: item.created_at)


def _page[ItemT](rows: list[ItemT], page: int, page_size: int) -> BusinessPage[ItemT]:
    start = (page - 1) * page_size
    return BusinessPage(
        items=tuple(rows[start : start + page_size]),
        total=len(rows),
        page=page,
        page_size=page_size,
    )


def _summarize_value(value: object) -> str:
    if isinstance(value, dict):
        if "weight" in value:
            return f"权重 {value['weight']}"
        if "status" in value:
            return str(value["status"])
        if "suggestion" in value:
            return str(value["suggestion"])
        return "、".join(str(key) for key in list(value.keys())[:4]) or "-"
    if isinstance(value, list | tuple):
        return f"{len(value)} 项"
    return str(value)


def _change_summary(before: object, after: object) -> str:
    if isinstance(before, dict) and isinstance(after, dict):
        if "weight" in before and "weight" in after:
            return f"{before['weight']} -> {after['weight']}"
        changed = [key for key in after if before.get(key) != after.get(key)]
        return "、".join(changed) if changed else "无变化"
    return "建议内容已变更"
