from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from tests.factories import (
    make_agent_report,
    make_debate,
    make_decision_proposal,
    make_hypothesis,
    make_research_session,
    make_risk_review,
    make_watchlist_item,
)

from aios.application.research_settlement import ResearchSettlementService
from aios.integrations.baostock.adapter import BaoStockMarketDataAdapter
from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.kernel.debate import DecisionAssemblyRecord
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    ApprovalStatus,
    LearningType,
    OutcomeStatus,
    ResearchConclusion,
)
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


@pytest.mark.external_llm
@pytest.mark.external_market
def test_real_brain005_settlement_learning_smoke() -> None:
    if os.getenv("AIOS_RUN_BRAIN005_EXTERNAL_LLM_TESTS") != "1":
        pytest.skip("set AIOS_RUN_BRAIN005_EXTERNAL_LLM_TESTS=1 to run BRAIN-005 smoke")
    model = os.getenv("AIOS_EXTERNAL_LLM_MODEL")
    if not model:
        pytest.skip("set AIOS_EXTERNAL_LLM_MODEL to run external LLM smoke")

    storage, assembly_id, decision = _seed_finalized_research_decision()
    lifecycle = DecisionLifecycleService(storage)
    result = ResearchSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=BaoStockMarketDataAdapter(),
        llm_adapter=LiteLLMAdapter(),
        llm_model=model,
    ).settle_assembly(
        assembly_id=assembly_id,
        as_of=datetime.now(UTC) + timedelta(days=7),
    )

    assert result.outcome.status in {
        OutcomeStatus.SETTLED,
        OutcomeStatus.INSUFFICIENT_DATA,
    }
    assert result.evaluation.outcome_id == result.outcome.outcome_id
    assert result.review.decision_id == decision.decision_id
    assert result.learnings
    assert all(
        learning.approval_status is ApprovalStatus.PENDING
        for learning in result.learnings
    )
    weight_learning = next(
        learning
        for learning in result.learnings
        if learning.learning_type is LearningType.AGENT_WEIGHT_UPDATE
    )
    assert weight_learning.after["application_mode"] == "proposal_only"
    assert weight_learning.after["status"] == "pending_approval"
    assert weight_learning.after["skill_weight_adjustments"]
    assert lifecycle.list_entities(Learning) == list(result.learnings)

    repeated = ResearchSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=BaoStockMarketDataAdapter(),
        llm_adapter=LiteLLMAdapter(),
        llm_model=model,
    ).settle_assembly(
        assembly_id=assembly_id,
        as_of=datetime.now(UTC) + timedelta(days=8),
    )

    assert repeated.record == result.record
    assert repeated.outcome == result.outcome
    assert repeated.evaluation == result.evaluation
    assert repeated.review == result.review
    assert repeated.learnings == result.learnings
    assert len(storage.list(Learning)) == len(result.learnings)


def _seed_finalized_research_decision() -> tuple[InMemoryStorage, str, Decision]:
    storage = InMemoryStorage()
    lifecycle = DecisionLifecycleService(storage)
    decision_created_at = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    evidence = Evidence(
        evidence_id="ev_brain005_smoke_market",
        evidence_type="market_daily_bar",
        source="brain005-smoke",
        symbols=("600519.SH",),
        published_at=decision_created_at - timedelta(days=1),
        available_at=decision_created_at - timedelta(days=1),
        summary="Historical market evidence for BRAIN-005 smoke.",
        reliability=0.9,
        content_hash="hash-brain005-smoke-market",
        created_at=decision_created_at - timedelta(days=1),
    )
    watchlist = make_watchlist_item(symbol="600519.SH")
    session = make_research_session(
        symbol="600519.SH",
        evidence_ids=(evidence.evidence_id,),
        as_of=decision_created_at,
    )
    report = make_agent_report(
        research_session_id=session.research_session_id,
        evidence_ids=(evidence.evidence_id,),
    )
    hypothesis = make_hypothesis(
        research_session_id=session.research_session_id,
        report_ids=(report.report_id,),
        evidence_ids=(evidence.evidence_id,),
    )
    debate = make_debate(
        research_session_id=session.research_session_id,
        report_ids=(report.report_id,),
        hypothesis_ids=(hypothesis.hypothesis_id,),
    )
    proposal = make_decision_proposal(
        debate_id=debate.debate_id,
        hypothesis_ids=(hypothesis.hypothesis_id,),
        evidence_ids=(evidence.evidence_id,),
    ).model_copy(
        update={
            "conclusion": ResearchConclusion.BUY,
            "confidence": 0.7,
            "thesis": "buy with risk controls",
        }
    )
    risk = make_risk_review(proposal_id=proposal.proposal_id).model_copy(
        update={
            "final_conclusion": ResearchConclusion.BUY,
            "final_confidence": 0.7,
            "reasons": ("risk accepted",),
        }
    )
    for entity in (
        evidence,
        watchlist,
        session,
        report,
        hypothesis,
        debate,
        proposal,
        risk,
    ):
        storage.save(entity)
    experiment = lifecycle.start_experiment(
        Experiment(
            name="brain005-smoke",
            model="manual-no-llm",
            prompt_version="decision-v1",
            agent_config_version="manual-smoke",
            dataset_snapshot="brain005-smoke-market",
            evidence_ids=(evidence.evidence_id,),
            parameters={"temperature": 0},
            started_at=decision_created_at - timedelta(minutes=10),
            finished_at=decision_created_at - timedelta(minutes=1),
            created_at=decision_created_at - timedelta(minutes=10),
        )
    )
    decision = lifecycle.create_decision(
        Decision(
            experiment_id=experiment.experiment_id,
            symbol=session.scope.symbol,
            action=Action.BUY,
            horizon=f"{session.scope.horizon_days}d",
            confidence=0.7,
            expected_return=0.0,
            max_expected_loss=0.1,
            evidence_ids=(evidence.evidence_id,),
            reasoning_summary=proposal.thesis,
            created_at=decision_created_at,
            valid_until=session.scope.valid_until,
        )
    )
    assembly = DecisionAssemblyRecord(
        research_session_id=session.research_session_id,
        debate_id=debate.debate_id,
        proposal_id=proposal.proposal_id,
        risk_review_id=risk.risk_review_id,
        decision_id=decision.decision_id,
        conclusion=proposal.conclusion,
        report_ids=(report.report_id,),
        hypothesis_ids=(hypothesis.hypothesis_id,),
        evidence_ids=(evidence.evidence_id,),
        created_at=decision_created_at,
    )
    storage.save(assembly)
    return storage, assembly.assembly_id, decision
