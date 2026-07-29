"""Tests for the Vibe-Trading adapter boundary.

These tests do not run Vibe-Trading. AIOS only keeps a narrow optional boundary
until a stable Vibe-Trading MCP/API output contract is wired.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture
def sample_as_of() -> datetime:
    return datetime(2026, 7, 17, 8, 0, tzinfo=UTC)


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "symbol": "000001.SZ",
        "market": "CN_A",
        "as_of": "2026-07-17T08:00:00Z",
        "workflow": "investment_committee",
        "vibe_run_id": "vr_test",
        "model_provider": "fake",
        "model_name": "fake-model",
        "started_at": "2026-07-17T08:00:00Z",
        "completed_at": "2026-07-17T08:01:00Z",
        "final_decision": {
            "signal": "hold",
            "confidence": 0.5,
            "time_horizon_days": 3,
            "rationale": "wait",
        },
    }
    payload.update(overrides)
    return payload


def _committee_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "target": "600519",
        "market": "CN",
        "horizon_days": 3,
        "decision": "WAIT",
        "summary": "Final decision: WAIT for a clearer three day setup.",
        "raw_report": (
            "Final Report\nDecision: WAIT\nTokens: input=10 output=20 total=30"
        ),
        "metadata": {"token_input": 10, "token_output": 20, "token_total": 30},
    }
    payload.update(overrides)
    return payload


def _run_adapter(sample_as_of: datetime) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    VibeTradingAdapter().analyze(
        symbol="000001.SZ",
        market="CN_A",
        as_of=sample_as_of,
        horizon_days=3,
        workflow="investment_committee",
        provider="fake",
        model="fake-model",
    )


def test_default_construction() -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    adapter = VibeTradingAdapter()
    assert adapter._config_overrides == {}


def test_with_overrides() -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    adapter = VibeTradingAdapter(config_overrides={"command": "vibe-trading"})
    assert adapter._config_overrides == {"command": "vibe-trading"}


def test_resolve_command_from_env_absolute_path(monkeypatch: Any) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")

    assert VibeTradingAdapter._resolve_command() == ["/opt/vibe/bin/vibe-trading"]


def test_resolve_command_from_env_with_prefix_args(monkeypatch: Any) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")

    assert VibeTradingAdapter._resolve_command() == ["/opt/vibe/bin/vibe-trading"]


def test_resolve_command_from_path(monkeypatch: Any) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    monkeypatch.delenv("VIBE_TRADING_EXECUTABLE", raising=False)

    with patch("aios.vibe_trading.adapter.shutil.which", return_value="/bin/vibe"):
        assert VibeTradingAdapter._resolve_command() == ["/bin/vibe"]


def test_resolve_command_from_local_repo_fallback(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    fallback = tmp_path / "Vibe-Trading" / ".venv" / "bin" / "vibe-trading"
    fallback.parent.mkdir(parents=True)
    fallback.touch()
    monkeypatch.delenv("VIBE_TRADING_EXECUTABLE", raising=False)
    monkeypatch.delenv("AIOS_VIBE_TRADING_PROJECT_DIR", raising=False)

    with (
        patch("aios.vibe_trading.adapter.shutil.which", return_value=None),
        patch.object(
            VibeTradingAdapter, "_local_fallback_command", return_value=fallback
        ),
    ):
        assert VibeTradingAdapter._resolve_command() == ["uv", "run", "vibe-trading"]


def test_resolve_command_raises_when_missing(monkeypatch: Any, tmp_path: Path) -> None:
    from aios.vibe_trading.adapter import (
        VibeTradingAdapter,
        VibeTradingConfigurationError,
    )

    fallback = tmp_path / "missing" / "vibe-trading"
    monkeypatch.delenv("VIBE_TRADING_EXECUTABLE", raising=False)
    monkeypatch.delenv("AIOS_VIBE_TRADING_PROJECT_DIR", raising=False)

    with (
        patch("aios.vibe_trading.adapter.shutil.which", return_value=None),
        patch.object(
            VibeTradingAdapter, "_local_fallback_command", return_value=fallback
        ),
        pytest.raises(VibeTradingConfigurationError) as exc_info,
    ):
        VibeTradingAdapter._resolve_command()

    message = str(exc_info.value)
    assert "VIBE_TRADING_EXECUTABLE" in message
    assert "PATH lookup result" in message
    assert str(fallback) in message


def test_format_trade_date_utc(sample_as_of: datetime) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    result = VibeTradingAdapter._format_trade_date(sample_as_of)
    assert result == "2026-07-17"


def test_format_trade_date_rejects_naive() -> None:
    from aios.vibe_trading.adapter import (
        VibeTradingAdapter,
        VibeTradingConfigurationError,
    )

    with pytest.raises(VibeTradingConfigurationError, match="timezone-aware"):
        VibeTradingAdapter._format_trade_date(datetime(2026, 7, 17, 8, 0))


def test_analyze_rejects_unstructured_cli_output(
    sample_as_of: datetime,
    monkeypatch: Any,
) -> None:
    from aios.vibe_trading.adapter import VibeTradingRuntimeError

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    with (
        patch(
            "aios.vibe_trading.adapter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=["vibe-trading"],
                returncode=0,
                stdout="plain text",
                stderr="diagnostic",
            ),
        ),
        pytest.raises(VibeTradingRuntimeError) as exc_info,
    ):
        _run_adapter(sample_as_of)

    message = str(exc_info.value)
    assert "parse_failed" in message
    assert "plain text" in message
    assert "diagnostic" in message


def test_analyze_runs_cli_protocol_with_string_user_vars(
    sample_as_of: datetime,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")

    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=json.dumps(_valid_payload()),
            stderr="",
        ),
    ) as run:
        _run_adapter(sample_as_of)

    command = run.call_args.args[0]
    kwargs = run.call_args.kwargs
    assert command[:5] == [
        "/opt/vibe/bin/vibe-trading",
        "--json",
        "--no-rich",
        "--swarm-run",
        "investment_committee",
    ]
    assert isinstance(command, list)
    assert kwargs.get("shell") is False
    variables = json.loads(command[5])
    assert variables["target"] == "000001.SZ"
    assert variables["market"] == "CN_A"
    assert variables["horizon_days"] == "3"
    assert variables["ticker"] == "000001.SZ"
    assert variables["symbol"] == "000001.SZ"
    assert all(isinstance(key, str) for key in variables)
    assert all(isinstance(value, str) for value in variables.values())


def test_analyze_accepts_pure_json_stdout(
    sample_as_of: datetime,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")

    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=json.dumps(_valid_payload(vibe_run_id="vr_json")),
            stderr="",
        ),
    ):
        from aios.vibe_trading.adapter import VibeTradingAdapter

        result = VibeTradingAdapter().analyze(
            symbol="000001.SZ",
            market="CN_A",
            as_of=sample_as_of,
            horizon_days=3,
            workflow="investment_committee",
            provider="fake",
            model="fake-model",
        )

    assert result.vibe_run_id == "vr_json"


def test_analyze_extracts_final_schema_valid_json_object_from_log_prefixed_stdout(
    sample_as_of: datetime,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    stdout = (
        "Starting swarm...\n"
        "Variables: {'target': '000001.SZ'}\n"
        f"{json.dumps(_valid_payload(vibe_run_id='vr_prefixed'))}\n"
    )

    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=stdout,
            stderr="",
        ),
    ):
        from aios.vibe_trading.adapter import VibeTradingAdapter

        result = VibeTradingAdapter().analyze(
            symbol="000001.SZ",
            market="CN_A",
            as_of=sample_as_of,
            horizon_days=3,
            workflow="investment_committee",
            provider="fake",
            model="fake-model",
        )

    assert result.vibe_run_id == "vr_prefixed"


def test_analyze_rejects_success_false_even_with_exit_code_zero(
    sample_as_of: datetime,
    monkeypatch: Any,
) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter, VibeTradingRuntimeError

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    payload = _valid_payload(success=False, error="preset validation failed")

    with (
        patch(
            "aios.vibe_trading.adapter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=["/opt/vibe/bin/vibe-trading"],
                returncode=0,
                stdout=json.dumps(payload),
                stderr="",
            ),
        ),
        pytest.raises(VibeTradingRuntimeError, match="preset validation failed"),
    ):
        VibeTradingAdapter().analyze(
            symbol="000001.SZ",
            market="CN_A",
            as_of=sample_as_of,
            horizon_days=3,
            workflow="investment_committee",
            provider="fake",
            model="fake-model",
        )


def test_cli_adapter_persists_successful_json_run(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    stdout = json.dumps(_committee_payload())
    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=stdout,
            stderr="",
        ),
    ):
        record = VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    assert record.provider_name == "vibe_trading"
    assert record.status == "completed"
    assert record.exit_code == 0
    assert record.stdout_raw == stdout
    assert record.output_hash == hashlib.sha256(stdout.encode()).hexdigest()
    assert record.parsed_output is not None
    assert record.parsed_output["decision"] == "WAIT"
    saved = tmp_path / f"{record.run_id}.json"
    assert saved.exists()
    saved_payload = json.loads(saved.read_text())
    assert saved_payload["run_id"] == record.run_id
    assert saved_payload["stdout_raw"] == stdout


def test_cli_adapter_extracts_json_after_logs(monkeypatch: Any, tmp_path: Path) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    stdout = "Starting swarm\nVariables\n" + json.dumps(_committee_payload())
    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=stdout,
            stderr="",
        ),
    ):
        record = VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    assert record.status == "completed"
    assert record.parsed_output is not None
    assert record.parsed_output["summary"].startswith("Final decision")
    assert record.stdout_raw == stdout


def test_cli_adapter_preserves_markdown_final_report_without_faking_json(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    stdout = (
        "Starting swarm\n"
        "Final Report\n"
        "For the next 3 days, final decision: WAIT.\n"
        "Bull: resilient brand.\n"
        "Bear: weak current price data source.\n"
        "COMPLETED\n"
        "Tokens: input=11 output=22 total=33\n"
    )
    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=stdout,
            stderr="",
        ),
    ):
        record = VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    assert record.status == "completed"
    assert record.parsed_output is not None
    assert record.parsed_output["decision"] == "WAIT"
    assert record.parsed_output["raw_report"].startswith("Final Report")
    assert record.stdout_raw == stdout
    assert record.token_usage == {"input": 11, "output": 22, "total": 33}


def test_cli_adapter_prefers_final_report_over_variables_json(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    stdout = (
        'Variables: {"target":"600519","market":"CN","horizon_days":"3"}\n'
        "── Final Report ──\n"
        "# PM Final Investment Decision\n\n"
        "## PM最终决定\n\n"
        "> ### ✅ 决定\uff1a做多 — 分阶段建仓\n"
        "COMPLETED  Time: 9m 53s\n"
        "Tokens: ~518,469 (in: 472,156 out: 46,313)\n"
    )
    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=stdout,
            stderr="",
        ),
    ):
        record = VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    assert record.status == "completed"
    assert record.parsed_output is not None
    assert record.parsed_output["decision"] == "BUY"
    assert record.parsed_output["raw_report"].startswith("Final Report")


def test_cli_adapter_parses_cautious_long_action_from_final_report() -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    parsed = VibeTradingCLIAdapter._normalise_parsed_output(
        payload={},
        raw_report=(
            "Final Report\n"
            "## PM DECISION STATEMENT\n"
            "**ACTION: CAUTIOUS LONG — INITIATE SCOUT POSITION AT 4.0% OF NAV**"
        ),
        target="600519",
        market="CN",
        horizon_days=3,
        duration_seconds=1.0,
        token_usage=None,
    )

    assert parsed["decision"] == "BUY"


def test_cli_adapter_parses_markdown_bold_chinese_decision() -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    parsed = VibeTradingCLIAdapter._normalise_parsed_output(
        payload={},
        raw_report="Final Report\n**决策**: **战术性做多\uff0c持有期 30-60 天**",
        target="600519",
        market="CN",
        horizon_days=3,
        duration_seconds=1.0,
        token_usage=None,
    )

    assert parsed["decision"] == "BUY"


def test_cli_adapter_persists_nonzero_exit(monkeypatch: Any, tmp_path: Path) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter, VibeTradingRuntimeError

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    with (
        patch(
            "aios.vibe_trading.adapter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=["/opt/vibe/bin/vibe-trading"],
                returncode=2,
                stdout="partial stdout",
                stderr="provider rejected request",
            ),
        ),
        pytest.raises(VibeTradingRuntimeError) as exc_info,
    ):
        VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    records = list(tmp_path.glob("vibe_run_*.json"))
    assert len(records) == 1
    payload = json.loads(records[0].read_text())
    assert payload["status"] == "failed"
    assert payload["error_type"] == "nonzero_exit"
    assert payload["stdout_raw"] == "partial stdout"
    assert "provider rejected" in payload["stderr_raw"]
    assert "nonzero_exit" in str(exc_info.value)


def test_cli_adapter_uses_1800_second_timeout(monkeypatch: Any, tmp_path: Path) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=json.dumps(_committee_payload()),
            stderr="",
        ),
    ) as run:
        VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    assert run.call_args.kwargs["timeout"] == 1800


def test_cli_adapter_runs_uv_fallback_inside_vibe_project(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    project_dir = tmp_path / "Vibe-Trading"
    project_dir.mkdir()
    monkeypatch.delenv("VIBE_TRADING_EXECUTABLE", raising=False)
    monkeypatch.delenv("AIOS_VIBE_TRADING_PROJECT_DIR", raising=False)
    with (
        patch("aios.vibe_trading.adapter.shutil.which", return_value=None),
        patch.object(
            VibeTradingCLIAdapter, "_local_fallback_command", return_value=project_dir
        ),
        patch(
            "aios.vibe_trading.adapter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=["uv", "run", "vibe-trading"],
                returncode=0,
                stdout=json.dumps(_committee_payload()),
                stderr="",
            ),
        ) as run,
    ):
        VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path / "results"}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    assert run.call_args.args[0][:3] == ["uv", "run", "vibe-trading"]
    assert run.call_args.kwargs["cwd"] == project_dir


def test_cli_adapter_timeout_persists_partial_output(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter, VibeTradingRuntimeError

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    timeout = subprocess.TimeoutExpired(
        cmd=["/opt/vibe/bin/vibe-trading"],
        timeout=1800,
        output="partial out",
        stderr="partial err",
    )
    with (
        patch("aios.vibe_trading.adapter.subprocess.run", side_effect=timeout),
        pytest.raises(VibeTradingRuntimeError, match="timeout"),
    ):
        VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    payload = json.loads(next(tmp_path.glob("vibe_run_*.json")).read_text())
    assert payload["status"] == "failed"
    assert payload["error_type"] == "timeout"
    assert payload["stdout_raw"] == "partial out"
    assert payload["stderr_raw"] == "partial err"
    assert payload["parsed_output"]["metadata"]["timeout_seconds"] == 1800


def test_cli_adapter_horizon_days_must_be_1_3_or_7(tmp_path: Path) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter, VibeTradingRuntimeError

    with pytest.raises(VibeTradingRuntimeError, match="invalid_input"):
        VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=5)


def test_cli_adapter_parses_token_usage_from_text() -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    usage = VibeTradingCLIAdapter._extract_token_usage(
        "Time 12m\nTokens: input=123 output=456 total=579"
    )

    assert usage == {"input": 123, "output": 456, "total": 579}


def test_cli_adapter_token_usage_ignores_report_body_numbers() -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    usage = VibeTradingCLIAdapter._extract_token_usage(
        "Decision was made in 2013 cases.\nTokens: ~770,845 (in: 702,013 out: 68,832)"
    )

    assert usage == {"input": 702013, "output": 68832, "total": 770845}


def test_cli_adapter_validation_warns_without_mutating_result() -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter

    parsed = VibeTradingCLIAdapter._normalise_parsed_output(
        payload={},
        raw_report=(
            "Final Report\nDecision: WAIT\n6-12 months view. "
            "5 year conclusion. backtest shows edge. RSI oversold."
        ),
        target="600519",
        market="CN",
        horizon_days=3,
        duration_seconds=10.0,
        token_usage=None,
    )
    validation = VibeTradingCLIAdapter._validate_output(
        parsed=parsed,
        target="600519",
        market="CN",
        horizon_days=3,
    )

    assert validation["valid"] is True
    assert parsed["decision"] == "WAIT"
    assert any("6-12" in warning for warning in validation["warnings"])
    assert any("current price" in warning for warning in validation["warnings"])
    assert validation["request_horizon_days"] == 3


def test_cli_adapter_builds_external_evidence_and_decision_candidate(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from aios.vibe_trading.adapter import VibeTradingCLIAdapter
    from aios.vibe_trading.output_mapper import (
        vibe_record_to_decision_candidate,
        vibe_record_to_external_agent_evidence,
    )

    monkeypatch.setenv("VIBE_TRADING_EXECUTABLE", "/opt/vibe/bin/vibe-trading")
    with patch(
        "aios.vibe_trading.adapter.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["/opt/vibe/bin/vibe-trading"],
            returncode=0,
            stdout=json.dumps(_committee_payload()),
            stderr="",
        ),
    ):
        record = VibeTradingCLIAdapter(
            config_overrides={"results_dir": tmp_path}
        ).run_investment_committee(target="600519", market="CN", horizon_days=3)

    evidence = vibe_record_to_external_agent_evidence(record)
    candidate = vibe_record_to_decision_candidate(
        record, evidence_ids=[evidence.evidence_id]
    )

    assert evidence.evidence_type == "external_agent_report"
    assert evidence.source == "vibe_trading"
    assert evidence.metadata["raw_output_hash"] == record.output_hash
    assert evidence.metadata["validation"]["valid"] is True
    assert evidence.metadata["provenance"]["external_agent_claims_only"] is True
    assert "verified_fact" not in evidence.metadata
    assert "aios_verified_fact" not in evidence.metadata
    assert candidate.source == "vibe_trading"
    assert candidate.action == "WAIT"
    assert candidate.requires_aios_review is True


def test_decision_candidate_faithfully_maps_external_buy_wait_sell_only() -> None:
    from aios.vibe_trading.output_mapper import (
        VibeTradingRunRecord,
        vibe_record_to_decision_candidate,
    )

    for action in ("BUY", "WAIT", "SELL"):
        record = VibeTradingRunRecord(
            run_id=f"vibe_run_{action.lower()}",
            target="600519",
            market="CN",
            horizon_days=3,
            command=("vibe-trading",),
            started_at=datetime(2026, 7, 22, 1, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 22, 1, 1, tzinfo=UTC),
            duration_seconds=60.0,
            exit_code=0,
            status="completed",
            stdout_raw=f"Final Report\nDecision: {action}",
            stderr_raw="",
            parsed_output={
                "decision": action,
                "summary": f"External committee says {action}.",
            },
            input_hash="input-hash",
            output_hash=f"output-hash-{action.lower()}",
            adapter_version="test",
            validation={
                "valid": True,
                "errors": [],
                "warnings": [],
                "request_horizon_days": 3,
                "detected_horizon": 3,
            },
        )

        candidate = vibe_record_to_decision_candidate(
            record, evidence_ids=("ev_00000000-0000-0000-0000-000000000001",)
        )

        assert candidate.source == "vibe_trading"
        assert candidate.action == action
        assert candidate.requires_aios_review is True
        assert candidate.evidence_ids == ("ev_00000000-0000-0000-0000-000000000001",)


def test_adapter_does_not_require_aios_venv_package_install() -> None:
    source = (
        Path(__file__).parent.parent.parent
        / "src"
        / "aios"
        / "vibe_trading"
        / "adapter.py"
    ).read_text()

    assert "importlib.metadata" not in source
    assert "vibe-trading-ai" not in source
    assert "_ensure_installed" not in source


def test_adapter_does_not_import_kernel() -> None:
    source = (
        Path(__file__).parent.parent.parent
        / "src"
        / "aios"
        / "vibe_trading"
        / "adapter.py"
    ).read_text()
    assert "aios.kernel" not in source
    assert "aios.workflows" not in source


def test_config_defaults_without_env(monkeypatch: Any) -> None:
    from aios.vibe_trading.config import vibe_trading_config_from_env

    for var in (
        "AIOS_VIBE_TRADING_PROVIDER",
        "AIOS_VIBE_TRADING_DEEP_THINK_MODEL",
        "AIOS_VIBE_TRADING_QUICK_THINK_MODEL",
        "AIOS_VIBE_TRADING_MAX_DEBATE_ROUNDS",
        "AIOS_VIBE_TRADING_MAX_RISK_DISCUSS_ROUNDS",
        "AIOS_VIBE_TRADING_MAX_RECUR_LIMIT",
        "AIOS_VIBE_TRADING_RESULTS_DIR",
    ):
        monkeypatch.delenv(var, raising=False)

    kw = vibe_trading_config_from_env()

    assert kw["llm_provider"] == "deepseek"
    assert kw["deep_think_llm"] == "deepseek/deepseek-chat"
    assert kw["quick_think_llm"] == "deepseek/deepseek-chat"
    assert kw["max_debate_rounds"] == 2
    assert kw["max_risk_discuss_rounds"] == 2
    assert kw["max_recur_limit"] == 50
    assert isinstance(kw["results_dir"], Path)


def test_config_env_override(monkeypatch: Any) -> None:
    from aios.vibe_trading.config import vibe_trading_config_from_env

    monkeypatch.setenv("AIOS_VIBE_TRADING_PROVIDER", "openai")
    monkeypatch.setenv("AIOS_VIBE_TRADING_DEEP_THINK_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("AIOS_VIBE_TRADING_QUICK_THINK_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("AIOS_VIBE_TRADING_MAX_DEBATE_ROUNDS", "3")
    monkeypatch.setenv("AIOS_VIBE_TRADING_MAX_RISK_DISCUSS_ROUNDS", "3")
    monkeypatch.setenv("AIOS_VIBE_TRADING_MAX_RECUR_LIMIT", "100")

    kw = vibe_trading_config_from_env()

    assert kw["llm_provider"] == "openai"
    assert kw["deep_think_llm"] == "openai/gpt-4o-mini"
    assert kw["max_debate_rounds"] == 3
    assert kw["max_recur_limit"] == 100
