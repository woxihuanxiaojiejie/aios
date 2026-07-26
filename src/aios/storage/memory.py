from __future__ import annotations

import builtins
from collections import defaultdict
from datetime import datetime
from typing import Protocol, cast

from aios.kernel.base import KernelModel
from aios.kernel.brain002 import (
    AnalysisTask,
    SkillDefinition,
    SkillExecution,
    SkillResult,
)
from aios.kernel.brain003 import DiscussionExecution, DiscussionResult
from aios.kernel.debate import (
    DebateRecord,
    DebateStatement,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    AgentReportStatus,
    AgentRole,
    HypothesisStatus,
    ResearchSessionStatus,
    WatchlistStatus,
)
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    UnsupportedEntityError,
)
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.research_run import ResearchRun
from aios.kernel.review import Review
from aios.kernel.settlement import (
    DecisionEvaluation,
    DecisionOutcome,
    ResearchSettlementRecord,
)
from aios.kernel.watchlist import WatchlistItem

SUPPORTED_ENTITY_TYPES = (
    Evidence,
    Experiment,
    Decision,
    Review,
    Learning,
    DecisionOutcome,
    DecisionEvaluation,
    WatchlistItem,
    ResearchSession,
    AgentReport,
    Hypothesis,
    DebateRecord,
    DebateStatement,
    DecisionProposal,
    RiskReview,
    DecisionAssemblyRecord,
    ResearchSettlementRecord,
    ResearchRun,
    SkillDefinition,
    AnalysisTask,
    SkillExecution,
    SkillResult,
    DiscussionExecution,
    DiscussionResult,
)


class _CreatedEntity(Protocol):
    entity_id: str
    created_at: datetime


class InMemoryStorage:
    def __init__(self) -> None:
        self._entities: dict[type[KernelModel], dict[str, KernelModel]] = defaultdict(
            dict
        )

    def save(self, entity: KernelModel) -> None:
        self._require_supported(type(entity))
        entity_type = type(entity)
        entity_id = entity.entity_id
        if entity_id in self._entities[entity_type]:
            msg = f"{entity_type.__name__} with id {entity_id} already exists"
            raise DuplicateEntityError(msg)
        self._entities[entity_type][entity_id] = entity

    def replace(self, entity: KernelModel) -> None:
        self._require_supported(type(entity))
        entity_type = type(entity)
        entity_id = entity.entity_id
        if entity_id not in self._entities[entity_type]:
            msg = f"{entity_type.__name__} with id {entity_id} does not exist"
            raise MissingEntityError(msg)
        self._entities[entity_type][entity_id] = entity

    def get[EntityT: KernelModel](
        self, entity_type: type[EntityT], entity_id: str
    ) -> EntityT:
        self._require_supported(entity_type)
        try:
            entity = self._entities[entity_type][entity_id]
        except KeyError as exc:
            msg = f"{entity_type.__name__} with id {entity_id} does not exist"
            raise MissingEntityError(msg) from exc
        return cast("EntityT", entity)

    def list[EntityT: KernelModel](self, entity_type: type[EntityT]) -> list[EntityT]:
        self._require_supported(entity_type)
        sorted_entities = sorted(
            self._entities[entity_type].values(),
            key=self._sort_key,
        )
        return [cast("EntityT", entity) for entity in sorted_entities]

    def exists[EntityT: KernelModel](
        self, entity_type: type[EntityT], entity_id: str
    ) -> bool:
        self._require_supported(entity_type)
        return entity_id in self._entities[entity_type]

    def get_decision_outcome_by_decision_id(
        self,
        decision_id: str,
    ) -> DecisionOutcome | None:
        self._require_supported(DecisionOutcome)
        for entity in self._entities[DecisionOutcome].values():
            outcome = cast("DecisionOutcome", entity)
            if outcome.decision_id == decision_id:
                return outcome
        return None

    def get_decision_evaluation_by_decision_id(
        self,
        decision_id: str,
        evaluation_rules_version: str,
    ) -> DecisionEvaluation | None:
        self._require_supported(DecisionEvaluation)
        for entity in self._entities[DecisionEvaluation].values():
            evaluation = cast("DecisionEvaluation", entity)
            if (
                evaluation.decision_id == decision_id
                and evaluation.evaluation_rules_version == evaluation_rules_version
            ):
                return evaluation
        return None

    def get_review_by_decision_id(self, decision_id: str) -> Review | None:
        self._require_supported(Review)
        for entity in self._entities[Review].values():
            review = cast("Review", entity)
            if review.decision_id == decision_id:
                return review
        return None

    def list_watchlist_items(
        self,
        *,
        status: WatchlistStatus | None = WatchlistStatus.ACTIVE,
        market: str | None = None,
        symbol: str | None = None,
    ) -> builtins.list[WatchlistItem]:
        self._require_supported(WatchlistItem)
        items: builtins.list[WatchlistItem] = self.list(WatchlistItem)
        if status is not None:
            items = [item for item in items if item.status is status]
        if market is not None:
            items = [item for item in items if item.market == market]
        if symbol is not None:
            items = [item for item in items if item.symbol == symbol]
        return items

    def find_active_watchlist_item(
        self,
        market: str,
        symbol: str,
    ) -> WatchlistItem | None:
        matches: builtins.list[WatchlistItem] = self.list_watchlist_items(
            status=WatchlistStatus.ACTIVE,
            market=market,
            symbol=symbol,
        )
        return matches[0] if matches else None

    def list_research_sessions(
        self,
        *,
        watchlist_item_id: str | None = None,
        symbol: str | None = None,
        market: str | None = None,
        status: ResearchSessionStatus | None = None,
        horizon_days: int | None = None,
    ) -> builtins.list[ResearchSession]:
        self._require_supported(ResearchSession)
        sessions: builtins.list[ResearchSession] = self.list(ResearchSession)
        if watchlist_item_id is not None:
            sessions = [
                session
                for session in sessions
                if session.scope.watchlist_item_id == watchlist_item_id
            ]
        if symbol is not None:
            sessions = [
                session for session in sessions if session.scope.symbol == symbol
            ]
        if market is not None:
            sessions = [
                session for session in sessions if session.scope.market == market
            ]
        if status is not None:
            sessions = [session for session in sessions if session.status is status]
        if horizon_days is not None:
            sessions = [
                session
                for session in sessions
                if session.scope.horizon_days == horizon_days
            ]
        return sessions

    def find_active_research_session(
        self,
        watchlist_item_id: str,
        as_of: datetime,
        horizon_days: int,
    ) -> ResearchSession | None:
        matches: builtins.list[ResearchSession] = [
            session
            for session in self.list_research_sessions(
                watchlist_item_id=watchlist_item_id,
                horizon_days=horizon_days,
            )
            if session.scope.as_of == as_of
            and session.status is not ResearchSessionStatus.CANCELLED
        ]
        return matches[0] if matches else None

    def list_agent_reports(
        self,
        *,
        research_session_id: str | None = None,
        role: AgentRole | None = None,
        status: AgentReportStatus | None = None,
    ) -> builtins.list[AgentReport]:
        self._require_supported(AgentReport)
        reports: builtins.list[AgentReport] = self.list(AgentReport)
        if research_session_id is not None:
            reports = [
                report
                for report in reports
                if report.research_session_id == research_session_id
            ]
        if role is not None:
            reports = [report for report in reports if report.role is role]
        if status is not None:
            reports = [report for report in reports if report.status is status]
        return reports

    def find_active_agent_report(
        self,
        research_session_id: str,
        role: AgentRole,
    ) -> AgentReport | None:
        matches = self.list_agent_reports(
            research_session_id=research_session_id,
            role=role,
            status=AgentReportStatus.ACTIVE,
        )
        return matches[0] if matches else None

    def list_hypotheses(
        self,
        *,
        research_session_id: str | None = None,
        status: HypothesisStatus | None = None,
    ) -> builtins.list[Hypothesis]:
        self._require_supported(Hypothesis)
        hypotheses: builtins.list[Hypothesis] = self.list(Hypothesis)
        if research_session_id is not None:
            hypotheses = [
                hypothesis
                for hypothesis in hypotheses
                if hypothesis.research_session_id == research_session_id
            ]
        if status is not None:
            hypotheses = [
                hypothesis for hypothesis in hypotheses if hypothesis.status is status
            ]
        return hypotheses

    def list_debates(
        self,
        *,
        research_session_id: str | None = None,
    ) -> builtins.list[DebateRecord]:
        self._require_supported(DebateRecord)
        debates: builtins.list[DebateRecord] = self.list(DebateRecord)
        if research_session_id is not None:
            debates = [
                debate
                for debate in debates
                if debate.research_session_id == research_session_id
            ]
        return debates

    def get_debate_statement(
        self,
        debate_id: str,
        agent_report_id: str,
        hypothesis_id: str,
    ) -> DebateStatement | None:
        self._require_supported(DebateStatement)
        for entity in self._entities[DebateStatement].values():
            statement = cast("DebateStatement", entity)
            if (
                statement.debate_id == debate_id
                and statement.agent_report_id == agent_report_id
                and statement.hypothesis_id == hypothesis_id
            ):
                return statement
        return None

    def get_decision_proposal_by_debate_id(
        self,
        debate_id: str,
    ) -> DecisionProposal | None:
        self._require_supported(DecisionProposal)
        for entity in self._entities[DecisionProposal].values():
            proposal = cast("DecisionProposal", entity)
            if proposal.debate_id == debate_id:
                return proposal
        return None

    def get_risk_review_by_proposal_id(self, proposal_id: str) -> RiskReview | None:
        self._require_supported(RiskReview)
        for entity in self._entities[RiskReview].values():
            review = cast("RiskReview", entity)
            if review.proposal_id == proposal_id:
                return review
        return None

    def get_decision_assembly_by_proposal_id(
        self,
        proposal_id: str,
    ) -> DecisionAssemblyRecord | None:
        self._require_supported(DecisionAssemblyRecord)
        for entity in self._entities[DecisionAssemblyRecord].values():
            assembly = cast("DecisionAssemblyRecord", entity)
            if assembly.proposal_id == proposal_id:
                return assembly
        return None

    def get_research_settlement_by_assembly_id(
        self,
        assembly_id: str,
    ) -> ResearchSettlementRecord | None:
        self._require_supported(ResearchSettlementRecord)
        for entity in self._entities[ResearchSettlementRecord].values():
            record = cast("ResearchSettlementRecord", entity)
            if record.assembly_id == assembly_id:
                return record
        return None

    def list_research_runs(
        self,
        *,
        watchlist_item_id: str | None = None,
        status: str | None = None,
    ) -> builtins.list[ResearchRun]:
        self._require_supported(ResearchRun)
        runs: builtins.list[ResearchRun] = self.list(ResearchRun)
        if watchlist_item_id is not None:
            runs = [run for run in runs if run.watchlist_item_id == watchlist_item_id]
        if status is not None:
            runs = [run for run in runs if run.status == status]
        return runs

    def _require_supported(self, entity_type: type[KernelModel]) -> None:
        if entity_type not in SUPPORTED_ENTITY_TYPES:
            msg = f"{entity_type.__name__} is not supported by InMemoryStorage"
            raise UnsupportedEntityError(msg)

    def _sort_key(self, entity: KernelModel) -> tuple[datetime, str]:
        if isinstance(entity, SkillExecution):
            return entity.started_at, entity.entity_id
        sortable = cast("_CreatedEntity", entity)
        return sortable.created_at, sortable.entity_id
