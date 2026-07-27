from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, cast

from aios.adapters.llm import LLMAdapter
from aios.adapters.market_data import MarketDataAdapter
from aios.application.brain002 import (
    ExecutableSkill,
    SkillExecutor,
    SkillRegistry,
    SkillSelector,
)
from aios.application.brain003 import DiscussionService
from aios.application.brain004 import DecisionService
from aios.application.brain_risk_review import RiskReviewService
from aios.application.evidence_bridge import CoreEvidenceBridge
from aios.application.formal_decision import FormalDecisionService
from aios.application.market_evidence import MarketEvidenceImportService
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.application.research_records import ResearchRecordService
from aios.integrations.evidence import Evidence as BrainEvidence
from aios.kernel.brain002 import AnalysisTask, SkillExecution, SkillResult
from aios.kernel.brain003 import DiscussionExecution, DiscussionResult
from aios.kernel.brain004 import DecisionExecution, DecisionResult
from aios.kernel.debate import DecisionAssemblyRecord, RiskReview
from aios.kernel.decision import Decision
from aios.kernel.enums import AgentRole, ResearchSessionStatus
from aios.kernel.errors import InvalidStateTransitionError
from aios.kernel.evidence import Evidence
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.skills.brain002 import (
    AnnouncementRiskSkill,
    MarketSentimentSkill,
    PolicyImpactSkill,
    SectorStrengthSkill,
    TechnicalTrendSkill,
)
from aios.workflows.decision_lifecycle import DecisionLifecycleService


class BrainEvidenceRepository(Protocol):
    def query(
        self,
        *,
        source: str | None = None,
        source_type: str | None = None,
        fingerprint: str | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        collected_from: datetime | None = None,
        collected_to: datetime | None = None,
        available_before: datetime | None = None,
        sort_by: Literal[
            "published_at",
            "collected_at",
            "available_at",
        ] = "collected_at",
        sort_order: Literal["asc", "desc"] = "asc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BrainEvidence], int]:
        """Return persisted BRAIN-001 Evidence records."""


@dataclass(frozen=True)
class BrainResearchPipelineResult:
    evidence_ids: tuple[str, ...]
    hypothesis_ids: tuple[str, ...]
    skill_execution_ids: tuple[str, ...]
    skill_result_ids: tuple[str, ...]
    discussion_execution_id: str
    discussion_result_id: str
    decision_execution_id: str
    decision_result_id: str
    risk_review_id: str
    decision_id: str
    assembly_id: str


class BrainResearchPipeline:
    def __init__(
        self,
        *,
        lifecycle: DecisionLifecycleService,
        market_data_adapter: MarketDataAdapter,
        llm_adapter: LLMAdapter,
        brain002_registry: SkillRegistry,
        brain_evidence_repository: BrainEvidenceRepository | None = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._storage = lifecycle.storage
        self._market_data_adapter = market_data_adapter
        self._llm_adapter = llm_adapter
        self._registry = brain002_registry
        self._brain_evidence_repository = brain_evidence_repository

    def run(
        self,
        *,
        session: ResearchSession,
        model: str,
        provider: str,
    ) -> BrainResearchPipelineResult:
        try:
            return self._run(session=session, model=model, provider=provider)
        except Exception as exc:
            self._record_failure(session, exc)
            raise

    def _run(
        self,
        *,
        session: ResearchSession,
        model: str,
        provider: str,
    ) -> BrainResearchPipelineResult:
        existing = self._existing_assembly(session)
        if existing is not None:
            return self._result_from_existing(existing)

        evidence = self._ensure_evidence(session)
        seed_report = self._ensure_seed_report(session, evidence)
        hypotheses = self._ensure_hypotheses(session, evidence, seed_report)
        self._transition_session(
            session,
            ResearchSessionStatus.HYPOTHESIS_READY,
            "hypotheses are ready",
        )
        task = self._ensure_analysis_task(session, evidence, hypotheses)
        self._transition_session(
            session,
            ResearchSessionStatus.SKILLS_RUNNING,
            "skill analysis started",
        )
        skill_executions, skill_results = self._run_skills(task, evidence, model)
        if not skill_results:
            msg = "BrainResearchPipeline requires at least one successful SkillResult"
            raise InvalidStateTransitionError(msg)
        discussion_execution, discussion = self._run_discussion(
            task,
            skill_results,
            evidence,
            model,
        )
        self._transition_session(
            session,
            ResearchSessionStatus.DISCUSSION_READY,
            "discussion is ready",
        )
        decision_execution, decision_result = self._run_decision(
            task,
            skill_results,
            discussion,
            evidence,
            model,
        )
        self._transition_session(
            session,
            ResearchSessionStatus.RISK_REVIEW,
            "risk review started",
        )
        risk_review = self._ensure_risk_review(
            session=session,
            decision_result=decision_result,
            discussion=discussion,
            skill_results=skill_results,
            evidence=evidence,
        )
        decision = self._create_decision(
            session=session,
            decision_result=decision_result,
            risk_review=risk_review,
            discussion=discussion,
            skill_results=skill_results,
            evidence=evidence,
            model=model,
            provider=provider,
        )
        self._transition_session(
            session,
            ResearchSessionStatus.DECISION_READY,
            "formal decision is ready",
        )
        assembly = self._create_assembly(
            session=session,
            decision=decision,
            decision_result=decision_result,
            risk_review=risk_review,
            skill_results=skill_results,
            hypotheses=hypotheses,
        )
        return BrainResearchPipelineResult(
            evidence_ids=tuple(item.evidence_id for item in evidence),
            hypothesis_ids=tuple(item.hypothesis_id for item in hypotheses),
            skill_execution_ids=tuple(item.execution_id for item in skill_executions),
            skill_result_ids=tuple(item.result_id for item in skill_results),
            discussion_execution_id=discussion_execution.discussion_execution_id,
            discussion_result_id=discussion.discussion_result_id,
            decision_execution_id=decision_execution.decision_execution_id,
            decision_result_id=decision_result.decision_result_id,
            risk_review_id=risk_review.risk_review_id,
            decision_id=decision.decision_id,
            assembly_id=assembly.assembly_id,
        )

    def _ensure_evidence(self, session: ResearchSession) -> tuple[Evidence, ...]:
        existing = tuple(
            self._storage.get(Evidence, evidence_id)
            for evidence_id in session.evidence_ids
        )
        if existing:
            self._transition_evidence_ready(session)
            return existing

        collecting = self._transition_session(
            session,
            ResearchSessionStatus.COLLECTING_EVIDENCE,
            "evidence collection started",
        )
        external = self._external_evidence(session)
        market = self._market_evidence(session)
        combined = tuple(dict.fromkeys((*external, *market)))
        if not combined:
            msg = "BrainResearchPipeline requires at least one Evidence"
            raise InvalidStateTransitionError(msg)
        updated = collecting.model_copy(update={"evidence_ids": combined})
        self._storage.replace(updated)
        self._transition_evidence_ready(updated)
        return tuple(
            self._storage.get(Evidence, evidence_id) for evidence_id in combined
        )

    def _transition_evidence_ready(self, session: ResearchSession) -> None:
        latest = self._storage.get(ResearchSession, session.research_session_id)
        if latest.status in {
            ResearchSessionStatus.CREATED,
            ResearchSessionStatus.COLLECTING_EVIDENCE,
        }:
            self._transition_session(
                latest,
                ResearchSessionStatus.EVIDENCE_READY,
                "evidence is ready",
            )

    def _transition_session(
        self,
        session: ResearchSession,
        to_state: ResearchSessionStatus,
        reason: str,
    ) -> ResearchSession:
        return ResearchLifecycleService(self._storage).transition(
            session.research_session_id,
            to_state,
            reason=reason,
        )

    def _external_evidence(self, session: ResearchSession) -> tuple[str, ...]:
        if self._brain_evidence_repository is None:
            return ()
        records, _ = self._brain_evidence_repository.query(
            available_before=session.scope.as_of,
            limit=100,
            offset=0,
        )
        bridge = CoreEvidenceBridge(self._storage)
        ids: list[str] = []
        for record in records:
            converted = bridge.ensure_core_evidence(
                record,
                default_symbol=session.scope.symbol,
            )
            ids.append(converted.evidence_id)
        return tuple(dict.fromkeys(ids))

    def _market_evidence(self, session: ResearchSession) -> tuple[str, ...]:
        result = MarketEvidenceImportService(
            adapter=self._market_data_adapter,
            lifecycle=self._lifecycle,
        ).import_daily_bars(
            session.scope.symbol,
            session.scope.as_of.date(),
            session.scope.as_of.date(),
            "none",
        )
        return tuple(result.evidence_ids)

    def _ensure_seed_report(
        self,
        session: ResearchSession,
        evidence: tuple[Evidence, ...],
    ) -> AgentReport:
        existing = self._storage.find_active_agent_report(
            session.research_session_id,
            AgentRole.NEWS,
        )
        if existing is not None and existing.source == "brain001_evidence_seed":
            return existing
        return ResearchRecordService(self._storage).create_agent_report(
            research_session_id=session.research_session_id,
            role=AgentRole.NEWS,
            summary=_hypothesis_summary(evidence),
            stance="watch",
            confidence=0.5,
            evidence_ids=tuple(item.evidence_id for item in evidence),
            source="brain001_evidence_seed",
            raw_reference="brain001:persisted-evidence",
        )

    def _ensure_hypotheses(
        self,
        session: ResearchSession,
        evidence: tuple[Evidence, ...],
        seed_report: AgentReport,
    ) -> tuple[Hypothesis, ...]:
        existing = self._storage.list_hypotheses(
            research_session_id=session.research_session_id
        )
        if existing:
            return tuple(existing)
        external = tuple(
            item for item in evidence if item.evidence_type != "market_daily_bar"
        )
        source_evidence = external or evidence
        hypothesis = ResearchRecordService(self._storage).create_hypothesis(
            research_session_id=session.research_session_id,
            statement=_hypothesis_statement(source_evidence),
            rationale=_hypothesis_summary(source_evidence),
            direction="neutral",
            horizon_days=session.scope.horizon_days,
            confidence=0.5,
            supporting_report_ids=(seed_report.report_id,),
            supporting_evidence_ids=tuple(item.evidence_id for item in source_evidence),
        )
        return (hypothesis,)

    def _ensure_analysis_task(
        self,
        session: ResearchSession,
        evidence: tuple[Evidence, ...],
        hypotheses: tuple[Hypothesis, ...],
    ) -> AnalysisTask:
        for task in self._storage.list(AnalysisTask):
            if (
                task.symbol == session.scope.symbol
                and task.as_of == session.scope.as_of
                and task.evidence_ids == tuple(item.evidence_id for item in evidence)
            ):
                return task
        task = AnalysisTask(
            symbol=session.scope.symbol,
            market=_brain_market(session.scope.market),
            asset_type="stock",
            horizon=_brain_horizon(session.scope.horizon_days),
            as_of=session.scope.as_of,
            evidence_ids=tuple(item.evidence_id for item in evidence),
            user_constraints={
                "hypotheses": [
                    {
                        "hypothesis_id": item.hypothesis_id,
                        "statement": item.statement,
                        "rationale": item.rationale,
                        "supporting_evidence_ids": list(item.supporting_evidence_ids),
                    }
                    for item in hypotheses
                ],
                "hypothesis_lifecycle": "evidence_first",
            },
        )
        self._storage.save(task)
        return task

    def _run_skills(
        self,
        task: AnalysisTask,
        evidence: tuple[Evidence, ...],
        model: str,
    ) -> tuple[tuple[SkillExecution, ...], tuple[SkillResult, ...]]:
        existing_executions = [
            item
            for item in self._storage.list(SkillExecution)
            if item.task_id == task.task_id
        ]
        if existing_executions:
            execution_ids = {item.execution_id for item in existing_executions}
            results = [
                result
                for result in self._storage.list(SkillResult)
                if result.execution_id in execution_ids
            ]
            return tuple(existing_executions), tuple(results)
        selection = SkillSelector(self._registry).select(task=task, evidence=evidence)
        skills_by_id = _mvp_skills_by_id()
        selected = tuple(
            skills_by_id[skill_id]
            for skill_id in selection.selected_skill_ids
            if skill_id in skills_by_id
        )
        outcome = SkillExecutor(llm=self._llm_adapter, model=model).execute(
            task=task,
            skills=selected,
            evidence=evidence,
        )
        for execution in outcome.executions:
            self._storage.save(execution)
        for result in outcome.results:
            self._storage.save(result)
        return outcome.executions, outcome.results

    def _run_discussion(
        self,
        task: AnalysisTask,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
        model: str,
    ) -> tuple[DiscussionExecution, DiscussionResult]:
        for result in self._storage.list(DiscussionResult):
            if result.task_id == task.task_id:
                execution = self._storage.get(
                    DiscussionExecution,
                    result.discussion_execution_id,
                )
                return execution, result
        outcome = DiscussionService(llm=self._llm_adapter, model=model).discuss(
            task=task,
            skill_results=skill_results,
            evidence=evidence,
        )
        self._storage.save(outcome.execution)
        if outcome.result is None:
            msg = outcome.execution.error or "DiscussionService failed"
            raise InvalidStateTransitionError(msg)
        self._storage.save(outcome.result)
        return outcome.execution, outcome.result

    def _run_decision(
        self,
        task: AnalysisTask,
        skill_results: tuple[SkillResult, ...],
        discussion: DiscussionResult,
        evidence: tuple[Evidence, ...],
        model: str,
    ) -> tuple[DecisionExecution, DecisionResult]:
        for result in self._storage.list(DecisionResult):
            if result.task_id == task.task_id:
                execution = self._storage.get(
                    DecisionExecution,
                    result.decision_execution_id,
                )
                return execution, result
        outcome = DecisionService(llm=self._llm_adapter, model=model).decide(
            task=task,
            skill_results=skill_results,
            discussion_result=discussion,
            evidence=evidence,
        )
        self._storage.save(outcome.execution)
        if outcome.result is None:
            msg = outcome.execution.error or "DecisionService failed"
            raise InvalidStateTransitionError(msg)
        self._storage.save(outcome.result)
        return outcome.execution, outcome.result

    def _ensure_risk_review(
        self,
        *,
        session: ResearchSession,
        decision_result: DecisionResult,
        discussion: DiscussionResult,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> RiskReview:
        return RiskReviewService(self._storage).submit_brain_risk_review(
            session=session,
            decision_result=decision_result,
            discussion_result=discussion,
            skill_results=skill_results,
            evidence=evidence,
        )

    def _create_decision(
        self,
        *,
        session: ResearchSession,
        decision_result: DecisionResult,
        risk_review: RiskReview,
        discussion: DiscussionResult,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
        model: str,
        provider: str,
    ) -> Decision:
        return FormalDecisionService(lifecycle=self._lifecycle).assemble(
            session=session,
            decision_result=decision_result,
            risk_review=risk_review,
            discussion_result=discussion,
            skill_results=skill_results,
            evidence=evidence,
            model=model,
            provider=provider,
        )

    def _create_assembly(
        self,
        *,
        session: ResearchSession,
        decision: Decision,
        decision_result: DecisionResult,
        risk_review: RiskReview,
        skill_results: tuple[SkillResult, ...],
        hypotheses: tuple[Hypothesis, ...],
    ) -> DecisionAssemblyRecord:
        existing = self._existing_assembly(session)
        if existing is not None:
            return existing
        if not risk_review.risk_review_id:
            msg = "BRAIN DecisionAssemblyRecord requires RiskReview"
            raise InvalidStateTransitionError(msg)
        assembly = DecisionAssemblyRecord(
            research_session_id=session.research_session_id,
            debate_id=None,
            proposal_id=None,
            risk_review_id=risk_review.risk_review_id,
            decision_id=decision.decision_id,
            conclusion=risk_review.final_conclusion,
            report_ids=tuple(item.result_id for item in skill_results),
            hypothesis_ids=tuple(item.hypothesis_id for item in hypotheses),
            evidence_ids=tuple(decision_result.evidence_refs) or decision.evidence_ids,
            created_at=session.scope.as_of,
        )
        self._storage.save(assembly)
        return assembly

    def _existing_assembly(
        self,
        session: ResearchSession,
    ) -> DecisionAssemblyRecord | None:
        for assembly in self._storage.list(DecisionAssemblyRecord):
            if assembly.research_session_id == session.research_session_id:
                return assembly
        return None

    def _result_from_existing(
        self,
        assembly: DecisionAssemblyRecord,
    ) -> BrainResearchPipelineResult:
        skill_results = tuple(
            self._storage.get(SkillResult, result_id)
            for result_id in assembly.report_ids
        )
        decision_result = _matching_decision_result(self._lifecycle, skill_results)
        if decision_result is None:
            msg = f"DecisionAssemblyRecord {assembly.assembly_id} has no DecisionResult"
            raise InvalidStateTransitionError(msg)
        discussion = self._storage.get(
            DiscussionResult,
            decision_result.discussion_result_id,
        )
        decision_execution = self._storage.get(
            DecisionExecution,
            decision_result.decision_execution_id,
        )
        discussion_execution = self._storage.get(
            DiscussionExecution,
            discussion.discussion_execution_id,
        )
        return BrainResearchPipelineResult(
            evidence_ids=assembly.evidence_ids,
            hypothesis_ids=assembly.hypothesis_ids,
            skill_execution_ids=tuple(
                item.execution_id
                for item in self._storage.list(SkillExecution)
                if item.task_id == decision_result.task_id
            ),
            skill_result_ids=decision_result.skill_result_ids,
            discussion_execution_id=discussion_execution.discussion_execution_id,
            discussion_result_id=discussion.discussion_result_id,
            decision_execution_id=decision_execution.decision_execution_id,
            decision_result_id=decision_result.decision_result_id,
            risk_review_id=assembly.risk_review_id or "",
            decision_id=assembly.decision_id,
            assembly_id=assembly.assembly_id,
        )

    def _record_failure(self, session: ResearchSession, exc: Exception) -> None:
        latest = self._storage.get(ResearchSession, session.research_session_id)
        if latest.status is ResearchSessionStatus.FAILED:
            return
        ResearchLifecycleService(self._storage).transition(
            latest,
            ResearchSessionStatus.FAILED,
            reason="brain research pipeline failed",
            failure_stage=latest.status.value,
            failure_error=str(exc),
            increment_retry=True,
        )


def _hypothesis_statement(evidence: tuple[Evidence, ...]) -> str:
    preferred = evidence[0]
    if preferred.evidence_type == "policy":
        return f"Policy evidence may affect {', '.join(preferred.symbols)}"
    if preferred.evidence_type == "company_announcement":
        return f"Announcement evidence may affect {', '.join(preferred.symbols)}"
    if preferred.evidence_type == "market_daily_bar":
        return f"Market context may affect {', '.join(preferred.symbols)}"
    return f"External evidence may affect {', '.join(preferred.symbols)}"


def _hypothesis_summary(evidence: tuple[Evidence, ...]) -> str:
    return " | ".join(item.summary for item in evidence[:3])


def _brain_market(market: str) -> str:
    normalized = market.strip().lower()
    if normalized in {"cn", "cn_a", "a_share"}:
        return "cn"
    if normalized in {"us", "usa"}:
        return "us"
    return normalized


def _brain_horizon(horizon_days: int) -> str:
    if horizon_days <= 1:
        return "intraday"
    if horizon_days <= 7:
        return "swing"
    return "position"


def _matching_decision_result(
    lifecycle: DecisionLifecycleService,
    skill_results: tuple[SkillResult, ...],
) -> DecisionResult | None:
    skill_result_ids = {result.result_id for result in skill_results}
    matches = [
        result
        for result in lifecycle.list_entities(DecisionResult)
        if set(result.skill_result_ids) == skill_result_ids
    ]
    return matches[-1] if matches else None


def _mvp_skills_by_id() -> dict[str, ExecutableSkill]:
    skills = cast(
        "tuple[ExecutableSkill, ...]",
        (
            TechnicalTrendSkill(),
            SectorStrengthSkill(),
            PolicyImpactSkill(),
            AnnouncementRiskSkill(),
            MarketSentimentSkill(),
        ),
    )
    return {skill.definition.skill_id: skill for skill in skills}
