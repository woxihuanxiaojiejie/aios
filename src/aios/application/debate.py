from __future__ import annotations

from datetime import UTC, datetime

from aios.adapters.storage import Storage
from aios.kernel.base import utc_now
from aios.kernel.debate import (
    DebateRecord,
    DebateStatement,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    AgentReportStatus,
    DebateStance,
    DebateStatus,
    DecisionStatus,
    ExperimentStatus,
    HypothesisStatus,
    ResearchConclusion,
    ResearchSessionStatus,
    RiskVerdict,
)
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
    ReferenceIntegrityError,
)
from aios.kernel.experiment import Experiment
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis


class DebateService:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def create_debate(self, *, research_session_id: str) -> DebateRecord:
        session = self._get_open_session(research_session_id)
        reports = self._storage.list_agent_reports(
            research_session_id=research_session_id,
            status=AgentReportStatus.ACTIVE,
        )
        hypotheses = [
            hypothesis
            for hypothesis in self._storage.list_hypotheses(
                research_session_id=research_session_id
            )
            if hypothesis.status
            in {HypothesisStatus.PROPOSED, HypothesisStatus.VALIDATED}
        ]
        if not reports:
            msg = "Debate requires at least one active AgentReport"
            raise InvalidStateTransitionError(msg)
        if not hypotheses:
            msg = "Debate requires at least one proposed or validated Hypothesis"
            raise InvalidStateTransitionError(msg)
        debate = DebateRecord(
            research_session_id=session.research_session_id,
            report_ids=tuple(report.report_id for report in reports),
            hypothesis_ids=tuple(hypothesis.hypothesis_id for hypothesis in hypotheses),
        )
        self._storage.save(debate)
        return debate

    def get_debate(self, debate_id: str) -> DebateRecord:
        return self._storage.get(DebateRecord, debate_id)

    def list_debates(
        self, *, research_session_id: str | None = None
    ) -> list[DebateRecord]:
        return self._storage.list_debates(research_session_id=research_session_id)

    def add_debate_statement(
        self,
        *,
        debate_id: str,
        agent_report_id: str,
        hypothesis_id: str,
        stance: DebateStance,
        reasoning: str,
        evidence_ids: list[str] | tuple[str, ...],
        confidence_before: float,
        confidence_after: float,
    ) -> DebateStatement:
        debate = self._storage.get(DebateRecord, debate_id)
        if debate.status is not DebateStatus.OPEN:
            msg = f"Debate {debate_id} is not open"
            raise InvalidStateTransitionError(msg)
        if agent_report_id not in debate.report_ids:
            msg = "DebateStatement AgentReport must be frozen on Debate"
            raise ReferenceIntegrityError(msg)
        if hypothesis_id not in debate.hypothesis_ids:
            msg = "DebateStatement Hypothesis must be frozen on Debate"
            raise ReferenceIntegrityError(msg)
        self._validate_debate_statement_references(
            debate,
            agent_report_id,
            hypothesis_id,
        )
        if (
            self._storage.get_debate_statement(
                debate_id, agent_report_id, hypothesis_id
            )
            is not None
        ):
            msg = "DebateStatement already exists for report and hypothesis"
            raise DuplicateEntityError(msg)
        session = self._storage.get(ResearchSession, debate.research_session_id)
        self._validate_session_evidence(session, tuple(evidence_ids))
        statement = DebateStatement(
            debate_id=debate_id,
            agent_report_id=agent_report_id,
            hypothesis_id=hypothesis_id,
            stance=stance,
            reasoning=reasoning,
            evidence_ids=tuple(evidence_ids),
            confidence_before=confidence_before,
            confidence_after=confidence_after,
        )
        self._storage.save(statement)
        return statement

    def assemble_decision_proposal(
        self,
        *,
        debate_id: str,
        conclusion: ResearchConclusion,
        confidence: float,
        thesis: str,
        supporting_hypothesis_ids: list[str] | tuple[str, ...],
        rejected_hypothesis_ids: list[str] | tuple[str, ...],
        evidence_ids: list[str] | tuple[str, ...],
        risk_notes: list[str] | tuple[str, ...],
    ) -> DecisionProposal:
        debate = self._storage.get(DebateRecord, debate_id)
        if debate.status is DebateStatus.CANCELLED:
            msg = f"Debate {debate_id} is cancelled"
            raise InvalidStateTransitionError(msg)
        if self._storage.get_decision_proposal_by_debate_id(debate_id) is not None:
            msg = f"Debate {debate_id} already has a DecisionProposal"
            raise DuplicateEntityError(msg)
        hypothesis_ids = set(supporting_hypothesis_ids) | set(rejected_hypothesis_ids)
        if not hypothesis_ids.issubset(set(debate.hypothesis_ids)):
            msg = "DecisionProposal hypotheses must be frozen on Debate"
            raise ReferenceIntegrityError(msg)
        self._validate_debate_hypotheses(debate, hypothesis_ids)
        session = self._storage.get(ResearchSession, debate.research_session_id)
        self._validate_session_evidence(session, tuple(evidence_ids))
        proposal = DecisionProposal(
            debate_id=debate_id,
            conclusion=conclusion,
            confidence=confidence,
            thesis=thesis,
            supporting_hypothesis_ids=tuple(supporting_hypothesis_ids),
            rejected_hypothesis_ids=tuple(rejected_hypothesis_ids),
            evidence_ids=tuple(evidence_ids),
            risk_notes=tuple(risk_notes),
        )
        self._storage.save(proposal)
        assembled = debate.model_copy(
            update={"status": DebateStatus.ASSEMBLED, "updated_at": utc_now()}
        )
        self._storage.replace(assembled)
        return proposal

    def submit_risk_review(
        self,
        *,
        proposal_id: str,
        verdict: RiskVerdict,
        final_conclusion: ResearchConclusion,
        final_confidence: float,
        reasons: list[str] | tuple[str, ...],
    ) -> RiskReview:
        proposal = self._storage.get(DecisionProposal, proposal_id)
        if self._storage.get_risk_review_by_proposal_id(proposal_id) is not None:
            msg = f"DecisionProposal {proposal_id} already has a RiskReview"
            raise DuplicateEntityError(msg)
        self._validate_risk(proposal, verdict, final_conclusion, final_confidence)
        review = RiskReview(
            proposal_id=proposal_id,
            verdict=verdict,
            final_conclusion=final_conclusion,
            final_confidence=final_confidence,
            reasons=tuple(reasons),
        )
        self._storage.save(review)
        return review

    def finalize_decision(self, proposal_id: str) -> DecisionAssemblyRecord:
        existing = self._storage.get_decision_assembly_by_proposal_id(proposal_id)
        if existing is not None:
            return existing
        proposal = self._storage.get(DecisionProposal, proposal_id)
        risk = self._storage.get_risk_review_by_proposal_id(proposal_id)
        if risk is None:
            msg = "DecisionProposal must have RiskReview before finalization"
            raise InvalidStateTransitionError(msg)
        debate = self._storage.get(DebateRecord, proposal.debate_id)
        session = self._storage.get(ResearchSession, debate.research_session_id)
        if not proposal.evidence_ids:
            msg = "final Decision requires at least one Evidence reference"
            raise ReferenceIntegrityError(msg)
        experiment_id = session.experiment_id or self._ensure_assembly_experiment(
            session, proposal
        )
        decision = Decision(
            experiment_id=experiment_id,
            symbol=session.scope.symbol,
            action=_action_for_conclusion(risk.final_conclusion),
            horizon=f"{session.scope.horizon_days}d",
            confidence=risk.final_confidence,
            expected_return=0.0,
            max_expected_loss=0.0,
            evidence_ids=proposal.evidence_ids,
            reasoning_summary=proposal.thesis,
            status=(
                DecisionStatus.INVALID
                if risk.final_conclusion is ResearchConclusion.INVALID
                else DecisionStatus.PROPOSED
            ),
            created_at=utc_now(),
            valid_until=session.scope.valid_until,
        )
        self._storage.save(decision)
        assembly = DecisionAssemblyRecord(
            research_session_id=session.research_session_id,
            debate_id=debate.debate_id,
            proposal_id=proposal.proposal_id,
            risk_review_id=risk.risk_review_id,
            decision_id=decision.decision_id,
            conclusion=risk.final_conclusion,
            report_ids=debate.report_ids,
            hypothesis_ids=debate.hypothesis_ids,
            evidence_ids=proposal.evidence_ids,
        )
        self._storage.save(assembly)
        finalized = debate.model_copy(
            update={"final_decision_id": decision.decision_id}
        )
        self._storage.replace(finalized)
        return assembly

    def _get_open_session(self, research_session_id: str) -> ResearchSession:
        session = self._storage.get(ResearchSession, research_session_id)
        if session.status is ResearchSessionStatus.CANCELLED:
            msg = f"ResearchSession {research_session_id} is cancelled"
            raise InvalidStateTransitionError(msg)
        return session

    def _validate_session_evidence(
        self, session: ResearchSession, evidence_ids: tuple[str, ...]
    ) -> None:
        if not set(evidence_ids).issubset(set(session.evidence_ids)):
            msg = "Evidence IDs must be frozen on ResearchSession"
            raise ReferenceIntegrityError(msg)

    def _validate_debate_statement_references(
        self,
        debate: DebateRecord,
        agent_report_id: str,
        hypothesis_id: str,
    ) -> None:
        report = self._storage.get(AgentReport, agent_report_id)
        if report.research_session_id != debate.research_session_id:
            msg = "DebateStatement AgentReport must belong to Debate ResearchSession"
            raise ReferenceIntegrityError(msg)
        self._validate_debate_hypotheses(debate, {hypothesis_id})

    def _validate_debate_hypotheses(
        self,
        debate: DebateRecord,
        hypothesis_ids: set[str],
    ) -> None:
        for hypothesis_id in hypothesis_ids:
            hypothesis = self._storage.get(Hypothesis, hypothesis_id)
            if hypothesis.research_session_id != debate.research_session_id:
                msg = "Debate Hypothesis must belong to Debate ResearchSession"
                raise ReferenceIntegrityError(msg)

    def _ensure_assembly_experiment(
        self, session: ResearchSession, proposal: DecisionProposal
    ) -> str:
        experiment = Experiment(
            name=f"decision-assembly-{session.research_session_id}",
            model="aios-structured-input",
            prompt_version="decision-assembly-v1",
            agent_config_version="manual-debate-risk-review",
            dataset_snapshot=f"research-session:{session.research_session_id}",
            evidence_ids=proposal.evidence_ids,
            parameters={"debate_id": proposal.debate_id},
            status=ExperimentStatus.FINISHED,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        self._storage.save(experiment)
        return experiment.experiment_id

    def _validate_risk(
        self,
        proposal: DecisionProposal,
        verdict: RiskVerdict,
        final_conclusion: ResearchConclusion,
        final_confidence: float,
    ) -> None:
        if final_confidence > proposal.confidence:
            msg = "RiskReview cannot increase confidence"
            raise InvalidStateTransitionError(msg)
        if proposal.conclusion in {
            ResearchConclusion.WATCH,
            ResearchConclusion.NO_TRADE,
            ResearchConclusion.INVALID,
        } and final_conclusion in {ResearchConclusion.BUY, ResearchConclusion.SELL}:
            msg = "RiskReview cannot upgrade non-trade conclusions to BUY or SELL"
            raise InvalidStateTransitionError(msg)
        if (
            verdict is RiskVerdict.APPROVE
            and final_conclusion is not proposal.conclusion
        ):
            msg = "APPROVE must preserve the DecisionProposal conclusion"
            raise InvalidStateTransitionError(msg)
        if verdict is RiskVerdict.VETO and final_conclusion not in {
            ResearchConclusion.WATCH,
            ResearchConclusion.NO_TRADE,
            ResearchConclusion.INVALID,
        }:
            msg = "VETO can only produce WATCH, NO_TRADE, or INVALID"
            raise InvalidStateTransitionError(msg)
        if verdict is RiskVerdict.DOWNGRADE and not _is_downgrade(
            proposal.conclusion, final_conclusion
        ):
            msg = "DOWNGRADE must lower trading strength"
            raise InvalidStateTransitionError(msg)


def _action_for_conclusion(conclusion: ResearchConclusion) -> Action:
    return {
        ResearchConclusion.BUY: Action.BUY,
        ResearchConclusion.SELL: Action.SELL,
        ResearchConclusion.HOLD: Action.HOLD,
        ResearchConclusion.WATCH: Action.OBSERVE,
        ResearchConclusion.NO_TRADE: Action.NO_TRADE,
        ResearchConclusion.INVALID: Action.NO_TRADE,
    }[conclusion]


def _is_downgrade(
    original: ResearchConclusion,
    final: ResearchConclusion,
) -> bool:
    rank = {
        ResearchConclusion.BUY: 3,
        ResearchConclusion.SELL: 3,
        ResearchConclusion.HOLD: 2,
        ResearchConclusion.WATCH: 1,
        ResearchConclusion.NO_TRADE: 0,
        ResearchConclusion.INVALID: 0,
    }
    return rank[final] < rank[original]
