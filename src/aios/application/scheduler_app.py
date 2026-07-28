from __future__ import annotations

import os
import signal
from dataclasses import dataclass
from datetime import UTC, datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

from aios.api.routes import brain002
from aios.application.research_runtime import ResearchRuntimeService
from aios.application.research_scheduler import (
    ResearchSchedulerResult,
    ResearchSchedulerService,
)
from aios.application.settlement_scheduler import (
    SettlementSchedulerResult,
    SettlementSchedulerService,
)
from aios.integrations.akshare.adapter import AKShareMarketDataAdapter
from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.integrations.trading_calendar import MarketTradingCalendar
from aios.storage.postgres import PostgresStorage
from aios.storage.postgres.evidence_repository import EvidenceRepository
from aios.vibe_trading.adapter import VibeTradingAdapter
from aios.workflows.decision_lifecycle import DecisionLifecycleService

DEFAULT_RESEARCH_WORKFLOW = "investment_committee"
DEFAULT_RESEARCH_PROVIDER = "deepseek"
DEFAULT_RESEARCH_MODEL = "deepseek/deepseek-chat"


@dataclass(frozen=True)
class SchedulerRunOnceResult:
    research: ResearchSchedulerResult
    settlement: SettlementSchedulerResult


def run_research_due_once() -> ResearchSchedulerResult:
    _load_runtime_env()
    storage = PostgresStorage()
    adapter = AKShareMarketDataAdapter()
    runtime = ResearchRuntimeService(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=adapter,
        vibe_trading_adapter=VibeTradingAdapter(),
        llm_adapter=LiteLLMAdapter(),
        brain002_registry=brain002.default_brain002_registry(),
        brain_evidence_repository=EvidenceRepository(storage.database_url),
    )
    return ResearchSchedulerService(
        storage=storage,
        runtime=runtime,
        trading_calendar=MarketTradingCalendar(),
        workflow=os.getenv("AIOS_RESEARCH_WORKFLOW", DEFAULT_RESEARCH_WORKFLOW),
        provider=os.getenv("AIOS_RESEARCH_PROVIDER", DEFAULT_RESEARCH_PROVIDER),
        model=os.getenv("AIOS_RESEARCH_MODEL", DEFAULT_RESEARCH_MODEL),
    ).run_due_once(as_of=_now())


def run_settlement_due_once() -> SettlementSchedulerResult:
    _load_runtime_env()
    storage = PostgresStorage()
    return SettlementSchedulerService(
        storage=storage,
        market_data_adapter=AKShareMarketDataAdapter(),
    ).run_due_once(as_of=_now())


def run_all_due_once() -> SchedulerRunOnceResult:
    return SchedulerRunOnceResult(
        research=run_research_due_once(),
        settlement=run_settlement_due_once(),
    )


def serve() -> None:
    _load_runtime_env()
    scheduler = BlockingScheduler(timezone=os.getenv("AIOS_SCHEDULER_TZ", "UTC"))
    scheduler.add_job(
        run_research_due_once,
        trigger=IntervalTrigger(
            seconds=_interval_seconds("AIOS_RESEARCH_SCAN_INTERVAL_SECONDS", 300)
        ),
        id="research_due_scan",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=_misfire_grace_time(),
    )
    scheduler.add_job(
        run_settlement_due_once,
        trigger=IntervalTrigger(
            seconds=_interval_seconds("AIOS_SETTLEMENT_SCAN_INTERVAL_SECONDS", 300)
        ),
        id="settlement_due_scan",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=_misfire_grace_time(),
    )

    def shutdown(_signum: int, _frame: object) -> None:
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    scheduler.start()


def _interval_seconds(env_name: str, default: int) -> int:
    value = os.getenv(env_name)
    if not value:
        return default
    return max(1, int(value))


def _misfire_grace_time() -> int:
    return _interval_seconds("AIOS_SCHEDULER_MISFIRE_GRACE_SECONDS", 300)


def _now() -> datetime:
    return datetime.now(UTC)


def _load_runtime_env() -> None:
    load_dotenv(".env", override=True)
