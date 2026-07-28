from __future__ import annotations

import os
import signal
from collections.abc import Callable
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
from aios.kernel.scheduler_runtime import (
    SchedulerJobRun,
    SchedulerJobStatus,
    SchedulerRuntime,
)
from aios.storage.postgres import PostgresStorage
from aios.storage.postgres.evidence_repository import EvidenceRepository
from aios.vibe_trading.adapter import VibeTradingAdapter
from aios.workflows.decision_lifecycle import DecisionLifecycleService

DEFAULT_RESEARCH_WORKFLOW = "investment_committee"
DEFAULT_RESEARCH_PROVIDER = "deepseek"
DEFAULT_RESEARCH_MODEL = "deepseek/deepseek-chat"
SCHEDULER_INSTANCE_ID_ENV = "AIOS_SCHEDULER_INSTANCE_ID"


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
    storage = PostgresStorage()
    instance_id = os.getenv(SCHEDULER_INSTANCE_ID_ENV, "scheduler-main")
    serve_started_at = _now()
    _write_heartbeat(storage, instance_id, started_at=serve_started_at)
    scheduler = BlockingScheduler(timezone=os.getenv("AIOS_SCHEDULER_TZ", "UTC"))
    scheduler.add_job(
        lambda: _recorded_job_run(
            storage=storage,
            instance_id=instance_id,
            scheduler_started_at=serve_started_at,
            job_id="research_due_scan",
            func=run_research_due_once,
        ),
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
        lambda: _recorded_job_run(
            storage=storage,
            instance_id=instance_id,
            scheduler_started_at=serve_started_at,
            job_id="settlement_due_scan",
            func=run_settlement_due_once,
        ),
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


def _recorded_job_run(
    *,
    storage: PostgresStorage,
    instance_id: str,
    scheduler_started_at: datetime,
    job_id: str,
    func: Callable[[], ResearchSchedulerResult | SettlementSchedulerResult],
) -> ResearchSchedulerResult | SettlementSchedulerResult:
    started_at = _now()
    _write_heartbeat(storage, instance_id, started_at=scheduler_started_at)
    try:
        result = func()
    except Exception as exc:
        completed_at = _now()
        storage.save_scheduler_job_run(
            SchedulerJobRun(
                job_id=job_id,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                error_type=type(exc).__name__,
                error_message=_safe_scheduler_error(str(exc)),
            )
        )
        _write_heartbeat(storage, instance_id, started_at=scheduler_started_at)
        raise
    completed_at = _now()
    storage.save_scheduler_job_run(
        _successful_job_run(job_id, result, started_at, completed_at)
    )
    _write_heartbeat(storage, instance_id, started_at=scheduler_started_at)
    return result


def _successful_job_run(
    job_id: str,
    result: ResearchSchedulerResult | SettlementSchedulerResult,
    started_at: datetime,
    completed_at: datetime,
) -> SchedulerJobRun:
    if isinstance(result, ResearchSchedulerResult):
        processed = len(result.runs) + len(result.errors)
        success = len(result.runs)
        failures = len(result.errors)
    else:
        processed = len(result.settled) + len(result.errors)
        success = len(result.settled)
        failures = len(result.errors)
    status: SchedulerJobStatus = "failed" if failures else "succeeded"
    return SchedulerJobRun(
        job_id=job_id,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        processed_count=processed,
        success_count=success,
        failure_count=failures,
        result_message=f"processed={processed}; succeeded={success}; failed={failures}",
        error_message="one or more scheduled items failed" if failures else None,
    )


def _write_heartbeat(
    storage: PostgresStorage,
    instance_id: str,
    *,
    started_at: datetime,
) -> None:
    now = _now()
    storage.upsert_scheduler_runtime(
        SchedulerRuntime(
            scheduler_instance_id=instance_id,
            started_at=started_at,
            last_heartbeat_at=now,
            updated_at=now,
        )
    )


def _safe_scheduler_error(message: str) -> str:
    first_line = message.splitlines()[0] if message else "scheduler job failed"
    return first_line[:240]


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
