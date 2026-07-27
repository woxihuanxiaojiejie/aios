from __future__ import annotations

import builtins
from datetime import datetime
from typing import Protocol, TypeVar

from aios.kernel.base import KernelModel
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
from aios.kernel.execution import SimulatedExecution
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.research_run import ResearchRun
from aios.kernel.review import Review
from aios.kernel.settlement import (
    DecisionEvaluation,
    DecisionOutcome,
    ResearchSettlementRecord,
)
from aios.kernel.trade_plan import TradePlan
from aios.kernel.watchlist import WatchlistItem

EntityT = TypeVar("EntityT", bound=KernelModel)


class Storage(Protocol):
    def save(self, entity: KernelModel) -> None:
        """Persist a new entity."""

    def replace(self, entity: KernelModel) -> None:
        """Replace an existing entity without changing its id."""

    def get(self, entity_type: type[EntityT], entity_id: str) -> EntityT:
        """Return an entity by type and id."""

    def list(self, entity_type: type[EntityT]) -> list[EntityT]:
        """Return all entities of a given type."""

    def exists(self, entity_type: type[EntityT], entity_id: str) -> bool:
        """Check whether an entity exists."""

    def get_decision_outcome_by_decision_id(
        self,
        decision_id: str,
    ) -> DecisionOutcome | None:
        """Return the settlement outcome for a Decision if one exists."""

    def get_decision_evaluation_by_decision_id(
        self,
        decision_id: str,
        evaluation_rules_version: str,
    ) -> DecisionEvaluation | None:
        """Return the versioned evaluation for a Decision if one exists."""

    def get_decision_by_decision_result_id(
        self,
        decision_result_id: str,
    ) -> Decision | None:
        """Return the BRAIN formal Decision for a DecisionResult if one exists."""

    def get_trade_plan_by_decision_id(self, decision_id: str) -> TradePlan | None:
        """Return the TradePlan for a Decision if one exists."""

    def get_simulated_execution_by_trade_plan_id(
        self,
        trade_plan_id: str,
    ) -> SimulatedExecution | None:
        """Return the SimulatedExecution for a TradePlan if one exists."""

    def get_settlement_outcome_by_execution_id(
        self,
        execution_id: str,
    ) -> DecisionOutcome | None:
        """Return the settlement Outcome for a SimulatedExecution if one exists."""

    def get_review_by_decision_id(self, decision_id: str) -> Review | None:
        """Return the Review for a Decision if one exists."""

    def list_watchlist_items(
        self,
        *,
        status: WatchlistStatus | None = WatchlistStatus.ACTIVE,
        market: str | None = None,
        symbol: str | None = None,
    ) -> builtins.list[WatchlistItem]:
        """Return WatchlistItems filtered by optional status, market, and symbol."""

    def find_active_watchlist_item(
        self,
        market: str,
        symbol: str,
    ) -> WatchlistItem | None:
        """Return the active WatchlistItem for a normalized market/symbol."""

    def list_research_sessions(
        self,
        *,
        watchlist_item_id: str | None = None,
        symbol: str | None = None,
        market: str | None = None,
        status: ResearchSessionStatus | None = None,
        horizon_days: int | None = None,
    ) -> builtins.list[ResearchSession]:
        """Return ResearchSessions filtered by optional scope and status fields."""

    def find_active_research_session(
        self,
        watchlist_item_id: str,
        as_of: datetime,
        horizon_days: int,
    ) -> ResearchSession | None:
        """Return a non-cancelled ResearchSession for an exact frozen scope."""

    def list_agent_reports(
        self,
        *,
        research_session_id: str | None = None,
        role: AgentRole | None = None,
        status: AgentReportStatus | None = None,
    ) -> builtins.list[AgentReport]:
        """Return AgentReports filtered by optional session, role, and status."""

    def find_active_agent_report(
        self,
        research_session_id: str,
        role: AgentRole,
    ) -> AgentReport | None:
        """Return the active AgentReport for a session role."""

    def list_hypotheses(
        self,
        *,
        research_session_id: str | None = None,
        status: HypothesisStatus | None = None,
    ) -> builtins.list[Hypothesis]:
        """Return Hypotheses filtered by optional session and status."""

    def list_debates(
        self,
        *,
        research_session_id: str | None = None,
    ) -> builtins.list[DebateRecord]:
        """Return DebateRecords filtered by optional session."""

    def get_debate_statement(
        self,
        debate_id: str,
        agent_report_id: str,
        hypothesis_id: str,
    ) -> DebateStatement | None:
        """Return one DebateStatement for a report/hypothesis pair."""

    def get_decision_proposal_by_debate_id(
        self,
        debate_id: str,
    ) -> DecisionProposal | None:
        """Return the DecisionProposal for a Debate if one exists."""

    def get_risk_review_by_proposal_id(self, proposal_id: str) -> RiskReview | None:
        """Return the RiskReview for a DecisionProposal if one exists."""

    def get_risk_review_by_decision_result_id(
        self,
        decision_result_id: str,
    ) -> RiskReview | None:
        """Return the BRAIN RiskReview for a DecisionResult if one exists."""

    def get_decision_assembly_by_proposal_id(
        self,
        proposal_id: str,
    ) -> DecisionAssemblyRecord | None:
        """Return the final Decision assembly record for a proposal."""

    def get_research_settlement_by_assembly_id(
        self,
        assembly_id: str,
    ) -> ResearchSettlementRecord | None:
        """Return the research settlement trace for an assembly if one exists."""

    def list_research_runs(
        self,
        *,
        watchlist_item_id: str | None = None,
        status: str | None = None,
    ) -> builtins.list[ResearchRun]:
        """Return ResearchRun orchestration records filtered by run metadata."""
