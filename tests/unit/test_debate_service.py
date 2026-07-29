from __future__ import annotations

from datetime import timedelta

import pytest
from tests.factories import (
    fixed_now,
    make_agent_report,
    make_debate,
    make_evidence,
    make_hypothesis,
    make_research_session,
)

from aios.application.debate import DebateService
from aios.kernel.debate import DecisionAssemblyRecord
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    DebateStance,
    DecisionStatus,
    ResearchConclusion,
    ResearchSessionStatus,
    RiskVerdict,
)
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
    MissingEntityError,
    ReferenceIntegrityError,
)
from aios.storage.memory import InMemoryStorage


def seed_session(
    storage: InMemoryStorage,
    *,
    suffix: str = "001",
    symbol: str = "600519",
) -> tuple[str, str, str, str]:
    evidence_id = f"ev_00000000-0000-0000-0000-000000000{suffix}"
    session_id = f"rs_00000000-0000-0000-0000-000000000{suffix}"
    report_id = f"ar_00000000-0000-0000-0000-000000000{suffix}"
    hypothesis_id = f"hp_00000000-0000-0000-0000-000000000{suffix}"
    evidence = make_evidence(evidence_id=evidence_id).model_copy(
        update={"symbols": (symbol,)}
    )
    session = make_research_session(
        research_session_id=session_id,
        watchlist_item_id=f"wl_00000000-0000-0000-0000-000000000{suffix}",
        symbol=symbol,
        evidence_ids=(evidence_id,),
    )
    report = make_agent_report(
        report_id=report_id,
        research_session_id=session_id,
        evidence_ids=(evidence_id,),
    )
    hypothesis = make_hypothesis(
        hypothesis_id=hypothesis_id,
        research_session_id=session_id,
        report_ids=(report_id,),
        evidence_ids=(evidence_id,),
    )
    for entity in (evidence, session, report, hypothesis):
        storage.save(entity)
    return session_id, report_id, hypothesis_id, evidence_id


def test_cancelled_research_session_cannot_create_debate() -> None:
    storage = InMemoryStorage()
    session_id, _report_id, _hypothesis_id, _evidence_id = seed_session(storage)
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


def test_create_debate_freezes_only_report_and_hypothesis_from_same_session() -> None:
    storage = InMemoryStorage()
    session_id, report_id, hypothesis_id, _evidence_id = seed_session(storage)
    _other_session_id, other_report_id, other_hypothesis_id, _other_evidence_id = (
        seed_session(storage, suffix="002", symbol="000001")
    )

    debate = DebateService(storage).create_debate(research_session_id=session_id)

    assert debate.research_session_id == session_id
    assert debate.report_ids == (report_id,)
    assert debate.hypothesis_ids == (hypothesis_id,)
    assert other_report_id not in debate.report_ids
    assert other_hypothesis_id not in debate.hypothesis_ids

    late_report = make_agent_report(
        report_id="ar_00000000-0000-0000-0000-000000000099",
        research_session_id=session_id,
    )
    storage.save(late_report)
    assert DebateService(storage).get_debate(debate.debate_id).report_ids == (
        report_id,
    )


def test_statement_references_only_frozen_debate_inputs_and_is_unique() -> None:
    storage = InMemoryStorage()
    session_id, report_id, hypothesis_id, evidence_id = seed_session(storage)
    _other_session_id, other_report_id, other_hypothesis_id, other_evidence_id = (
        seed_session(storage, suffix="002", symbol="000001")
    )
    service = DebateService(storage)
    debate = service.create_debate(research_session_id=session_id)

    with pytest.raises(ReferenceIntegrityError):
        service.add_debate_statement(
            debate_id=debate.debate_id,
            agent_report_id=report_id,
            hypothesis_id=hypothesis_id,
            stance=DebateStance.OPPOSE,
            reasoning="wrong evidence",
            evidence_ids=[other_evidence_id],
            confidence_before=0.5,
            confidence_after=0.4,
        )

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
    assert statement.hypothesis_id == hypothesis_id

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
            agent_report_id=other_report_id,
            hypothesis_id=hypothesis_id,
            stance=DebateStance.OPPOSE,
            reasoning="wrong report",
            evidence_ids=[],
            confidence_before=0.5,
            confidence_after=0.4,
        )
    with pytest.raises(ReferenceIntegrityError):
        service.add_debate_statement(
            debate_id=debate.debate_id,
            agent_report_id=report_id,
            hypothesis_id=other_hypothesis_id,
            stance=DebateStance.OPPOSE,
            reasoning="wrong hypothesis",
            evidence_ids=[],
            confidence_before=0.5,
            confidence_after=0.4,
        )


def test_proposal_references_only_frozen_hypotheses_and_is_one_per_debate() -> None:
    storage = InMemoryStorage()
    session_id, _report_id, hypothesis_id, evidence_id = seed_session(storage)
    _other_session_id, _other_report_id, other_hypothesis_id, other_evidence_id = (
        seed_session(storage, suffix="002", symbol="000001")
    )
    service = DebateService(storage)
    debate = service.create_debate(research_session_id=session_id)

    with pytest.raises(ReferenceIntegrityError):
        service.assemble_decision_proposal(
            debate_id=debate.debate_id,
            conclusion=ResearchConclusion.BUY,
            confidence=0.7,
            thesis="bad hypothesis",
            supporting_hypothesis_ids=[other_hypothesis_id],
            rejected_hypothesis_ids=[],
            evidence_ids=[evidence_id],
            risk_notes=[],
        )
    with pytest.raises(ReferenceIntegrityError):
        service.assemble_decision_proposal(
            debate_id=debate.debate_id,
            conclusion=ResearchConclusion.BUY,
            confidence=0.7,
            thesis="bad evidence",
            supporting_hypothesis_ids=[hypothesis_id],
            rejected_hypothesis_ids=[],
            evidence_ids=[other_evidence_id],
            risk_notes=[],
        )

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
    assert proposal.debate_id == debate.debate_id

    with pytest.raises(DuplicateEntityError):
        service.assemble_decision_proposal(
            debate_id=debate.debate_id,
            conclusion=ResearchConclusion.WATCH,
            confidence=0.5,
            thesis="second proposal",
            supporting_hypothesis_ids=[hypothesis_id],
            rejected_hypothesis_ids=[],
            evidence_ids=[evidence_id],
            risk_notes=[],
        )


@pytest.mark.parametrize(
    ("verdict", "final_conclusion"),
    [
        (RiskVerdict.APPROVE, ResearchConclusion.BUY),
        (RiskVerdict.DOWNGRADE, ResearchConclusion.WATCH),
        (RiskVerdict.VETO, ResearchConclusion.INVALID),
    ],
)
def test_risk_review_accepts_approve_downgrade_and_veto_rules(
    verdict: RiskVerdict,
    final_conclusion: ResearchConclusion,
) -> None:
    storage = InMemoryStorage()
    _session_id, _report_id, hypothesis_id, evidence_id = seed_session(storage)
    service = DebateService(storage)
    debate = service.create_debate(
        research_session_id="rs_00000000-0000-0000-0000-000000000001"
    )
    proposal = service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.BUY,
        confidence=0.7,
        thesis="buy with risk controls",
        supporting_hypothesis_ids=[hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence_id],
        risk_notes=[],
    )

    review = service.submit_risk_review(
        proposal_id=proposal.proposal_id,
        verdict=verdict,
        final_conclusion=final_conclusion,
        final_confidence=0.6,
        reasons=["risk reviewed"],
    )

    assert review.verdict is verdict
    assert review.final_conclusion is final_conclusion


@pytest.mark.parametrize(
    ("verdict", "final_conclusion"),
    [
        (RiskVerdict.APPROVE, ResearchConclusion.WATCH),
        (RiskVerdict.DOWNGRADE, ResearchConclusion.BUY),
        (RiskVerdict.VETO, ResearchConclusion.BUY),
    ],
)
def test_risk_review_rejects_invalid_verdict_transitions(
    verdict: RiskVerdict,
    final_conclusion: ResearchConclusion,
) -> None:
    storage = InMemoryStorage()
    _session_id, _report_id, hypothesis_id, evidence_id = seed_session(storage)
    service = DebateService(storage)
    debate = service.create_debate(
        research_session_id="rs_00000000-0000-0000-0000-000000000001"
    )
    proposal = service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.BUY,
        confidence=0.7,
        thesis="buy with risk controls",
        supporting_hypothesis_ids=[hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence_id],
        risk_notes=[],
    )

    with pytest.raises(InvalidStateTransitionError):
        service.submit_risk_review(
            proposal_id=proposal.proposal_id,
            verdict=verdict,
            final_conclusion=final_conclusion,
            final_confidence=0.6,
            reasons=["bad transition"],
        )


def test_risk_review_cannot_increase_confidence_or_upgrade_non_trade_conclusion() -> (
    None
):
    storage = InMemoryStorage()
    _session_id, _report_id, hypothesis_id, evidence_id = seed_session(storage)
    service = DebateService(storage)
    debate = service.create_debate(
        research_session_id="rs_00000000-0000-0000-0000-000000000001"
    )
    proposal = service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.WATCH,
        confidence=0.5,
        thesis="watch pending confirmation",
        supporting_hypothesis_ids=[hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence_id],
        risk_notes=[],
    )

    with pytest.raises(InvalidStateTransitionError):
        service.submit_risk_review(
            proposal_id=proposal.proposal_id,
            verdict=RiskVerdict.APPROVE,
            final_conclusion=ResearchConclusion.WATCH,
            final_confidence=0.6,
            reasons=["confidence increase"],
        )
    with pytest.raises(InvalidStateTransitionError):
        service.submit_risk_review(
            proposal_id=proposal.proposal_id,
            verdict=RiskVerdict.APPROVE,
            final_conclusion=ResearchConclusion.BUY,
            final_confidence=0.5,
            reasons=["upgrade"],
        )


def test_each_proposal_has_one_risk_review() -> None:
    storage = InMemoryStorage()
    _session_id, _report_id, hypothesis_id, evidence_id = seed_session(storage)
    service = DebateService(storage)
    debate = service.create_debate(
        research_session_id="rs_00000000-0000-0000-0000-000000000001"
    )
    proposal = service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.BUY,
        confidence=0.7,
        thesis="buy with risk controls",
        supporting_hypothesis_ids=[hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence_id],
        risk_notes=[],
    )
    service.submit_risk_review(
        proposal_id=proposal.proposal_id,
        verdict=RiskVerdict.APPROVE,
        final_conclusion=ResearchConclusion.BUY,
        final_confidence=0.7,
        reasons=["approved"],
    )

    with pytest.raises(DuplicateEntityError):
        service.submit_risk_review(
            proposal_id=proposal.proposal_id,
            verdict=RiskVerdict.DOWNGRADE,
            final_conclusion=ResearchConclusion.WATCH,
            final_confidence=0.5,
            reasons=["second review"],
        )


def test_finalize_creates_decision_assembly_and_is_idempotent() -> None:
    storage = InMemoryStorage()
    session_id, report_id, hypothesis_id, evidence_id = seed_session(storage)
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
        risk_notes=[],
    )
    risk = service.submit_risk_review(
        proposal_id=proposal.proposal_id,
        verdict=RiskVerdict.APPROVE,
        final_conclusion=ResearchConclusion.BUY,
        final_confidence=0.7,
        reasons=["approved"],
    )

    assembly = service.finalize_decision(proposal.proposal_id)
    second = service.finalize_decision(proposal.proposal_id)

    assert isinstance(assembly, DecisionAssemblyRecord)
    assert second == assembly
    assert len(storage.list(Decision)) == 1
    decision = storage.get(Decision, assembly.decision_id)
    assert decision.action is Action.BUY
    assert decision.status is DecisionStatus.PROPOSED
    assert decision.symbol == "600519"
    assert decision.horizon == "3d"
    assert decision.confidence == risk.final_confidence
    assert decision.evidence_ids == (evidence_id,)
    assert assembly.research_session_id == session_id
    assert assembly.debate_id == debate.debate_id
    assert assembly.proposal_id == proposal.proposal_id
    assert assembly.risk_review_id == risk.risk_review_id
    assert assembly.report_ids == (report_id,)
    assert assembly.hypothesis_ids == (hypothesis_id,)
    assert assembly.evidence_ids == (evidence_id,)


def test_finalize_invalid_maps_to_no_trade_and_invalid_status() -> None:
    storage = InMemoryStorage()
    session_id, _report_id, hypothesis_id, evidence_id = seed_session(storage)
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

    assert decision.action is Action.NO_TRADE
    assert decision.status is DecisionStatus.INVALID


def test_missing_entities_raise_correct_errors() -> None:
    service = DebateService(InMemoryStorage())

    with pytest.raises(MissingEntityError):
        service.create_debate(research_session_id="rs_missing")
    with pytest.raises(MissingEntityError):
        service.get_debate("db_missing")
    with pytest.raises(MissingEntityError):
        service.add_debate_statement(
            debate_id="db_missing",
            agent_report_id="ar_missing",
            hypothesis_id="hp_missing",
            stance=DebateStance.SUPPORT,
            reasoning="missing",
            evidence_ids=[],
            confidence_before=0.5,
            confidence_after=0.6,
        )
    with pytest.raises(MissingEntityError):
        service.submit_risk_review(
            proposal_id="dp_missing",
            verdict=RiskVerdict.APPROVE,
            final_conclusion=ResearchConclusion.BUY,
            final_confidence=0.5,
            reasons=["missing"],
        )
    with pytest.raises(MissingEntityError):
        service.finalize_decision("dp_missing")


def test_service_revalidates_references_even_for_manually_saved_debate() -> None:
    storage = InMemoryStorage()
    session_id, report_id, _hypothesis_id, evidence_id = seed_session(storage)
    _other_session_id, _other_report_id, other_hypothesis_id, _other_evidence_id = (
        seed_session(storage, suffix="002", symbol="000001")
    )
    debate = make_debate(
        research_session_id=session_id,
        report_ids=(report_id,),
        hypothesis_ids=(other_hypothesis_id,),
    )
    storage.save(debate)

    with pytest.raises(ReferenceIntegrityError):
        DebateService(storage).add_debate_statement(
            debate_id=debate.debate_id,
            agent_report_id=report_id,
            hypothesis_id=other_hypothesis_id,
            stance=DebateStance.SUPPORT,
            reasoning="cannot bypass validation",
            evidence_ids=[evidence_id],
            confidence_before=0.5,
            confidence_after=0.6,
        )
