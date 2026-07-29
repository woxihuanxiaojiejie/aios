from __future__ import annotations

from aios import cli
from aios.application.research_scheduler import ResearchSchedulerResult
from aios.application.scheduler_app import SchedulerRunOnceResult
from aios.application.settlement_scheduler import SettlementSchedulerResult


def test_cli_scheduler_run_once_uses_existing_console_entry(
    monkeypatch,
    capsys,
) -> None:
    def run_all_due_once() -> SchedulerRunOnceResult:
        return SchedulerRunOnceResult(
            research=ResearchSchedulerResult(runs=(), errors=()),
            settlement=SettlementSchedulerResult(settled=(), errors=()),
        )

    monkeypatch.setattr(cli, "run_all_due_once", run_all_due_once)
    monkeypatch.setattr("sys.argv", ["aios", "scheduler", "run-once"])

    cli.main()

    assert "research_runs=0" in capsys.readouterr().out


def test_cli_settlement_run_once_uses_scheduler_service(monkeypatch, capsys) -> None:
    def run_settlement_due_once() -> SettlementSchedulerResult:
        return SettlementSchedulerResult(settled=(), errors=())

    monkeypatch.setattr(cli, "run_settlement_due_once", run_settlement_due_once)
    monkeypatch.setattr("sys.argv", ["aios", "settlement", "run-once"])

    cli.main()

    assert capsys.readouterr().out.strip() == "settlements=0 errors=0"
