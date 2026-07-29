from __future__ import annotations

import os
import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from aios import __version__
from aios.adapters.storage import Storage
from aios.application.research_scheduler import research_due_items
from aios.application.settlement_scheduler import settlement_due_executions
from aios.integrations.litellm.adapter import validate_llm_runtime_config
from aios.integrations.litellm.errors import LLMConfigurationError
from aios.kernel.scheduler_runtime import SchedulerJobRun
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres import PostgresStorage

SystemStatus = Literal[
    "healthy",
    "degraded",
    "unavailable",
    "not_configured",
    "unknown",
]

FIXED_SCHEDULER_JOBS = ("research_due_scan", "settlement_due_scan")
SENSITIVE_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password|authorization|database[_-]?url|traceback)"
    r"[^,\n;]*",
    re.IGNORECASE,
)


class ApplicationStatus(BaseModel):
    status: SystemStatus
    name: str
    version: str | None
    commit: str | None
    environment: str | None
    started_at: datetime | None
    checked_at: datetime
    message: str | None = None


class DatabaseStatus(BaseModel):
    status: SystemStatus
    backend: str
    checked_at: datetime
    latency_ms: int | None
    message: str | None = None


class SchedulerStatus(BaseModel):
    status: SystemStatus
    running: bool
    last_heartbeat_at: datetime | None
    heartbeat_age_seconds: int | None
    message: str | None = None


class SchedulerJobStatus(BaseModel):
    status: SystemStatus
    enabled: bool
    last_started_at: datetime | None
    last_completed_at: datetime | None
    last_result: str | None
    last_error: str | None
    processed_count: int | None = None
    success_count: int | None = None
    failure_count: int | None = None


class QueueStatus(BaseModel):
    research_due: int
    settlement_due: int
    failed_research_runs: int
    resumable_research_runs: int


class ProviderStatus(BaseModel):
    provider: str
    model: str | None
    configured: bool
    status: SystemStatus
    message: str | None = None


class SystemStatusSummary(BaseModel):
    generated_at: datetime
    overall_status: SystemStatus
    application: ApplicationStatus
    database: DatabaseStatus
    scheduler: SchedulerStatus
    jobs: dict[str, SchedulerJobStatus]
    queues: QueueStatus
    providers: list[ProviderStatus]
    issues: list[str]


class SystemStatusService:
    def __init__(
        self,
        *,
        storage: Storage,
        environ: Mapping[str, str] | None = None,
        started_at: datetime | None = None,
    ) -> None:
        self._storage = storage
        self._environ = environ if environ is not None else os.environ
        self._started_at = started_at

    def build(self, *, as_of: datetime | None = None) -> SystemStatusSummary:
        generated_at = as_of or datetime.now(UTC)
        application = self._application_status(generated_at)
        database = self._database_status(generated_at)
        scheduler = self._scheduler_status(generated_at)
        jobs = self._job_statuses()
        queues = self._queue_status(generated_at)
        providers = [self._provider_status()]
        issues = self._issues(database, scheduler, jobs, queues, providers)
        return SystemStatusSummary(
            generated_at=generated_at,
            overall_status=self._overall_status(
                application=application,
                database=database,
                scheduler=scheduler,
                jobs=jobs,
                queues=queues,
                providers=providers,
            ),
            application=application,
            database=database,
            scheduler=scheduler,
            jobs=jobs,
            queues=queues,
            providers=providers,
            issues=issues,
        )

    def _application_status(self, checked_at: datetime) -> ApplicationStatus:
        commit = _env_first(self._environ, ("AIOS_GIT_COMMIT", "GIT_COMMIT"))
        return ApplicationStatus(
            status="healthy",
            name="AIOS",
            version=__version__,
            commit=commit,
            environment=_env_first(self._environ, ("AIOS_ENVIRONMENT", "ENVIRONMENT")),
            started_at=self._started_at,
            checked_at=checked_at,
            message=None if commit else "git commit was not injected",
        )

    def _database_status(self, checked_at: datetime) -> DatabaseStatus:
        started = time.perf_counter()
        try:
            self._storage.health_check()
        except Exception:
            return DatabaseStatus(
                status="unavailable",
                backend=_storage_backend(self._storage),
                checked_at=checked_at,
                latency_ms=None,
                message="database health check failed",
            )
        return DatabaseStatus(
            status="healthy",
            backend=_storage_backend(self._storage),
            checked_at=checked_at,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _scheduler_status(self, generated_at: datetime) -> SchedulerStatus:
        try:
            runtime = self._storage.get_latest_scheduler_runtime()
        except Exception:
            return SchedulerStatus(
                status="unavailable",
                running=False,
                last_heartbeat_at=None,
                heartbeat_age_seconds=None,
                message="scheduler heartbeat could not be read",
            )
        if runtime is None:
            return SchedulerStatus(
                status="unknown",
                running=False,
                last_heartbeat_at=None,
                heartbeat_age_seconds=None,
                message="scheduler heartbeat has not been recorded",
            )
        age = int((generated_at - runtime.last_heartbeat_at).total_seconds())
        if age <= _heartbeat_threshold_seconds(self._environ):
            return SchedulerStatus(
                status="healthy",
                running=True,
                last_heartbeat_at=runtime.last_heartbeat_at,
                heartbeat_age_seconds=max(0, age),
            )
        return SchedulerStatus(
            status="unavailable",
            running=False,
            last_heartbeat_at=runtime.last_heartbeat_at,
            heartbeat_age_seconds=max(0, age),
            message="scheduler heartbeat is expired",
        )

    def _job_statuses(self) -> dict[str, SchedulerJobStatus]:
        return {job_id: self._job_status(job_id) for job_id in FIXED_SCHEDULER_JOBS}

    def _job_status(self, job_id: str) -> SchedulerJobStatus:
        try:
            run = self._storage.get_latest_scheduler_job_run(job_id)
        except Exception:
            return SchedulerJobStatus(
                status="unknown",
                enabled=True,
                last_started_at=None,
                last_completed_at=None,
                last_result=None,
                last_error="job status could not be read",
            )
        if run is None:
            return SchedulerJobStatus(
                status="unknown",
                enabled=True,
                last_started_at=None,
                last_completed_at=None,
                last_result=None,
                last_error=None,
            )
        return _job_status_from_run(run)

    def _queue_status(self, as_of: datetime) -> QueueStatus:
        runs = self._storage.list_research_runs()
        failed = [run for run in runs if run.status == "failed"]
        resumable = [run for run in runs if run.status != "completed"]
        return QueueStatus(
            research_due=len(research_due_items(self._storage, as_of)),
            settlement_due=len(settlement_due_executions(self._storage, as_of)),
            failed_research_runs=len(failed),
            resumable_research_runs=len(resumable),
        )

    def _provider_status(self) -> ProviderStatus:
        model = self._environ.get("AIOS_EXTERNAL_LLM_MODEL", "").strip()
        if not model:
            return ProviderStatus(
                provider="unknown",
                model=None,
                configured=False,
                status="not_configured",
                message="AIOS_EXTERNAL_LLM_MODEL is not set",
            )
        provider = model.split("/", maxsplit=1)[0] if "/" in model else "unknown"
        try:
            validate_llm_runtime_config(model, self._environ)
        except LLMConfigurationError as exc:
            missing_credentials = "must be set for" in str(exc)
            return ProviderStatus(
                provider=provider,
                model=model,
                configured=False,
                status="not_configured" if missing_credentials else "degraded",
                message=(
                    "provider credentials are not configured"
                    if missing_credentials
                    else _safe_message(str(exc))
                ),
            )
        return ProviderStatus(
            provider=provider,
            model=model,
            configured=True,
            status="healthy",
        )

    def _overall_status(
        self,
        *,
        application: ApplicationStatus,
        database: DatabaseStatus,
        scheduler: SchedulerStatus,
        jobs: dict[str, SchedulerJobStatus],
        queues: QueueStatus,
        providers: list[ProviderStatus],
    ) -> SystemStatus:
        if application.status == "unavailable" or database.status == "unavailable":
            return "unavailable"
        if (
            scheduler.status in {"degraded", "unavailable"}
            or any(job.status == "degraded" for job in jobs.values())
            or any(provider.status == "degraded" for provider in providers)
            or queues.failed_research_runs > 0
            or queues.resumable_research_runs > 0
            or queues.settlement_due > 0
        ):
            return "degraded"
        return "healthy"

    def _issues(
        self,
        database: DatabaseStatus,
        scheduler: SchedulerStatus,
        jobs: dict[str, SchedulerJobStatus],
        queues: QueueStatus,
        providers: list[ProviderStatus],
    ) -> list[str]:
        issues: list[str] = []
        if database.status == "unavailable":
            issues.append("Database health check failed")
        if scheduler.status == "unavailable":
            issues.append("Scheduler heartbeat is expired or unavailable")
        for job_id, job in jobs.items():
            if job.status == "degraded":
                issues.append(f"{job_id} last run failed")
        for provider in providers:
            if provider.status == "degraded":
                issues.append(f"{provider.provider} provider configuration is invalid")
        if queues.failed_research_runs:
            issues.append("Failed research runs require attention")
        if queues.resumable_research_runs:
            issues.append("Resumable research runs require attention")
        if queues.settlement_due:
            issues.append("Settlement work is due")
        return issues


def _job_status_from_run(run: SchedulerJobRun) -> SchedulerJobStatus:
    if run.status == "succeeded":
        return SchedulerJobStatus(
            status="healthy",
            enabled=True,
            last_started_at=run.started_at,
            last_completed_at=run.completed_at,
            last_result=run.result_message,
            last_error=None,
            processed_count=run.processed_count,
            success_count=run.success_count,
            failure_count=run.failure_count,
        )
    return SchedulerJobStatus(
        status="degraded",
        enabled=True,
        last_started_at=run.started_at,
        last_completed_at=run.completed_at,
        last_result=run.result_message,
        last_error=_safe_message(run.error_message or run.error_type or "job failed"),
        processed_count=run.processed_count,
        success_count=run.success_count,
        failure_count=run.failure_count,
    )


def _storage_backend(storage: Storage) -> str:
    if isinstance(storage, PostgresStorage):
        return "postgresql"
    if isinstance(storage, InMemoryStorage):
        return "in_memory"
    return "unknown"


def _heartbeat_threshold_seconds(environ: Mapping[str, str]) -> int:
    research_interval = _interval_seconds_from_env(
        environ,
        "AIOS_RESEARCH_SCAN_INTERVAL_SECONDS",
        300,
    )
    settlement_interval = _interval_seconds_from_env(
        environ,
        "AIOS_SETTLEMENT_SCAN_INTERVAL_SECONDS",
        300,
    )
    misfire_grace = _interval_seconds_from_env(
        environ,
        "AIOS_SCHEDULER_MISFIRE_GRACE_SECONDS",
        300,
    )
    return max(research_interval, settlement_interval, misfire_grace) * 3


def _interval_seconds_from_env(
    environ: Mapping[str, str],
    env_name: str,
    default: int,
) -> int:
    value = environ.get(env_name)
    if not value:
        return default
    return max(1, int(value))


def _env_first(environ: Mapping[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        value = environ.get(name, "").strip()
        if value:
            return value
    return None


def _safe_message(message: str) -> str:
    cleaned = SENSITIVE_PATTERN.sub("[redacted]", message)
    first_line = cleaned.splitlines()[0] if cleaned else ""
    return first_line[:240]
