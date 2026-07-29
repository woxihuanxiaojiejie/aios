from datetime import UTC

import pytest
from tests.factories import (
    make_agent_report,
    make_debate,
    make_debate_statement,
    make_decision,
    make_decision_proposal,
    make_evaluation,
    make_evidence,
    make_experiment,
    make_hypothesis,
    make_learning,
    make_outcome,
    make_research_session,
    make_review,
    make_risk_review,
    make_watchlist_item,
)

from aios.kernel.base import KernelModel
from aios.kernel.debate import (
    DebateRecord,
    DebateStatement,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.decision import Decision
from aios.kernel.errors import UnsupportedEntityError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.kernel.watchlist import WatchlistItem, WatchlistStatus
from aios.storage.postgres.mapper import model_to_entity, to_model


class UnsupportedEntity(KernelModel):
    id_field = "unsupported_id"

    unsupported_id: str = "zz_unsupported"


@pytest.mark.parametrize(
    "entity",
    [
        make_evidence(),
        make_experiment(make_evidence().evidence_id),
        make_decision(
            make_experiment(make_evidence().evidence_id).experiment_id,
            make_evidence().evidence_id,
        ),
        make_review(
            make_decision(
                make_experiment(make_evidence().evidence_id).experiment_id,
                make_evidence().evidence_id,
            ).decision_id
        ),
        make_learning(
            make_review(
                make_decision(
                    make_experiment(make_evidence().evidence_id).experiment_id,
                    make_evidence().evidence_id,
                ).decision_id
            ).review_id
        ),
        make_outcome(
            make_decision(
                make_experiment(make_evidence().evidence_id).experiment_id,
                make_evidence().evidence_id,
            ).decision_id,
            make_experiment(make_evidence().evidence_id).experiment_id,
        ),
        make_evaluation(
            make_decision(
                make_experiment(make_evidence().evidence_id).experiment_id,
                make_evidence().evidence_id,
            ).decision_id,
            make_outcome(
                make_decision(
                    make_experiment(make_evidence().evidence_id).experiment_id,
                    make_evidence().evidence_id,
                ).decision_id,
                make_experiment(make_evidence().evidence_id).experiment_id,
            ).outcome_id,
            make_experiment(make_evidence().evidence_id).experiment_id,
        ),
        make_watchlist_item(),
        make_watchlist_item(
            watchlist_item_id="wl_00000000-0000-0000-0000-000000000002",
            status=WatchlistStatus.ARCHIVED,
        ),
        make_research_session(evidence_ids=(make_evidence().evidence_id,)),
        make_agent_report(evidence_ids=(make_evidence().evidence_id,)),
        make_hypothesis(evidence_ids=(make_evidence().evidence_id,)),
        make_debate(),
        make_debate_statement(),
        make_decision_proposal(),
        make_risk_review(),
    ],
)
def test_domain_to_orm_and_back(entity: KernelModel) -> None:
    model = to_model(entity)
    restored = model_to_entity(model)

    assert restored == entity


def test_jsonb_and_utc_fields_round_trip() -> None:
    evidence = make_evidence()
    restored_evidence = model_to_entity(to_model(evidence))

    assert isinstance(restored_evidence, Evidence)
    assert restored_evidence.symbols == ("NVDA", "MSFT")
    assert restored_evidence.metadata == {"form": "10-Q", "nested": {"page": 3}}
    assert restored_evidence.created_at.tzinfo is UTC

    experiment = make_experiment(evidence.evidence_id)
    restored_experiment = model_to_entity(to_model(experiment))
    assert isinstance(restored_experiment, Experiment)
    assert restored_experiment.evidence_ids == (evidence.evidence_id,)
    assert restored_experiment.parameters == {"temperature": 0, "weights": [1, 2]}

    decision = make_decision(experiment.experiment_id, evidence.evidence_id)
    restored_decision = model_to_entity(to_model(decision))
    assert isinstance(restored_decision, Decision)
    assert restored_decision.evidence_ids == (evidence.evidence_id,)

    review = make_review(decision.decision_id)
    restored_review = model_to_entity(to_model(review))
    assert isinstance(restored_review, Review)
    assert restored_review.cause_tags == ("guidance", "momentum")

    learning = make_learning(review.review_id)
    restored_learning = model_to_entity(to_model(learning))
    assert isinstance(restored_learning, Learning)
    assert restored_learning.before == {"weight": 0.4, "tags": ["guidance"]}
    assert restored_learning.after == {"weight": 0.45, "tags": ["guidance"]}

    outcome = make_outcome(decision.decision_id, experiment.experiment_id)
    restored_outcome = model_to_entity(to_model(outcome))
    assert isinstance(restored_outcome, DecisionOutcome)
    assert restored_outcome.market_data_snapshot == {"entry_trade_date": "2026-07-20"}

    evaluation = make_evaluation(
        decision.decision_id,
        outcome.outcome_id,
        experiment.experiment_id,
    )
    restored_evaluation = model_to_entity(to_model(evaluation))
    assert isinstance(restored_evaluation, DecisionEvaluation)
    assert restored_evaluation.explanation == "deterministic evaluation"

    active_watchlist = make_watchlist_item()
    restored_active_watchlist = model_to_entity(to_model(active_watchlist))
    assert isinstance(restored_active_watchlist, WatchlistItem)
    assert restored_active_watchlist.archived_at is None
    assert restored_active_watchlist.status is WatchlistStatus.ACTIVE

    archived_watchlist = make_watchlist_item(
        watchlist_item_id="wl_00000000-0000-0000-0000-000000000003",
        status=WatchlistStatus.ARCHIVED,
    )
    restored_archived_watchlist = model_to_entity(to_model(archived_watchlist))
    assert isinstance(restored_archived_watchlist, WatchlistItem)
    assert restored_archived_watchlist.status is WatchlistStatus.ARCHIVED
    assert restored_archived_watchlist.archived_at == archived_watchlist.archived_at

    research_session = make_research_session(
        evidence_ids=(evidence.evidence_id,),
    )
    restored_research_session = model_to_entity(to_model(research_session))
    assert isinstance(restored_research_session, ResearchSession)
    assert restored_research_session.scope == research_session.scope
    assert restored_research_session.evidence_ids == (evidence.evidence_id,)
    assert restored_research_session.experiment_id is None

    report = make_agent_report(evidence_ids=(evidence.evidence_id,))
    restored_report = model_to_entity(to_model(report))
    assert isinstance(restored_report, AgentReport)
    assert restored_report == report

    hypothesis = make_hypothesis(evidence_ids=(evidence.evidence_id,))
    restored_hypothesis = model_to_entity(to_model(hypothesis))
    assert isinstance(restored_hypothesis, Hypothesis)
    assert restored_hypothesis == hypothesis

    debate = make_debate()
    restored_debate = model_to_entity(to_model(debate))
    assert isinstance(restored_debate, DebateRecord)
    assert restored_debate == debate

    statement = make_debate_statement(evidence_ids=(evidence.evidence_id,))
    restored_statement = model_to_entity(to_model(statement))
    assert isinstance(restored_statement, DebateStatement)
    assert restored_statement == statement

    proposal = make_decision_proposal(evidence_ids=(evidence.evidence_id,))
    restored_proposal = model_to_entity(to_model(proposal))
    assert isinstance(restored_proposal, DecisionProposal)
    assert restored_proposal == proposal

    risk = make_risk_review()
    restored_risk = model_to_entity(to_model(risk))
    assert isinstance(restored_risk, RiskReview)
    assert restored_risk == risk


def test_unsupported_entity_mapping_fails() -> None:
    with pytest.raises(UnsupportedEntityError, match="UnsupportedEntity"):
        to_model(UnsupportedEntity())
