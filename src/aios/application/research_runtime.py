from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aios.adapters.llm import LLMAdapter
from aios.adapters.market_data import MarketDataAdapter
from aios.adapters.vibe_trading import VibeTradingResearchAdapter
from aios.application.brain002 import SkillRegistry
from aios.application.brain_research_pipeline import BrainEvidenceRepository
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.application.research_runner import ResearchRunner
from aios.application.simulated_execution import SimulatedExecutionService
from aios.application.trade_plan import TradePlanService
from aios.kernel.decision import Decision
from aios.kernel.enums import TradePlanStatus
from aios.kernel.execution import SimulatedExecution
from aios.kernel.research_run import ResearchRun
from aios.kernel.trade_plan import TradePlan
from aios.workflows.decision_lifecycle import DecisionLifecycleService


@dataclass(frozen=True)
class ResearchRuntimeResult:
    run: ResearchRun
    trade_plan: TradePlan | None
    execution: SimulatedExecution | None


class ResearchRuntimeService:
    """Orchestrate research output into simulated execution without changing BRAIN."""

    def __init__(
        self,
        *,
        lifecycle: DecisionLifecycleService,
        market_data_adapter: MarketDataAdapter,
        vibe_trading_adapter: VibeTradingResearchAdapter,
        llm_adapter: LLMAdapter | None = None,
        brain002_registry: SkillRegistry | None = None,
        brain_evidence_repository: BrainEvidenceRepository | None = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._storage = lifecycle.storage
        self._market_data_adapter = market_data_adapter
        self._vibe_trading_adapter = vibe_trading_adapter
        self._llm_adapter = llm_adapter
        self._brain002_registry = brain002_registry
        self._brain_evidence_repository = brain_evidence_repository

    def run_watchlist_item(
        self,
        *,
        watchlist_item_id: str,
        horizon_days: int,
        as_of: datetime,
        workflow: str,
        provider: str,
        model: str,
    ) -> ResearchRuntimeResult:
        run = ResearchRunner(
            lifecycle=self._lifecycle,
            market_data_adapter=self._market_data_adapter,
            vibe_trading_adapter=self._vibe_trading_adapter,
            llm_adapter=self._llm_adapter,
            brain002_registry=self._brain002_registry,
            brain_evidence_repository=self._brain_evidence_repository,
        ).run_research(
            watchlist_item_id=watchlist_item_id,
            horizon_days=horizon_days,
            as_of=as_of,
            workflow=workflow,
            provider=provider,
            model=model,
        )
        decision = self._decision_for_run(run)
        if decision is None:
            return ResearchRuntimeResult(run=run, trade_plan=None, execution=None)
        plan = TradePlanService(self._lifecycle).create_from_decision(
            decision.decision_id
        )
        if plan.status is not TradePlanStatus.READY:
            return ResearchRuntimeResult(run=run, trade_plan=plan, execution=None)
        execution = SimulatedExecutionService(
            lifecycle=ResearchLifecycleService(self._storage),
            market_data_adapter=self._market_data_adapter,
        ).execute_trade_plan(plan.trade_plan_id)
        return ResearchRuntimeResult(run=run, trade_plan=plan, execution=execution)

    def _decision_for_run(self, run: ResearchRun) -> Decision | None:
        if run.raw_output_reference and run.raw_output_reference.startswith("brain:"):
            decision_result_id = run.raw_output_reference.removeprefix("brain:")
            return self._storage.get_decision_by_decision_result_id(decision_result_id)
        if run.research_session_id is None:
            return None
        decisions = [
            decision
            for decision in self._storage.list(Decision)
            if decision.research_session_id == run.research_session_id
        ]
        return decisions[-1] if decisions else None
