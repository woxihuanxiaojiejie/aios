from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from tests.factories import (
    make_agent_report,
    make_evidence,
    make_hypothesis,
    make_research_session,
    make_watchlist_item,
)

from aios.adapters.llm import LLMStructuredResult
from aios.adapters.market_data import Adjustment, MarketBar
from aios.api.app import create_app
from aios.application.debate import DebateService
from aios.application.research_settlement import ResearchSettlementService
from aios.application.research_settlement_worker import ResearchSettlementWorker
from aios.kernel.base import KernelModel
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    ApprovalStatus,
    DebateStance,
    EvaluationFinalResult,
    LearningType,
    ResearchConclusion,
    RiskVerdict,
)
from aios.kernel.errors import DecisionNotReadyForSettlementError
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchScope, ResearchSession
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


class FixtureMarketDataAdapter:
    def __init__(self, bars: list[MarketBar]) -> None:
        self.bars = bars
        self.calls = 0

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        self.calls += 1
        return [
            bar
            for bar in self.bars
            if bar.symbol == symbol and start_date <= bar.trade_date <= end_date
        ]


class LearningAdvisorLLM:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
                "temperature": temperature,
            }
        )
        parsed = response_schema.model_validate(
            {
                "cause_summary": "Technical thesis was confirmed by realized return.",
                "evidence_references": ["ev_00000000-0000-0000-0000-000000000001"],
                "report_references": ["ar_00000000-0000-0000-0000-000000000001"],
                "skill_weight_adjustments": [
                    {
                        "skill_id": "manual",
                        "report_id": "ar_00000000-0000-0000-0000-000000000001",
                        "delta": "0.50",
                        "reason": "Confirmed report should receive a small boost.",
                    }
                ],
                "learning_recommendations": [
                    "Keep the technical report slightly stronger after approval."
                ],
            }
        )
        return LLMStructuredResult(
            parsed=parsed,
            provider="fake",
            model=model,
            request_id="brain005_fake_request",
            prompt_tokens=100,
            completion_tokens=30,
            total_tokens=130,
            extracted_payload=parsed.model_dump(mode="json"),
            latency_ms=10,
            raw_finish_reason="stop",
        )


class FailOnceLearningStorage(InMemoryStorage):
    def __init__(self) -> None:
        super().__init__()
        self.learning_saves = 0
        self.fail_on_learning_save = True

    def save(self, entity: KernelModel) -> None:
        if isinstance(entity, Learning):
            self.learning_saves += 1
            if self.fail_on_learning_save and self.learning_saves == 2:
                raise RuntimeError("transient learning save failure")
        super().save(entity)


def market_bar(trade_date: date, close: str, *, symbol: str = "600519") -> MarketBar:
    price = Decimal(close)
    return MarketBar(
        symbol=symbol,
        market="CN_A",
        trade_date=trade_date,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        adjustment=Adjustment.NONE,
        source="fixture-test",
        fetched_at=datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
    )


def seed_finalized_research_decision() -> tuple[InMemoryStorage, str, Decision]:
    return seed_finalized_research_decision_with_storage(InMemoryStorage())


def seed_finalized_research_decision_with_storage(
    storage: InMemoryStorage,
) -> tuple[InMemoryStorage, str, Decision]:
    evidence = make_evidence().model_copy(update={"symbols": ("600519",)})
    watchlist = make_watchlist_item()
    session = make_research_session(
        evidence_ids=(evidence.evidence_id,),
        as_of=datetime.now(UTC) + timedelta(hours=1),
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
    for entity in (evidence, watchlist, session, report, hypothesis):
        storage.save(entity)
    debate_service = DebateService(storage)
    debate = debate_service.create_debate(
        research_session_id=session.research_session_id
    )
    debate_service.add_debate_statement(
        debate_id=debate.debate_id,
        agent_report_id=report.report_id,
        hypothesis_id=hypothesis.hypothesis_id,
        stance=DebateStance.SUPPORT,
        reasoning="report supports hypothesis",
        evidence_ids=[evidence.evidence_id],
        confidence_before=0.5,
        confidence_after=0.7,
    )
    proposal = debate_service.assemble_decision_proposal(
        debate_id=debate.debate_id,
        conclusion=ResearchConclusion.BUY,
        confidence=0.7,
        thesis="buy with risk controls",
        supporting_hypothesis_ids=[hypothesis.hypothesis_id],
        rejected_hypothesis_ids=[],
        evidence_ids=[evidence.evidence_id],
        risk_notes=["size small"],
    )
    debate_service.submit_risk_review(
        proposal_id=proposal.proposal_id,
        verdict=RiskVerdict.APPROVE,
        final_conclusion=ResearchConclusion.BUY,
        final_confidence=0.7,
        reasons=["risk accepted"],
    )
    assembly = debate_service.finalize_decision(proposal.proposal_id)
    decision = storage.get(Decision, assembly.decision_id)
    return storage, assembly.assembly_id, decision


def test_research_settlement_links_existing_lifecycle_and_proposes_learning() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    adapter = FixtureMarketDataAdapter(
        [
            market_bar(decision.created_at.date(), "10.00"),
            market_bar(decision.valid_until.date() + timedelta(days=1), "10.50"),
        ]
    )
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=adapter,
    )

    result = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=1),
    )
    second = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=2),
    )

    assert second.record == result.record
    assert second.outcome == result.outcome
    assert adapter.calls == 1
    assert len(storage.list(DecisionOutcome)) == 1
    assert len(storage.list(DecisionEvaluation)) == 1
    assert len(storage.list(Learning)) == 2
    assert result.record.research_session_id == (
        "rs_00000000-0000-0000-0000-000000000001"
    )
    assert result.record.assembly_id == assembly_id
    assert result.record.decision_id == decision.decision_id
    assert result.record.outcome_id == result.outcome.outcome_id
    assert result.record.evaluation_id == result.evaluation.evaluation_id
    assert result.record.review_id == result.review.review_id
    assert result.record.evidence_ids == decision.evidence_ids
    assert result.record.report_ids == ("ar_00000000-0000-0000-0000-000000000001",)
    assert result.record.hypothesis_ids == ("hp_00000000-0000-0000-0000-000000000001",)
    assert result.evaluation.final_result is EvaluationFinalResult.PASS
    assert "final conclusion correct" in result.review.review_summary
    assert "supported hypotheses" in result.review.review_summary
    assert "stronger reports" in result.review.review_summary
    assert "Debate/RiskReview" in result.review.review_summary
    assert {learning.learning_type for learning in result.learnings} == {
        LearningType.AGENT_WEIGHT_UPDATE,
        LearningType.RULE_UPDATE,
    }
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
    assert weight_learning.after["source_refs"]["evidence_ids"] == list(
        result.record.evidence_ids
    )
    assert weight_learning.after["skill_weight_adjustments"] == [
        {
            "skill_id": "manual",
            "report_id": "ar_00000000-0000-0000-0000-000000000001",
            "delta": "0.02",
            "reason": (
                "settlement passed; supported report is eligible for a small increase"
            ),
        }
    ]


def test_research_settlement_scans_due_unsettled_assemblies_idempotently() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    adapter = FixtureMarketDataAdapter(
        [
            market_bar(decision.created_at.date(), "10.00"),
            market_bar(decision.valid_until.date() + timedelta(days=1), "10.50"),
        ]
    )
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=adapter,
    )

    early = service.settle_due(as_of=decision.valid_until - timedelta(seconds=1))
    first = service.settle_due(as_of=decision.valid_until + timedelta(days=1))
    second = service.settle_due(as_of=decision.valid_until + timedelta(days=2))

    assert early == ()
    assert len(first) == 1
    assert first[0].record.assembly_id == assembly_id
    assert second == ()
    assert adapter.calls == 1
    assert len(storage.list(DecisionOutcome)) == 1
    assert len(storage.list(DecisionEvaluation)) == 1
    assert len(storage.list(Learning)) == 2


def test_research_settlement_uses_llm_only_for_learning_advice() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    llm = LearningAdvisorLLM()
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FixtureMarketDataAdapter(
            [
                market_bar(decision.created_at.date(), "10.00"),
                market_bar(decision.valid_until.date() + timedelta(days=1), "10.50"),
            ]
        ),
        llm_adapter=llm,
        llm_model="deepseek/deepseek-chat",
    )

    result = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=1),
    )
    repeated = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=2),
    )

    assert repeated.record == result.record
    assert len(llm.calls) == 1
    assert llm.calls[0]["temperature"] == 0
    weight_learning = next(
        learning
        for learning in result.learnings
        if learning.learning_type is LearningType.AGENT_WEIGHT_UPDATE
    )
    assert weight_learning.after["llm_cause_summary"] == (
        "Technical thesis was confirmed by realized return."
    )
    assert weight_learning.after["llm_evidence_references"] == [
        "ev_00000000-0000-0000-0000-000000000001"
    ]
    assert weight_learning.after["llm_report_references"] == [
        "ar_00000000-0000-0000-0000-000000000001"
    ]
    assert weight_learning.after["llm_audit"] == {
        "provider": "fake",
        "model": "deepseek/deepseek-chat",
        "request_id": "brain005_fake_request",
        "prompt_tokens": 100,
        "completion_tokens": 30,
        "total_tokens": 130,
        "latency_ms": 10,
        "raw_finish_reason": "stop",
        "extracted_payload": {
            "cause_summary": "Technical thesis was confirmed by realized return.",
            "evidence_references": ["ev_00000000-0000-0000-0000-000000000001"],
            "report_references": ["ar_00000000-0000-0000-0000-000000000001"],
            "skill_weight_adjustments": [
                {
                    "skill_id": "manual",
                    "report_id": "ar_00000000-0000-0000-0000-000000000001",
                    "delta": "0.50",
                    "reason": "Confirmed report should receive a small boost.",
                }
            ],
            "learning_recommendations": [
                "Keep the technical report slightly stronger after approval."
            ],
        },
    }
    assert weight_learning.after["skill_weight_adjustments"] == [
        {
            "skill_id": "manual",
            "report_id": "ar_00000000-0000-0000-0000-000000000001",
            "delta": "0.05",
            "reason": "Confirmed report should receive a small boost.",
        }
    ]


def test_research_settlement_completes_insufficient_data_as_inconclusive() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FixtureMarketDataAdapter([]),
    )

    result = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=1),
    )
    repeated = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=2),
    )

    assert result.outcome.status.value == "insufficient_data"
    assert result.outcome.market_data_source == "unavailable"
    assert result.evaluation.final_result.value == "inconclusive"
    assert result.learnings
    assert repeated.record == result.record
    assert len(storage.list(Learning)) == 2


def test_research_settlement_retry_recovers_missing_learning_proposal() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision_with_storage(
        FailOnceLearningStorage()
    )
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FixtureMarketDataAdapter(
            [
                market_bar(decision.created_at.date(), "10.00"),
                market_bar(decision.valid_until.date() + timedelta(days=1), "10.50"),
            ]
        ),
    )

    with pytest.raises(RuntimeError, match="transient learning save failure"):
        service.settle_assembly(
            assembly_id=assembly_id,
            as_of=decision.valid_until + timedelta(days=1),
        )
    assert len(storage.list(Learning)) == 1

    storage.fail_on_learning_save = False
    result = service.settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=2),
    )

    assert {learning.learning_type for learning in result.learnings} == {
        LearningType.AGENT_WEIGHT_UPDATE,
        LearningType.RULE_UPDATE,
    }
    assert len(storage.list(Learning)) == 2
    assert len(result.record.learning_ids) == 2


def test_research_settlement_worker_automatically_scans_due_assemblies() -> None:
    storage, decision = seed_due_research_decision()
    adapter = FixtureMarketDataAdapter(
        [
            market_bar(decision.created_at.date(), "10.00"),
            market_bar(decision.valid_until.date() + timedelta(days=1), "10.50"),
        ]
    )
    worker = ResearchSettlementWorker(
        storage=storage,
        market_data_adapter=adapter,
    )

    first = worker.run_once(as_of=datetime.now(UTC))
    second = worker.run_once(as_of=datetime.now(UTC) + timedelta(minutes=5))

    assert len(first.settled) == 1
    assert second.settled == ()
    assert adapter.calls == 1
    assert len(storage.list(DecisionOutcome)) == 1
    assert len(storage.list(DecisionEvaluation)) == 1
    assert len(storage.list(Learning)) == 2


def test_app_lifespan_starts_research_settlement_worker() -> None:
    storage, decision = seed_due_research_decision()
    adapter = FixtureMarketDataAdapter(
        [
            market_bar(decision.created_at.date(), "10.00"),
            market_bar(decision.valid_until.date() + timedelta(days=1), "10.50"),
        ]
    )

    with TestClient(
        create_app(
            storage=storage,
            market_data_adapter=adapter,
            enable_research_settlement_worker=True,
            research_settlement_interval_seconds=60,
        )
    ):
        deadline = time.monotonic() + 2
        while len(storage.list(Learning)) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)

    assert adapter.calls == 1
    assert len(storage.list(DecisionOutcome)) == 1
    assert len(storage.list(DecisionEvaluation)) == 1
    assert len(storage.list(Learning)) == 2


def seed_due_research_decision() -> tuple[InMemoryStorage, Decision]:
    storage, _assembly_id, decision = seed_finalized_research_decision()
    now = datetime.now(UTC).replace(microsecond=0)
    created_at = now - timedelta(days=4)
    valid_until = now - timedelta(days=1)
    session = storage.get(
        ResearchSession,
        "rs_00000000-0000-0000-0000-000000000001",
    )
    storage.replace(
        session.model_copy(
            update={
                "scope": ResearchScope(
                    **{
                        **session.scope.model_dump(),
                        "as_of": created_at,
                        "valid_until": valid_until,
                    }
                )
            }
        )
    )
    storage.replace(
        decision.model_copy(
            update={
                "created_at": created_at,
                "valid_until": valid_until,
            }
        )
    )
    return storage, storage.get(Decision, decision.decision_id)


def test_research_settlement_uses_session_valid_until_for_readiness() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FixtureMarketDataAdapter([]),
    )

    with pytest.raises(DecisionNotReadyForSettlementError):
        service.settle_assembly(
            assembly_id=assembly_id,
            as_of=decision.valid_until - timedelta(seconds=1),
        )


def test_research_settlement_rejects_decision_horizon_drift() -> None:
    storage, assembly_id, decision = seed_finalized_research_decision()
    storage.replace(decision.model_copy(update={"horizon": "7d"}))
    service = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FixtureMarketDataAdapter([]),
    )

    with pytest.raises(ValueError, match="ResearchSession horizon"):
        service.settle_assembly(
            assembly_id=assembly_id,
            as_of=decision.valid_until + timedelta(days=1),
        )
