from __future__ import annotations

from datetime import timedelta

import pytest
from tests.factories import (
    fixed_now,
    make_agent_report,
    make_evidence,
    make_hypothesis,
    make_research_session,
)

from aios.application.debate import DebateService
from aios.kernel.debate import DecisionAssemblyRecord
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    DebateStance,
    DebateStatus,
    ResearchConclusion,
    ResearchSessionStatus,
    RiskVerdict,
)
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
    ReferenceIntegrityError,
)
from aios.storage.memory import InMemoryStorage


def seeded_storage() -> tuple[InMemoryStorage, str, str, str, str]:
    storage = InMemoryStorage()
    evidence = make_evidence().model_copy(update={"symbols": ("600519",)})
    session = make_research_session(evidence_ids=(evidence.evidence_id,))
    report = make_agent_report(
        research_session_id=session.research_session_id,
        evidence_ids=(evidence.evidence_id,),
    )
    hypothesis = make_hypothesis(
        research_session_id=session.research_session_id,
        report_ids=(report.report_id,),
        evidence_ids=(evidence.evidence_id,),
    )
    for entity in [evidence, session, report, hypothesis]:
        storage.save(entity)
    return (
        storage,
        session.research_session_id,
        report.report_id,
        hypothesis.hypothesis_id,
        evidence.evidence_id,
    )


def test_create_debate_freezes_active_reports_and_hypotheses() -> None:
    storage, session_id, report_id, hypothesis_id, _evidence_id = seeded_storage()

    debate = DebateService(storage).create_debate(research_session_id=session_id)

    assert debate.research_session_id == session_id
    assert debate.report_ids == (report_id,)
    assert debate.hypothesis_ids == (hypothesis_id,)
    assert debate.status is DebateStatus.OPEN

    replacement = make_agent_report(
        report_id="ar_00000000-0000-0000-0000-000000000099",
        research_session_id=session_id,
    )
    storage.save(replacement)
    assert DebateService(storage).get_debate(debate.debate_id).report_ids == (
        report_id,
    )


def test_cancelled_session_cannot_create_debate() -> None:
    storage, session_id, _report_id, _hypothesis_id, _evidence_id = seeded_storage()
    session = storage.get(type(make_research_session()), session_id)
    storage.replace(
        session.model_copy(
            update={
                "status": ResearchSessionStatus.CANCELLED,
                "cancelled_at": fixed_now() + timedelta(minutes=1),
            }
        )
    )

    with pytest.raises(InvalidStateTransitionError):
        DebateService(storage).create_debate(research_session_id=session_id)


def test_debate_statement_reference_and_uniqueness_rules() -> None:
    storage, session_id, report_id, hypothesis_id, evidence_id = seeded_storage()
    service = DebateService(storage)
    debate = service.create_debate(research_session_id=session_id)

    statement = service.add_debate_statement(
        debate_id=debate.debate_id,
        agent_report_id=report_id,
        hypothesis_id=hypothesis_id,
        stance=DebateStance.SUPPORT,
        reasoning="supports",
        evidence_ids=[evidence_id],
        confidence_before=0.5,
        confidence_after=0.6,
    )
    assert statement.agent_report_id == report_id

    with pytest.raises(DuplicateEntityError):
        service.add_debate_statement(
            debate_id=debate.debate_id,
            agent_report_id=report_id,
            hypothesis_id=hypothesis_id,
            stance=DebateStance.NEUTRAL,
            reasoning="again",
            evidence_ids=[],
            confidence_before=0.5,
            confidence_after=0.5,
        )

    with pytest.raises(ReferenceIntegrityError):
        service.add_debate_statement(
            debate_id=debate.debate_id,
            agent_report_id="ar_missing",
            hypothesis_id=hypothesis_id,
            stance=DebateStance.OPPOSE,
            reasoning="bad",
            evidence_ids=[],
            confidence_before=0.5,
            confidence_after=0.4,
        )


def test_proposal_risk_and_finalize_are_auditable_and_idempotent() -> None:
    storage, session_id, report_id, hypothesis_id, evidence_id = seeded_storage()
    service = DebateService(storage)
    debate = service.create_debate(research_session_id=session_id)
    proposal = service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.BUY,
        confidence=0.7,
        thesis="buy with risk controls",
        supporting_hypothesis_ids=[hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence_id],
        risk_notes=["size small"],
    )

    with pytest.raises(InvalidStateTransitionError):
        service.submit_risk_review(
            proposal_id=proposal.proposal_id,
            verdict=RiskVerdict.DOWNGRADE,
            final_conclusion=ResearchConclusion.SELL,
            final_confidence=0.8,
            reasons=["upgrade attempt"],
        )

    risk = service.submit_risk_review(
        proposal_id=proposal.proposal_id,
        verdict=RiskVerdict.DOWNGRADE,
        final_conclusion=ResearchConclusion.WATCH,
        final_confidence=0.5,
        reasons=["risk downgrade"],
    )
    assert risk.final_conclusion is ResearchConclusion.WATCH

    assembly = service.finalize_decision(proposal.proposal_id)
    assert isinstance(assembly, DecisionAssemblyRecord)
    assert assembly.research_session_id == session_id
    assert assembly.debate_id == debate.debate_id
    assert assembly.proposal_id == proposal.proposal_id
    assert assembly.risk_review_id == risk.risk_review_id
    assert assembly.report_ids == (report_id,)
    assert assembly.hypothesis_ids == (hypothesis_id,)
    decision = storage.get(Decision, assembly.decision_id)
    assert decision.action.value == "observe"
    assert decision.evidence_ids == (evidence_id,)

    assert service.finalize_decision(proposal.proposal_id) == assembly


def test_veto_and_invalid_mapping() -> None:
    storage, session_id, _report_id, hypothesis_id, evidence_id = seeded_storage()
    service = DebateService(storage)
    debate = service.create_debate(research_session_id=session_id)
    proposal = service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.BUY,
        confidence=0.7,
        thesis="invalidated by risk",
        supporting_hypothesis_ids=[hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence_id],
        risk_notes=[],
    )
    service.submit_risk_review(
        proposal_id=proposal.proposal_id,
        verdict=RiskVerdict.VETO,
        final_conclusion=ResearchConclusion.INVALID,
        final_confidence=0.1,
        reasons=["invalid setup"],
    )

    assembly = service.finalize_decision(proposal.proposal_id)
    decision = storage.get(Decision, assembly.decision_id)
    assert decision.action.value == "no_trade"
    assert decision.status.value == "invalid"
