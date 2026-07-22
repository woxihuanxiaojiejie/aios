from __future__ import annotations

from datetime import timedelta

from tests.unit.test_research_settlement_service import (
    FixtureMarketDataAdapter,
    market_bar,
    seed_finalized_research_decision,
)

from aios.application.research_settlement import ResearchSettlementService
from aios.kernel.debate import (
    DebateRecord,
    DebateStatement,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.decision import Decision
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.settlement import ResearchSettlementRecord
from aios.kernel.watchlist import WatchlistItem
from aios.storage.postgres.storage import PostgresStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def test_postgres_research_settlement_trace_persists(
    migrated_postgres_url: str,
) -> None:
    memory_storage, assembly_id, decision = seed_finalized_research_decision()
    storage = PostgresStorage(migrated_postgres_url)
    for entity_type in (
        Evidence,
        WatchlistItem,
        ResearchSession,
        AgentReport,
        Hypothesis,
        Experiment,
        Decision,
        DebateRecord,
        DebateStatement,
        DecisionProposal,
        RiskReview,
        DecisionAssemblyRecord,
    ):
        for entity in memory_storage.list(entity_type):
            storage.save(entity)

    result = ResearchSettlementService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FixtureMarketDataAdapter(
            [
                market_bar(decision.created_at.date(), "10.00"),
                market_bar(decision.valid_until.date() + timedelta(days=1), "10.30"),
            ]
        ),
    ).settle_assembly(
        assembly_id=assembly_id,
        as_of=decision.valid_until + timedelta(days=1),
    )

    fresh_storage = PostgresStorage(migrated_postgres_url)
    assert (
        fresh_storage.get(
            ResearchSettlementRecord, result.record.research_settlement_id
        )
        == result.record
    )
    assert fresh_storage.list(Learning) == list(result.learnings)
