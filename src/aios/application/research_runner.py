from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from aios.adapters.llm import LLMAdapter
from aios.adapters.market_data import Adjustment, MarketDataAdapter
from aios.adapters.vibe_trading import VibeTradingResearchAdapter
from aios.application.brain002 import SkillRegistry
from aios.application.brain_research_pipeline import (
    BrainEvidenceRepository,
    BrainResearchPipeline,
)
from aios.application.debate import DebateService
from aios.application.market_evidence import MarketEvidenceImportService
from aios.application.research_records import ResearchRecordService
from aios.application.research_session import ResearchSessionService
from aios.kernel.base import utc_now
from aios.kernel.debate import (
    DebateRecord,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.enums import DebateStance, ResearchConclusion, RiskVerdict
from aios.kernel.errors import DuplicateEntityError, InvalidStateTransitionError
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.research_run import ResearchRun, ResearchRunStage
from aios.kernel.watchlist import WatchlistItem
from aios.vibe_trading.output_mapper import (
    VibeTradingRawResult,
    map_vibe_trading_result_to_agent_report_inputs,
)
from aios.workflows.decision_lifecycle import DecisionLifecycleService


class ResearchRunner:
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

    def run_research(
        self,
        *,
        watchlist_item_id: str,
        horizon_days: int,
        as_of: datetime,
        workflow: str,
        provider: str,
        model: str,
    ) -> ResearchRun:
        run = self._find_or_create_run(
            watchlist_item_id=watchlist_item_id,
            horizon_days=horizon_days,
            as_of=as_of,
            workflow=workflow,
            provider=provider,
            model=model,
        )
        return self._execute(run)

    def resume_research(self, run_id: str) -> ResearchRun:
        run = self.get_run_status(run_id)
        if run.status == "completed":
            return run
        return self._execute(
            run.model_copy(
                update={"status": "running", "current_stage": "session", "error": None}
            )
        )

    def get_run_status(self, run_id: str) -> ResearchRun:
        return self._storage.get(ResearchRun, run_id)

    def _execute(self, run: ResearchRun) -> ResearchRun:
        self._replace_run(run)
        try:
            if run.workflow != "legacy_vibe":
                self._execute_brain(run)
                return self._mark_completed(run)
            session = self._ensure_session(run)
            vibe_result = self._ensure_vibe_result(run, session)
            reports = self._ensure_agent_reports(run, session, vibe_result)
            hypotheses = self._ensure_hypotheses(run, session, reports, vibe_result)
            debate = self._ensure_debate(run, session, reports, hypotheses)
            self._ensure_debate_statements(debate, reports, hypotheses, vibe_result)
            proposal = self._ensure_proposal(debate, hypotheses, vibe_result)
            self._ensure_risk_review(proposal, vibe_result)
            self._ensure_decision(proposal)
            return self._mark_completed(run)
        except Exception as exc:
            latest = self._storage.get(ResearchRun, run.run_id)
            failed = latest.model_copy(
                update={
                    "status": "failed",
                    "current_stage": "failed",
                    "failed_stage": latest.current_stage,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "finished_at": utc_now(),
                    "updated_at": utc_now(),
                }
            )
            self._replace_run(failed)
            raise

    def _execute_brain(self, run: ResearchRun) -> None:
        self._set_stage(run, "session")
        session = self._ensure_session(run, skip_evidence=True)
        if self._llm_adapter is None:
            msg = "Brain research workflow requires an LLM adapter"
            raise InvalidStateTransitionError(msg)
        if self._brain002_registry is None:
            msg = "Brain research workflow requires a BRAIN-002 registry"
            raise InvalidStateTransitionError(msg)
        self._set_stage_for_session(session.research_session_id, "evidence")
        result = BrainResearchPipeline(
            lifecycle=self._lifecycle,
            market_data_adapter=self._market_data_adapter,
            llm_adapter=self._llm_adapter,
            brain002_registry=self._brain002_registry,
            brain_evidence_repository=self._brain_evidence_repository,
        ).run(
            session=session,
            model=str(run.input_params["model"]),
            provider=str(run.input_params["provider"]),
        )
        updated = self._storage.get(ResearchRun, run.run_id).model_copy(
            update={
                "raw_output_reference": f"brain:{result.decision_result_id}",
                "updated_at": utc_now(),
            }
        )
        self._replace_run(updated)

    def _ensure_session(
        self,
        run: ResearchRun,
        *,
        skip_evidence: bool = False,
    ) -> ResearchSession:
        self._set_stage(run, "session")
        as_of = _param_datetime(run, "as_of")
        horizon_days = int(run.input_params["horizon_days"])
        existing = (
            self._storage.get(ResearchSession, run.research_session_id)
            if run.research_session_id
            else None
        )
        if existing is not None:
            return existing
        evidence_ids = () if skip_evidence else self._ensure_evidence_ids(run)
        try:
            session = ResearchSessionService(self._storage).create_session(
                watchlist_item_id=run.watchlist_item_id,
                horizon_days=horizon_days,
                as_of=as_of,
                evidence_ids=evidence_ids,
            )
        except DuplicateEntityError:
            duplicate_session = self._storage.find_active_research_session(
                run.watchlist_item_id,
                as_of,
                horizon_days,
            )
            if duplicate_session is None:
                raise
            session = duplicate_session
        updated = run.model_copy(
            update={
                "research_session_id": session.research_session_id,
                "updated_at": utc_now(),
            }
        )
        self._replace_run(updated)
        return session

    def _ensure_evidence_ids(self, run: ResearchRun) -> tuple[str, ...]:
        self._set_stage(run, "evidence")
        as_of = _param_datetime(run, "as_of")
        symbol = str(run.input_params["symbol"])
        start = as_of.date() - timedelta(days=7)
        imported = MarketEvidenceImportService(
            adapter=self._market_data_adapter,
            lifecycle=self._lifecycle,
        ).import_daily_bars(symbol, start, as_of.date(), Adjustment.NONE)
        if not imported.evidence_ids:
            msg = "ResearchRunner requires at least one market Evidence"
            raise InvalidStateTransitionError(msg)
        return tuple(imported.evidence_ids)

    def _ensure_vibe_result(
        self, run: ResearchRun, session: ResearchSession
    ) -> VibeTradingRawResult:
        self._set_stage(run, "vibe_research")
        result = self._vibe_trading_adapter.analyze(
            symbol=session.scope.symbol,
            market=session.scope.market,
            as_of=session.scope.as_of,
            horizon_days=session.scope.horizon_days,
            workflow=run.workflow,
            provider=str(run.input_params["provider"]),
            model=str(run.input_params["model"]),
        )
        updated = run.model_copy(
            update={
                "vibe_run_id": result.vibe_run_id,
                "raw_output_reference": result.raw_output_reference,
                "updated_at": utc_now(),
            }
        )
        self._replace_run(updated)
        return result

    def _ensure_agent_reports(
        self,
        run: ResearchRun,
        session: ResearchSession,
        result: VibeTradingRawResult,
    ) -> list[AgentReport]:
        self._set_stage(run, "agent_reports")
        confidence = _confidence_from_result(result)
        if confidence is None:
            msg = "Vibe-Trading output is missing structured confidence"
            raise InvalidStateTransitionError(msg)
        payloads = map_vibe_trading_result_to_agent_report_inputs(
            result,
            default_confidence=confidence,
        )
        if not payloads:
            msg = "Vibe-Trading output has no mappable analyst reports"
            raise InvalidStateTransitionError(msg)
        service = ResearchRecordService(self._storage)
        reports: list[AgentReport] = []
        for payload in payloads:
            existing = self._storage.find_active_agent_report(
                session.research_session_id,
                payload.role,
            )
            if existing is not None:
                reports.append(existing)
                continue
            reports.append(
                service.create_agent_report(
                    research_session_id=session.research_session_id,
                    role=payload.role,
                    summary=payload.summary,
                    stance=payload.stance,
                    confidence=payload.confidence or confidence,
                    evidence_ids=session.evidence_ids,
                    source="vibe_trading",
                    raw_reference=(
                        f"vibe:{result.vibe_run_id}:{result.workflow}:"
                        f"{payload.raw_reference}"
                    ),
                )
            )
        return reports

    def _ensure_hypotheses(
        self,
        run: ResearchRun,
        session: ResearchSession,
        reports: list[AgentReport],
        result: VibeTradingRawResult,
    ) -> list[Hypothesis]:
        self._set_stage(run, "hypotheses")
        existing = self._storage.list_hypotheses(
            research_session_id=session.research_session_id
        )
        service = ResearchRecordService(self._storage)
        hypotheses: list[Hypothesis] = list(existing)
        conclusion = _conclusion_from_result(result)
        confidence = _confidence_from_result(result)
        if confidence is None:
            msg = "Vibe-Trading output is missing structured confidence"
            raise InvalidStateTransitionError(msg)
        for report in reports:
            if any(report.report_id in h.supporting_report_ids for h in hypotheses):
                continue
            hypotheses.append(
                service.create_hypothesis(
                    research_session_id=session.research_session_id,
                    statement=(
                        f"{report.role.value} Agent 汇报支持"
                        f"{conclusion.value} 方向的研究假设"
                    ),
                    rationale=result.trader_plan
                    or result.risk_assessment.get("final_trade_decision", "")
                    or report.summary,
                    direction=conclusion.value,
                    horizon_days=session.scope.horizon_days,
                    confidence=confidence,
                    supporting_report_ids=(report.report_id,),
                    supporting_evidence_ids=session.evidence_ids,
                )
            )
        return hypotheses

    def _ensure_debate(
        self,
        run: ResearchRun,
        session: ResearchSession,
        reports: list[AgentReport],
        hypotheses: list[Hypothesis],
    ) -> DebateRecord:
        self._set_stage(run, "debate")
        report_ids = {report.report_id for report in reports}
        hypothesis_ids = {hypothesis.hypothesis_id for hypothesis in hypotheses}
        for debate in self._storage.list_debates(
            research_session_id=session.research_session_id
        ):
            if (
                set(debate.report_ids) == report_ids
                and set(debate.hypothesis_ids) == hypothesis_ids
            ):
                return debate
        return DebateService(self._storage).create_debate(
            research_session_id=session.research_session_id
        )

    def _ensure_debate_statements(
        self,
        debate: DebateRecord,
        reports: list[AgentReport],
        hypotheses: list[Hypothesis],
        result: VibeTradingRawResult,
    ) -> None:
        service = DebateService(self._storage)
        hypothesis_by_report = {
            hypothesis.supporting_report_ids[0]: hypothesis
            for hypothesis in hypotheses
            if hypothesis.supporting_report_ids
        }
        for report in reports:
            hypothesis = hypothesis_by_report.get(report.report_id)
            if hypothesis is None:
                continue
            if (
                self._storage.get_debate_statement(
                    debate.debate_id,
                    report.report_id,
                    hypothesis.hypothesis_id,
                )
                is not None
            ):
                continue
            service.add_debate_statement(
                debate_id=debate.debate_id,
                agent_report_id=report.report_id,
                hypothesis_id=hypothesis.hypothesis_id,
                stance=DebateStance.SUPPORT,
                reasoning=result.investment_debate.get("judge_decision")
                or result.trader_plan
                or report.summary,
                evidence_ids=report.evidence_ids,
                confidence_before=report.confidence,
                confidence_after=hypothesis.confidence,
            )

    def _ensure_proposal(
        self,
        debate: DebateRecord,
        hypotheses: list[Hypothesis],
        result: VibeTradingRawResult,
    ) -> DecisionProposal:
        self._set_stage_for_session(debate.research_session_id, "proposal")
        existing = self._storage.get_decision_proposal_by_debate_id(debate.debate_id)
        if existing is not None:
            return existing
        evidence_ids = tuple(
            dict.fromkeys(
                evidence_id
                for hypothesis in hypotheses
                for evidence_id in hypothesis.supporting_evidence_ids
            )
        )
        return DebateService(self._storage).assemble_decision_proposal(
            debate_id=debate.debate_id,
            conclusion=_conclusion_from_result(result),
            confidence=_confidence_from_result(result) or 0,
            thesis=result.trader_plan
            or result.risk_assessment.get("final_trade_decision", "")
            or "Vibe-Trading structured research proposal",
            supporting_hypothesis_ids=tuple(h.hypothesis_id for h in hypotheses),
            rejected_hypothesis_ids=(),
            evidence_ids=evidence_ids,
            risk_notes=tuple(result.risk_assessment.values()),
        )

    def _ensure_risk_review(
        self, proposal: DecisionProposal, result: VibeTradingRawResult
    ) -> RiskReview:
        self._set_stage_for_debate(proposal.debate_id, "risk_review")
        existing = self._storage.get_risk_review_by_proposal_id(proposal.proposal_id)
        if existing is not None:
            return existing
        return DebateService(self._storage).submit_risk_review(
            proposal_id=proposal.proposal_id,
            verdict=RiskVerdict.APPROVE,
            final_conclusion=proposal.conclusion,
            final_confidence=proposal.confidence,
            reasons=(
                result.risk_assessment.get("risk_judge_decision")
                or result.risk_assessment.get("final_trade_decision")
                or "Vibe-Trading risk assessment approved the proposal",
            ),
        )

    def _ensure_decision(self, proposal: DecisionProposal) -> DecisionAssemblyRecord:
        self._set_stage_for_debate(proposal.debate_id, "decision")
        return DebateService(self._storage).finalize_decision(proposal.proposal_id)

    def _find_or_create_run(self, **params: Any) -> ResearchRun:
        input_params = {
            "horizon_days": params["horizon_days"],
            "as_of": params["as_of"].isoformat(),
            "workflow": params["workflow"],
            "provider": params["provider"],
            "model": params["model"],
        }
        watchlist = self._storage.get(WatchlistItem, params["watchlist_item_id"])
        input_params["symbol"] = watchlist.symbol
        for run in self._storage.list(ResearchRun):
            if (
                run.watchlist_item_id == params["watchlist_item_id"]
                and run.workflow == params["workflow"]
                and run.input_params == input_params
            ):
                return run
        run = ResearchRun(
            watchlist_item_id=params["watchlist_item_id"],
            symbol=watchlist.symbol,
            research_window_key=(
                f"{watchlist.market}:{watchlist.symbol}:"
                f"{params['horizon_days']}:{params['as_of'].isoformat()}"
            ),
            workflow=params["workflow"],
            input_params=input_params,
        )
        self._storage.save(run)
        return run

    def _mark_completed(self, run: ResearchRun) -> ResearchRun:
        latest = self._storage.get(ResearchRun, run.run_id)
        completed = latest.model_copy(
            update={
                "status": "completed",
                "current_stage": "completed",
                "error": None,
                "failed_stage": None,
                "error_type": None,
                "finished_at": utc_now(),
                "updated_at": utc_now(),
            }
        )
        self._replace_run(completed)
        return completed

    def _set_stage(self, run: ResearchRun, stage: ResearchRunStage) -> None:
        latest = self._storage.get(ResearchRun, run.run_id)
        if latest.current_stage == stage and latest.status == "running":
            return
        self._replace_run(
            latest.model_copy(
                update={
                    "current_stage": stage,
                    "status": "running",
                    "updated_at": utc_now(),
                }
            )
        )

    def _set_stage_for_session(
        self, research_session_id: str, stage: ResearchRunStage
    ) -> None:
        for run in self._storage.list(ResearchRun):
            if run.research_session_id == research_session_id:
                self._set_stage(run, stage)
                return

    def _set_stage_for_debate(self, debate_id: str, stage: ResearchRunStage) -> None:
        debate = self._storage.get(DebateRecord, debate_id)
        self._set_stage_for_session(debate.research_session_id, stage)

    def _replace_run(self, run: ResearchRun) -> None:
        if self._storage.exists(ResearchRun, run.run_id):
            self._storage.replace(run)
        else:
            self._storage.save(run)


def _param_datetime(run: ResearchRun, name: str) -> datetime:
    value = datetime.fromisoformat(str(run.input_params[name]))
    if value.tzinfo is None:
        msg = f"{name} must be timezone-aware"
        raise ValueError(msg)
    return value


def _confidence_from_result(result: VibeTradingRawResult) -> float | None:
    if not result.final_decision:
        return None
    confidence = result.final_decision.get("confidence")
    return float(confidence) if confidence is not None else None


def _conclusion_from_result(result: VibeTradingRawResult) -> ResearchConclusion:
    if not result.final_decision:
        msg = "Vibe-Trading output is missing structured final_decision"
        raise InvalidStateTransitionError(msg)
    signal = str(result.final_decision.get("signal", "")).strip().lower()
    mapping = {
        "buy": ResearchConclusion.BUY,
        "sell": ResearchConclusion.SELL,
        "hold": ResearchConclusion.HOLD,
        "watch": ResearchConclusion.WATCH,
        "no_trade": ResearchConclusion.NO_TRADE,
        "no trade": ResearchConclusion.NO_TRADE,
        "invalid": ResearchConclusion.INVALID,
    }
    try:
        return mapping[signal]
    except KeyError as exc:
        msg = f"unsupported Vibe-Trading final signal: {signal}"
        raise InvalidStateTransitionError(msg) from exc
