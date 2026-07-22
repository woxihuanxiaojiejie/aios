from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError
from tests.factories import (
    fixed_now,
    make_agent_report,
    make_evidence,
    make_hypothesis,
    make_research_session,
)

from aios.application.research_records import ResearchRecordService
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
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.storage.memory import InMemoryStorage


def test_agent_report_model_validates_confidence_and_normalizes_fields() -> None:
    report = AgentReport(
        research_session_id="rs_1",
        role="technical",
        summary="  constructive trend  ",
        stance=" watch ",
        confidence=1,
        evidence_ids=("ev_1",),
        source="manual",
        raw_reference="  ticket-1 ",
    )

    assert report.report_id.startswith("ar_")
    assert report.role is AgentRole.TECHNICAL
    assert report.summary == "constructive trend"
    assert report.stance == "watch"
    assert report.source == "manual"
    assert report.raw_reference == "ticket-1"
    assert report.status is AgentReportStatus.ACTIVE

    with pytest.raises(ValidationError):
        AgentReport(
            research_session_id="rs_1",
            role="technical",
            summary="x",
            stance="watch",
            confidence=1.1,
            evidence_ids=(),
            source="manual",
        )


def test_hypothesis_model_validates_required_text() -> None:
    hypothesis = make_hypothesis()

    assert hypothesis.hypothesis_id.startswith("hp_")
    assert hypothesis.status is HypothesisStatus.PROPOSED

    with pytest.raises(ValidationError):
        Hypothesis(
            research_session_id="rs_1",
            statement=" ",
            rationale="x",
            direction="bullish",
            horizon_days=3,
            confidence=0.5,
            supporting_report_ids=("ar_1",),
            supporting_evidence_ids=(),
        )


def test_agent_report_service_create_archive_and_duplicate_role_rules() -> None:
    storage = InMemoryStorage()
    evidence = make_evidence().model_copy(update={"symbols": ("600519",)})
    session = make_research_session(evidence_ids=(evidence.evidence_id,))
    storage.save(evidence)
    storage.save(session)
    service = ResearchRecordService(storage)

    report = service.create_agent_report(
        research_session_id=session.research_session_id,
        role=AgentRole.TECHNICAL,
        summary="trend",
        stance="watch",
        confidence=0.7,
        evidence_ids=[evidence.evidence_id],
        source="manual",
    )

    assert report.status is AgentReportStatus.ACTIVE
    assert report.evidence_ids == (evidence.evidence_id,)
    assert (
        storage.find_active_agent_report(
            session.research_session_id,
            AgentRole.TECHNICAL,
        )
        == report
    )

    with pytest.raises(DuplicateEntityError):
        service.create_agent_report(
            research_session_id=session.research_session_id,
            role=AgentRole.TECHNICAL,
            summary="duplicate",
            stance="watch",
            confidence=0.5,
            evidence_ids=[],
            source="manual",
        )

    archived = service.archive_agent_report(report.report_id)
    assert archived.status is AgentReportStatus.ARCHIVED
    assert archived.archived_at is not None
    assert service.get_agent_report(report.report_id) == archived

    replacement = service.create_agent_report(
        research_session_id=session.research_session_id,
        role=AgentRole.TECHNICAL,
        summary="new",
        stance="watch",
        confidence=0.6,
        evidence_ids=[],
        source="manual",
    )
    assert replacement.report_id != report.report_id


def test_agent_report_service_rejects_cancelled_session_and_non_session_evidence() -> (
    None
):
    storage = InMemoryStorage()
    evidence = make_evidence().model_copy(update={"symbols": ("600519",)})
    other = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000099",
    ).model_copy(update={"symbols": ("600519",)})
    session = make_research_session(evidence_ids=(evidence.evidence_id,))
    cancelled = session.model_copy(
        update={
            "status": ResearchSessionStatus.CANCELLED,
            "cancelled_at": fixed_now() + timedelta(minutes=1),
        }
    )
    storage.save(evidence)
    storage.save(other)
    storage.save(cancelled)
    service = ResearchRecordService(storage)

    with pytest.raises(InvalidStateTransitionError):
        service.create_agent_report(
            research_session_id=session.research_session_id,
            role=AgentRole.NEWS,
            summary="news",
            stance="neutral",
            confidence=0.5,
            evidence_ids=[],
            source="manual",
        )

    active = session.model_copy(
        update={
            "research_session_id": "rs_00000000-0000-0000-0000-000000000099",
            "status": ResearchSessionStatus.EVIDENCE_READY,
            "cancelled_at": None,
        }
    )
    storage.save(active)
    with pytest.raises(ReferenceIntegrityError):
        service.create_agent_report(
            research_session_id=active.research_session_id,
            role=AgentRole.NEWS,
            summary="news",
            stance="neutral",
            confidence=0.5,
            evidence_ids=[other.evidence_id],
            source="manual",
        )


def test_hypothesis_service_rules_and_status_updates() -> None:
    storage = InMemoryStorage()
    evidence = make_evidence().model_copy(update={"symbols": ("600519",)})
    session = make_research_session(evidence_ids=(evidence.evidence_id,))
    report = make_agent_report(
        research_session_id=session.research_session_id,
        evidence_ids=(evidence.evidence_id,),
    )
    storage.save(evidence)
    storage.save(session)
    storage.save(report)
    service = ResearchRecordService(storage)

    first = service.create_hypothesis(
        research_session_id=session.research_session_id,
        statement="Demand improves",
        rationale="report",
        direction="bullish",
        horizon_days=session.scope.horizon_days,
        confidence=0.6,
        supporting_report_ids=[report.report_id],
        supporting_evidence_ids=[evidence.evidence_id],
    )
    second = service.create_hypothesis(
        research_session_id=session.research_session_id,
        statement="Margins stabilize",
        rationale="report",
        direction="bullish",
        horizon_days=session.scope.horizon_days,
        confidence=0.55,
        supporting_report_ids=[report.report_id],
        supporting_evidence_ids=[],
    )
    assert service.list_hypotheses(research_session_id=session.research_session_id) == [
        first,
        second,
    ]

    with pytest.raises(DuplicateEntityError):
        service.create_hypothesis(
            research_session_id=session.research_session_id,
            statement="third",
            rationale="report",
            direction="bullish",
            horizon_days=session.scope.horizon_days,
            confidence=0.5,
            supporting_report_ids=[report.report_id],
            supporting_evidence_ids=[],
        )

    updated = service.update_hypothesis_status(
        first.hypothesis_id,
        HypothesisStatus.VALIDATED,
    )
    assert updated.status is HypothesisStatus.VALIDATED

    with pytest.raises(InvalidStateTransitionError):
        service.update_hypothesis_status(first.hypothesis_id, HypothesisStatus.PROPOSED)


def test_hypothesis_service_rejects_cross_session_references_and_horizon_mismatch() -> (
    None
):
    storage = InMemoryStorage()
    first_session = make_research_session()
    second_session = make_research_session(
        research_session_id="rs_00000000-0000-0000-0000-000000000002",
    )
    report = make_agent_report(research_session_id=second_session.research_session_id)
    storage.save(first_session)
    storage.save(second_session)
    storage.save(report)
    service = ResearchRecordService(storage)

    with pytest.raises(ReferenceIntegrityError):
        service.create_hypothesis(
            research_session_id=first_session.research_session_id,
            statement="x",
            rationale="x",
            direction="bullish",
            horizon_days=first_session.scope.horizon_days,
            confidence=0.5,
            supporting_report_ids=[report.report_id],
            supporting_evidence_ids=[],
        )

    with pytest.raises(InvalidStateTransitionError):
        service.create_hypothesis(
            research_session_id=first_session.research_session_id,
            statement="x",
            rationale="x",
            direction="bullish",
            horizon_days=7,
            confidence=0.5,
            supporting_report_ids=[],
            supporting_evidence_ids=[],
        )


def test_research_record_storage_filters_and_missing_get() -> None:
    storage = InMemoryStorage()
    report = make_agent_report()
    hypothesis = make_hypothesis(report_ids=(report.report_id,))
    storage.save(report)
    storage.save(hypothesis)

    assert storage.list_agent_reports(
        research_session_id=report.research_session_id
    ) == [report]
    assert storage.list_agent_reports(role=AgentRole.TECHNICAL) == [report]
    assert storage.list_hypotheses(
        research_session_id=hypothesis.research_session_id
    ) == [hypothesis]
    assert storage.list_hypotheses(status=HypothesisStatus.PROPOSED) == [hypothesis]

    service = ResearchRecordService(storage)
    with pytest.raises(MissingEntityError):
        service.get_agent_report("ar_missing")
    with pytest.raises(MissingEntityError):
        service.get_hypothesis("hp_missing")
