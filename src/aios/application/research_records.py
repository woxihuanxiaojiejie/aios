from __future__ import annotations

from aios.adapters.storage import Storage
from aios.kernel.base import utc_now
from aios.kernel.enums import (
    AgentReportStatus,
    AgentRole,
    HypothesisStatus,
    ResearchSessionStatus,
)
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
    MissingEntityError,
    ReferenceIntegrityError,
)
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis


class ResearchRecordService:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def create_agent_report(
        self,
        *,
        research_session_id: str,
        role: AgentRole,
        summary: str,
        stance: str,
        confidence: float,
        evidence_ids: list[str] | tuple[str, ...],
        source: str,
        raw_reference: str | None = None,
    ) -> AgentReport:
        session = self._get_open_session(research_session_id)
        evidence_tuple = tuple(evidence_ids)
        self._validate_session_evidence(session, evidence_tuple)
        existing = self._storage.find_active_agent_report(research_session_id, role)
        if existing is not None:
            msg = f"active AgentReport already exists for {research_session_id}:{role}"
            raise DuplicateEntityError(msg)
        report = AgentReport(
            research_session_id=research_session_id,
            role=role,
            summary=summary,
            stance=stance,
            confidence=confidence,
            evidence_ids=evidence_tuple,
            source=source,
            raw_reference=raw_reference,
        )
        self._storage.save(report)
        return report

    def get_agent_report(self, report_id: str) -> AgentReport:
        return self._storage.get(AgentReport, report_id)

    def list_agent_reports(
        self,
        *,
        research_session_id: str | None = None,
        role: AgentRole | None = None,
        status: AgentReportStatus | None = None,
    ) -> list[AgentReport]:
        return self._storage.list_agent_reports(
            research_session_id=research_session_id,
            role=role,
            status=status,
        )

    def archive_agent_report(self, report_id: str) -> AgentReport:
        report = self._storage.get(AgentReport, report_id)
        if report.status is AgentReportStatus.ARCHIVED:
            msg = f"AgentReport {report_id} is already archived"
            raise InvalidStateTransitionError(msg)
        now = utc_now()
        archived = report.model_copy(
            update={
                "status": AgentReportStatus.ARCHIVED,
                "archived_at": now,
                "updated_at": now,
            },
        )
        self._storage.replace(archived)
        return archived

    def create_hypothesis(
        self,
        *,
        research_session_id: str,
        statement: str,
        rationale: str,
        direction: str,
        horizon_days: int,
        confidence: float,
        supporting_report_ids: list[str] | tuple[str, ...],
        supporting_evidence_ids: list[str] | tuple[str, ...],
    ) -> Hypothesis:
        session = self._get_open_session(research_session_id)
        if horizon_days != session.scope.horizon_days:
            msg = "Hypothesis horizon_days must match ResearchSession scope"
            raise InvalidStateTransitionError(msg)
        report_ids = tuple(supporting_report_ids)
        evidence_ids = tuple(supporting_evidence_ids)
        self._validate_supporting_reports(research_session_id, report_ids)
        self._validate_session_evidence(session, evidence_ids)
        self._validate_hypothesis_count(research_session_id, report_ids)
        hypothesis = Hypothesis(
            research_session_id=research_session_id,
            statement=statement,
            rationale=rationale,
            direction=direction,
            horizon_days=horizon_days,
            confidence=confidence,
            supporting_report_ids=report_ids,
            supporting_evidence_ids=evidence_ids,
            status=HypothesisStatus.PROPOSED,
        )
        self._storage.save(hypothesis)
        return hypothesis

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis:
        return self._storage.get(Hypothesis, hypothesis_id)

    def list_hypotheses(
        self,
        *,
        research_session_id: str | None = None,
        status: HypothesisStatus | None = None,
    ) -> list[Hypothesis]:
        return self._storage.list_hypotheses(
            research_session_id=research_session_id,
            status=status,
        )

    def update_hypothesis_status(
        self,
        hypothesis_id: str,
        status: HypothesisStatus,
    ) -> Hypothesis:
        hypothesis = self._storage.get(Hypothesis, hypothesis_id)
        if status is HypothesisStatus.PROPOSED:
            msg = "Hypothesis status cannot be reset to proposed"
            raise InvalidStateTransitionError(msg)
        updated = hypothesis.model_copy(
            update={"status": status, "updated_at": utc_now()},
        )
        self._storage.replace(updated)
        return updated

    def _get_open_session(self, research_session_id: str) -> ResearchSession:
        try:
            session = self._storage.get(ResearchSession, research_session_id)
        except MissingEntityError:
            raise
        if session.status is ResearchSessionStatus.CANCELLED:
            msg = f"ResearchSession {research_session_id} is cancelled"
            raise InvalidStateTransitionError(msg)
        return session

    def _validate_session_evidence(
        self,
        session: ResearchSession,
        evidence_ids: tuple[str, ...],
    ) -> None:
        allowed = set(session.evidence_ids)
        for evidence_id in evidence_ids:
            if evidence_id not in allowed:
                msg = (
                    f"Evidence {evidence_id} is not frozen on "
                    f"ResearchSession {session.research_session_id}"
                )
                raise ReferenceIntegrityError(msg)

    def _validate_supporting_reports(
        self,
        research_session_id: str,
        report_ids: tuple[str, ...],
    ) -> None:
        for report_id in report_ids:
            report = self._storage.get(AgentReport, report_id)
            if report.research_session_id != research_session_id:
                msg = f"AgentReport {report_id} belongs to another ResearchSession"
                raise ReferenceIntegrityError(msg)

    def _validate_hypothesis_count(
        self,
        research_session_id: str,
        report_ids: tuple[str, ...],
    ) -> None:
        existing = self._storage.list_hypotheses(
            research_session_id=research_session_id
        )
        for report_id in report_ids:
            count = sum(
                1
                for hypothesis in existing
                if report_id in hypothesis.supporting_report_ids
            )
            if count >= 2:
                msg = f"AgentReport {report_id} already has two Hypotheses"
                raise DuplicateEntityError(msg)
