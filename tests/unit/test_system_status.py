from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from tests.factories import make_watchlist_item
from tests.unit.test_scheduler_runtime import _waiting_settlement_execution

from aios.api.app import create_app
from aios.application.system_status import SystemStatusService
from aios.kernel.research_run import ResearchRun
from aios.kernel.scheduler_runtime import SchedulerJobRun, SchedulerRuntime
from aios.storage.memory import InMemoryStorage

AS_OF = datetime(2026, 7, 28, 8, 0, tzinfo=UTC)


def test_system_status_api_returns_empty_database_status_without_secrets(
    monkeypatch,
) -> None:
    storage = InMemoryStorage()
    app = create_app(storage=storage)
    monkeypatch.setenv("AIOS_EXTERNAL_LLM_MODEL", "")
    app.state.started_at = datetime(2026, 7, 28, 7, 59, tzinfo=UTC)

    response = TestClient(app).get("/api/v1/system/status")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "healthy"
    assert body["application"]["status"] == "healthy"
    assert body["application"]["version"] == "0.1.0"
    assert body["application"]["commit"] is None
    assert body["database"]["backend"] == "in_memory"
    assert body["database"]["status"] == "healthy"
    assert body["scheduler"]["status"] == "unknown"
    assert body["scheduler"]["running"] is False
    assert body["queues"] == {
        "research_due": 0,
        "settlement_due": 0,
        "failed_research_runs": 0,
        "resumable_research_runs": 0,
    }
    assert body["providers"] == [
        {
            "provider": "unknown",
            "model": None,
            "configured": False,
            "status": "not_configured",
            "message": "AIOS_EXTERNAL_LLM_MODEL is not set",
        }
    ]
    serialized = response.text.lower()
    for sensitive in (
        "api_key",
        "secret",
        "token",
        "password",
        "authorization",
        "database_url",
    ):
        assert sensitive not in serialized


def test_system_status_counts_due_and_research_failures_from_business_sources() -> None:
    as_of = datetime(2026, 8, 5, 8, 0, tzinfo=UTC)
    storage, _execution, _adapter = _waiting_settlement_execution()
    due = make_watchlist_item(
        watchlist_item_id="wl_due",
        symbol="600519",
    ).model_copy(
        update={
            "auto_research_enabled": True,
            "next_run_at": as_of - timedelta(minutes=1),
        }
    )
    not_due = make_watchlist_item(
        watchlist_item_id="wl_not_due",
        symbol="000001",
    ).model_copy(
        update={
            "auto_research_enabled": True,
            "next_run_at": as_of + timedelta(minutes=1),
        }
    )
    for item in (due, not_due):
        storage.save(item)
    storage.save(
        ResearchRun(
            run_id="run_failed",
            watchlist_item_id=due.watchlist_item_id,
            workflow="investment_committee",
            input_params={},
            current_stage="failed",
            status="failed",
            failed_stage="evidence",
            error_type="RuntimeError",
            error="provider timeout",
            created_at=as_of - timedelta(minutes=5),
            updated_at=as_of - timedelta(minutes=4),
            finished_at=as_of - timedelta(minutes=4),
        )
    )
    storage.save(
        ResearchRun(
            run_id="run_running",
            watchlist_item_id=not_due.watchlist_item_id,
            workflow="investment_committee",
            input_params={},
            current_stage="evidence",
            status="running",
            created_at=as_of - timedelta(hours=1),
            updated_at=as_of - timedelta(hours=1),
        )
    )
    summary = SystemStatusService(storage=storage, environ={}).build(as_of=as_of)

    assert summary.queues.research_due == 1
    assert summary.queues.settlement_due == 1
    assert summary.queues.failed_research_runs == 1
    assert summary.queues.resumable_research_runs == 2
    assert summary.overall_status == "degraded"


def test_scheduler_heartbeat_and_job_records_drive_status() -> None:
    storage = InMemoryStorage()
    storage.upsert_scheduler_runtime(
        SchedulerRuntime(
            scheduler_instance_id="scheduler-main",
            started_at=AS_OF - timedelta(minutes=2),
            last_heartbeat_at=AS_OF - timedelta(seconds=30),
            updated_at=AS_OF - timedelta(seconds=30),
        )
    )
    storage.save_scheduler_job_run(
        SchedulerJobRun(
            job_run_id="sjr_research_ok",
            job_id="research_due_scan",
            status="succeeded",
            started_at=AS_OF - timedelta(minutes=1),
            completed_at=AS_OF - timedelta(seconds=50),
            processed_count=3,
            success_count=3,
            failure_count=0,
            result_message="processed 3 watchlist items",
        )
    )
    storage.save_scheduler_job_run(
        SchedulerJobRun(
            job_run_id="sjr_settlement_failed",
            job_id="settlement_due_scan",
            status="failed",
            started_at=AS_OF - timedelta(minutes=1),
            completed_at=AS_OF - timedelta(seconds=40),
            processed_count=1,
            success_count=0,
            failure_count=1,
            error_type="RuntimeError",
            error_message="Authorization: Bearer secret-token\nTraceback: hidden",
        )
    )

    summary = SystemStatusService(storage=storage, environ={}).build(as_of=AS_OF)

    assert summary.scheduler.status == "healthy"
    assert summary.scheduler.running is True
    assert summary.scheduler.heartbeat_age_seconds == 30
    assert summary.jobs["research_due_scan"].status == "healthy"
    assert (
        summary.jobs["research_due_scan"].last_result == "processed 3 watchlist items"
    )
    assert summary.jobs["settlement_due_scan"].status == "degraded"
    assert "secret-token" not in str(summary.jobs["settlement_due_scan"].last_error)
    assert "Traceback" not in str(summary.jobs["settlement_due_scan"].last_error)
    assert summary.overall_status == "degraded"


def test_scheduler_heartbeat_expiry_marks_scheduler_unavailable() -> None:
    storage = InMemoryStorage()
    storage.upsert_scheduler_runtime(
        SchedulerRuntime(
            scheduler_instance_id="scheduler-main",
            started_at=AS_OF - timedelta(minutes=20),
            last_heartbeat_at=AS_OF - timedelta(minutes=16),
            updated_at=AS_OF - timedelta(minutes=16),
        )
    )

    summary = SystemStatusService(storage=storage, environ={}).build(as_of=AS_OF)

    assert summary.scheduler.status == "unavailable"
    assert summary.scheduler.running is False
    assert summary.overall_status == "degraded"


def test_provider_status_uses_local_validation_without_returning_key(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AIOS_EXTERNAL_LLM_MODEL", "deepseek/deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "real-key-not-returned")
    storage = InMemoryStorage()

    summary = SystemStatusService(storage=storage).build(as_of=AS_OF)

    assert summary.providers[0].provider == "deepseek"
    assert summary.providers[0].configured is True
    assert summary.providers[0].status == "healthy"
    assert "real-key-not-returned" not in summary.model_dump_json()


def test_provider_invalid_configuration_is_degraded() -> None:
    storage = InMemoryStorage()

    summary = SystemStatusService(
        storage=storage,
        environ={"AIOS_EXTERNAL_LLM_MODEL": "unsupported/model", "TOKEN": "secret"},
    ).build(as_of=AS_OF)

    assert summary.providers[0].provider == "unsupported"
    assert summary.providers[0].configured is False
    assert summary.providers[0].status == "degraded"
    assert "TOKEN" not in summary.model_dump_json()


def test_database_failure_is_reported_without_leaking_exception() -> None:
    summary = SystemStatusService(
        storage=FailingHealthStorage(),
        environ={},
    ).build(as_of=AS_OF)

    assert summary.database.status == "unavailable"
    assert summary.overall_status == "unavailable"
    assert summary.database.message == "database health check failed"


class FailingHealthStorage(InMemoryStorage):
    def health_check(self) -> Any:
        raise RuntimeError("password=secret database_url=postgres://user:pass@host/db")
