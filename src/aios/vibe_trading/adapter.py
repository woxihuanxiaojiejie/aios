"""Vibe-Trading adapter boundary for AIOS.

AIOS talks to Vibe-Trading only through the CLI. It does not import
Vibe-Trading internals, copy its source, or assume its terminal output is pure
JSON.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from aios.vibe_trading.config import vibe_trading_config_from_env
from aios.vibe_trading.output_mapper import VibeTradingRawResult, VibeTradingRunRecord

ADAPTER_VERSION = "vibe_trading_cli_adapter_v1"
ALLOWED_HORIZON_DAYS = {1, 3, 7}


class VibeTradingConfigurationError(Exception):
    """Raised when Vibe-Trading integration configuration is invalid."""


class VibeTradingRuntimeError(Exception):
    """Raised when Vibe-Trading execution fails at the AIOS CLI boundary."""

    def __init__(self, message: str, *, error_type: str = "unknown_error") -> None:
        super().__init__(f"{error_type}: {message}")
        self.error_type = error_type


class VibeTradingCLIAdapter:
    """Production CLI bridge for the Vibe-Trading integration boundary."""

    def __init__(
        self,
        *,
        config_overrides: dict[str, Any] | None = None,
    ) -> None:
        self._config_overrides = config_overrides or {}

    def run_investment_committee(
        self,
        *,
        target: str,
        market: str,
        horizon_days: int,
    ) -> VibeTradingRunRecord:
        """Run the fixed Vibe-Trading investment committee CLI contract."""
        config = vibe_trading_config_from_env(overrides=self._config_overrides)
        results_dir = Path(config["results_dir"])
        timeout_seconds = self._timeout_seconds()
        started_at = datetime.now(UTC)
        start_monotonic = time.monotonic()
        run_id = f"vibe_run_{uuid4()}"
        stdout_raw = ""
        stderr_raw = ""
        parsed_output: dict[str, Any] | None = None
        validation: dict[str, Any] | None = None
        exit_code: int | None = None
        error_type: str | None = None
        error_message: str | None = None
        status = "completed"
        command: list[str] = []
        raise_error: BaseException | None = None
        input_payload = {
            "target": target,
            "market": market,
            "horizon_days": str(horizon_days),
            "ticker": target,
            "symbol": target,
        }

        try:
            self._validate_input(
                target=target, market=market, horizon_days=horizon_days
            )
            base_command = self._resolve_command()
            cwd = self._resolve_command_cwd(base_command)
            json_input = json.dumps(input_payload, sort_keys=True)
            command = [
                *base_command,
                "--json",
                "--no-rich",
                "--swarm-run",
                "investment_committee",
                json_input,
            ]
            run_kwargs: dict[str, Any] = {
                "shell": False,
                "capture_output": True,
                "text": True,
                "timeout": timeout_seconds,
            }
            if cwd is not None:
                run_kwargs["cwd"] = cwd
            completed = subprocess.run(command, **run_kwargs)
            exit_code = completed.returncode
            stdout_raw = completed.stdout
            stderr_raw = completed.stderr
            if completed.returncode != 0:
                status = "failed"
                error_type = self._classify_nonzero_error(stderr_raw, stdout_raw)
                error_message = self._runtime_error_message(
                    "Vibe-Trading failed",
                    returncode=completed.returncode,
                    stdout=stdout_raw,
                    stderr=stderr_raw,
                )
            else:
                token_usage = self._extract_token_usage(stdout_raw)
                business_error = self._business_error(
                    self._extract_last_json_object(stdout_raw) or {}
                )
                if business_error:
                    status = "failed"
                    error_type = "provider_error"
                    error_message = self._runtime_error_message(
                        f"Vibe-Trading returned failed result: {business_error}",
                        returncode=completed.returncode,
                        stdout=stdout_raw,
                        stderr=stderr_raw,
                    )
                    parsed_output = self._unknown_output(
                        target=target,
                        market=market,
                        horizon_days=horizon_days,
                        raw_report=stdout_raw,
                        duration_seconds=time.monotonic() - start_monotonic,
                        token_usage=token_usage,
                    )
                    validation = {
                        "valid": False,
                        "errors": [business_error],
                        "warnings": [],
                        "request_horizon_days": horizon_days,
                        "detected_horizon": None,
                    }
                    raise VibeTradingRuntimeError(
                        error_message,
                        error_type=error_type,
                    )
                parsed_output = self._parse_cli_output(
                    stdout=stdout_raw,
                    target=target,
                    market=market,
                    horizon_days=horizon_days,
                    duration_seconds=time.monotonic() - start_monotonic,
                    token_usage=token_usage,
                )
                validation = self._validate_output(
                    parsed=parsed_output,
                    target=target,
                    market=market,
                    horizon_days=horizon_days,
                )
                if validation["errors"]:
                    status = "validation_failed"
                    error_type = "validation_failed"
                    error_message = "; ".join(str(e) for e in validation["errors"])
        except subprocess.TimeoutExpired as exc:
            stdout_raw = _coerce_timeout_stream(exc.stdout or exc.output)
            stderr_raw = _coerce_timeout_stream(exc.stderr)
            status = "failed"
            error_type = "timeout"
            error_message = f"Vibe-Trading timed out after {timeout_seconds}s"
            parsed_output = self._unknown_output(
                target=target,
                market=market,
                horizon_days=horizon_days,
                raw_report="",
                duration_seconds=time.monotonic() - start_monotonic,
                token_usage=None,
            )
            parsed_output["metadata"]["timeout_seconds"] = timeout_seconds
        except FileNotFoundError as exc:
            status = "failed"
            error_type = "executable_not_found"
            error_message = self._missing_command_message()
            raise_error = exc
        except VibeTradingConfigurationError as exc:
            status = "failed"
            error_type = "executable_not_found"
            error_message = str(exc)
            raise_error = exc
        except VibeTradingRuntimeError as exc:
            status = "parse_failed" if exc.error_type == "parse_failed" else "failed"
            error_type = exc.error_type
            error_message = str(exc)
            if stderr_raw and stderr_raw not in error_message:
                error_message = f"{error_message}; stderr={stderr_raw!r}"
            raise_error = exc
        except Exception as exc:
            status = "failed"
            error_type = "unknown_error"
            error_message = str(exc)
            raise_error = exc

        duration_seconds = time.monotonic() - start_monotonic
        token_usage = self._extract_token_usage(stdout_raw)
        record = VibeTradingRunRecord(
            run_id=run_id,
            provider_name="vibe_trading",
            target=target,
            market=market,
            horizon_days=horizon_days,
            command=tuple(command),
            started_at=started_at,
            completed_at=datetime.now(UTC),
            duration_seconds=duration_seconds,
            exit_code=exit_code,
            status=status,
            stdout_raw=stdout_raw,
            stderr_raw=stderr_raw,
            parsed_output=parsed_output,
            input_hash=_sha256_text(json.dumps(input_payload, sort_keys=True)),
            output_hash=_sha256_text(stdout_raw),
            adapter_version=ADAPTER_VERSION,
            token_usage=token_usage,
            error_type=error_type,
            error_message=error_message,
            validation=validation,
        )
        self._persist_run_record(record, results_dir)
        if raise_error is not None:
            raise VibeTradingRuntimeError(
                error_message or str(raise_error),
                error_type=error_type or "unknown_error",
            ) from raise_error
        if error_type is not None:
            raise VibeTradingRuntimeError(
                error_message or error_type,
                error_type=error_type,
            )
        return record

    def analyze(
        self,
        *,
        symbol: str,
        market: str,
        as_of: datetime,
        horizon_days: int,
        workflow: str,
        provider: str,
        model: str,
    ) -> VibeTradingRawResult:
        """Run Vibe-Trading and return the legacy research-run result shape."""
        self._format_trade_date(as_of)
        record = self.run_investment_committee(
            target=symbol,
            market=market,
            horizon_days=horizon_days,
        )
        return self._record_to_raw_result(
            record=record,
            as_of=as_of,
            workflow=workflow,
            provider=provider,
            model=model,
        )

    @staticmethod
    def _record_to_raw_result(
        *,
        record: VibeTradingRunRecord,
        as_of: datetime,
        workflow: str,
        provider: str,
        model: str,
    ) -> VibeTradingRawResult:
        parsed = record.parsed_output or {}
        raw_metadata = parsed.get("metadata")
        metadata: dict[str, Any] = (
            raw_metadata if isinstance(raw_metadata, dict) else {}
        )
        raw_report = str(parsed.get("raw_report") or record.stdout_raw)
        final_decision: dict[str, Any] | None = None
        if parsed.get("decision") != "UNKNOWN":
            final_decision = {
                "signal": str(parsed.get("decision")).lower(),
                "confidence": parsed.get("confidence"),
                "time_horizon_days": record.horizon_days,
                "rationale": parsed.get("summary") or raw_report,
            }
        result = VibeTradingRawResult(
            symbol=record.target,
            market=record.market,
            as_of=as_of,
            vibe_run_id=str(metadata.get("upstream_vibe_run_id") or record.run_id),
            workflow=workflow,
            raw_output_reference=str(record.run_id),
            analyst_reports={"external_agent_report": raw_report},
            investment_debate={},
            trader_plan=str(parsed.get("summary") or raw_report),
            risk_assessment={"final_trade_decision": raw_report},
            final_decision=final_decision,
            upstream_version=record.adapter_version,
            model_provider=provider,
            model_name=model,
            started_at=record.started_at,
            completed_at=record.completed_at,
            raw_state={
                "run_record": record.model_dump(mode="json"),
                "external_agent_claims_only": True,
            },
        )
        try:
            return VibeTradingRawResult.model_validate(result.model_dump())
        except ValidationError as exc:
            msg = "Vibe-Trading run record could not be mapped to legacy result"
            raise VibeTradingRuntimeError(msg, error_type="parse_failed") from exc

    @classmethod
    def _resolve_command(cls) -> list[str]:
        env_executable = os.getenv("VIBE_TRADING_EXECUTABLE")
        if env_executable:
            return [env_executable]

        path_result = shutil.which("vibe-trading")
        if path_result:
            return [path_result]

        project_dir = os.getenv("AIOS_VIBE_TRADING_PROJECT_DIR")
        if project_dir and Path(project_dir).exists():
            return ["uv", "run", "vibe-trading"]

        fallback = cls._local_fallback_command()
        if fallback.exists():
            return ["uv", "run", "vibe-trading"]

        raise VibeTradingConfigurationError(cls._missing_command_message())

    @classmethod
    def _missing_command_message(cls) -> str:
        env_executable = os.getenv("VIBE_TRADING_EXECUTABLE")
        path_result = shutil.which("vibe-trading")
        project_dir = os.getenv("AIOS_VIBE_TRADING_PROJECT_DIR")
        fallback = cls._local_fallback_command()
        return (
            "Vibe-Trading CLI command was not found. "
            f"VIBE_TRADING_EXECUTABLE={env_executable!r}; "
            f"PATH lookup result={path_result!r}; "
            f"AIOS_VIBE_TRADING_PROJECT_DIR={project_dir!r}; "
            f"local fallback project dir={fallback}"
        )

    @staticmethod
    def _local_fallback_command() -> Path:
        project_root = Path(__file__).resolve().parents[3]
        return project_root.parent / "Vibe-Trading"

    @classmethod
    def _resolve_command_cwd(cls, command: list[str]) -> Path | None:
        if command != ["uv", "run", "vibe-trading"]:
            return None
        project_dir = os.getenv("AIOS_VIBE_TRADING_PROJECT_DIR")
        if project_dir and Path(project_dir).exists():
            return Path(project_dir)
        fallback = cls._local_fallback_command()
        if fallback.exists():
            return fallback
        return None

    @staticmethod
    def _format_trade_date(as_of: datetime) -> str:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            msg = "as_of must be timezone-aware"
            raise VibeTradingConfigurationError(msg)
        return as_of.date().isoformat()

    @staticmethod
    def _build_user_vars(
        *,
        symbol: str,
        market: str,
        trade_date: str,
        horizon_days: int,
        provider: str,
        model: str,
    ) -> dict[str, str]:
        return {
            str(key): str(value)
            for key, value in {
                "target": symbol,
                "market": market,
                "ticker": symbol,
                "symbol": symbol,
                "trade_date": trade_date,
                "horizon_days": horizon_days,
                "provider": provider,
                "model": model,
            }.items()
        }

    @staticmethod
    def _parse_stdout_payload(
        stdout: str,
        *,
        returncode: int,
        stderr: str,
    ) -> dict[str, Any]:
        payload = VibeTradingCLIAdapter._extract_last_schema_valid_json_object(stdout)
        if payload is None:
            msg = VibeTradingCLIAdapter._runtime_error_message(
                "Vibe-Trading CLI did not return structured JSON output",
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
            raise VibeTradingRuntimeError(msg, error_type="parse_failed")
        return payload

    @staticmethod
    def _extract_last_schema_valid_json_object(stdout: str) -> dict[str, Any] | None:
        decoder = json.JSONDecoder()
        last_payload: dict[str, Any] | None = None
        for index, character in enumerate(stdout):
            if character != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(stdout[index:])
            except json.JSONDecodeError:
                continue
            if not isinstance(candidate, dict):
                continue
            try:
                VibeTradingRawResult.model_validate(candidate)
            except ValidationError:
                continue
            last_payload = candidate
        return last_payload

    @staticmethod
    def _business_error(payload: dict[str, Any]) -> str | None:
        if payload.get("success") is False:
            return VibeTradingCLIAdapter._first_error_reason(payload, "success=false")
        if payload.get("status") == "failed":
            return VibeTradingCLIAdapter._first_error_reason(payload, "status=failed")
        error = payload.get("error")
        if error:
            return str(error)
        validation_error = payload.get("validation_error")
        if validation_error:
            return str(validation_error)
        return None

    @staticmethod
    def _first_error_reason(payload: dict[str, Any], fallback: str) -> str:
        return str(
            payload.get("error")
            or payload.get("validation_error")
            or payload.get("message")
            or fallback
        )

    @staticmethod
    def _runtime_error_message(
        summary: str,
        *,
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> str:
        return (
            f"{summary}; exit code {returncode}; "
            f"stdout={VibeTradingCLIAdapter._truncate_output(stdout)!r}; "
            f"stderr={VibeTradingCLIAdapter._truncate_output(stderr)!r}"
        )

    @staticmethod
    def _truncate_output(value: str, limit: int = 2000) -> str:
        stripped = value.strip()
        if len(stripped) <= limit:
            return stripped
        return stripped[:limit] + "...[truncated]"

    @staticmethod
    def _upstream_version(command: list[str]) -> str:
        return "cli:" + shlex.join(command)

    def _timeout_seconds(self) -> int:
        configured = self._config_overrides.get("timeout_seconds")
        if configured is not None:
            return int(configured)
        return int(os.getenv("AIOS_VIBE_TIMEOUT_SECONDS", "1800"))

    @staticmethod
    def _validate_input(*, target: str, market: str, horizon_days: int) -> None:
        if not target.strip() or not market.strip():
            raise VibeTradingRuntimeError(
                "target and market are required", error_type="invalid_input"
            )
        if horizon_days not in ALLOWED_HORIZON_DAYS:
            raise VibeTradingRuntimeError(
                "horizon_days must be one of 1, 3, or 7",
                error_type="invalid_input",
            )

    @staticmethod
    def _parse_cli_output(
        *,
        stdout: str,
        target: str,
        market: str,
        horizon_days: int,
        duration_seconds: float,
        token_usage: dict[str, int] | None,
    ) -> dict[str, Any]:
        payload = VibeTradingCLIAdapter._extract_last_json_object(stdout)
        final_report = VibeTradingCLIAdapter._extract_final_report(stdout)
        if final_report and not _looks_like_result_payload(payload):
            payload = None
        if payload is not None:
            raw_report = str(
                payload.get("raw_report")
                or payload.get("final_report")
                or payload.get("report")
                or stdout.strip()
            )
            return VibeTradingCLIAdapter._normalise_parsed_output(
                payload=payload,
                raw_report=raw_report,
                target=target,
                market=market,
                horizon_days=horizon_days,
                duration_seconds=duration_seconds,
                token_usage=token_usage,
            )
        if not final_report:
            raise VibeTradingRuntimeError(
                VibeTradingCLIAdapter._runtime_error_message(
                    "Vibe-Trading CLI did not return JSON or a Final Report",
                    returncode=0,
                    stdout=stdout,
                    stderr="",
                ),
                error_type="parse_failed",
            )
        return VibeTradingCLIAdapter._normalise_parsed_output(
            payload={},
            raw_report=final_report,
            target=target,
            market=market,
            horizon_days=horizon_days,
            duration_seconds=duration_seconds,
            token_usage=token_usage,
        )

    @staticmethod
    def _normalise_parsed_output(
        *,
        payload: dict[str, Any],
        raw_report: str,
        target: str,
        market: str,
        horizon_days: int,
        duration_seconds: float,
        token_usage: dict[str, int] | None,
    ) -> dict[str, Any]:
        decision = VibeTradingCLIAdapter._extract_decision(payload, raw_report)
        summary = str(
            payload.get("summary")
            or payload.get("rationale")
            or VibeTradingCLIAdapter._first_non_empty_line(raw_report)
            or ""
        )
        confidence = payload.get("confidence")
        return {
            "provider": "vibe_trading",
            "target": str(payload.get("target") or payload.get("symbol") or target),
            "market": str(payload.get("market") or market),
            "horizon_days": int(payload.get("horizon_days") or horizon_days),
            "decision": decision,
            "confidence": float(confidence) if confidence is not None else None,
            "summary": summary,
            "bull_arguments": _list_of_strings(payload.get("bull_arguments")),
            "bear_arguments": _list_of_strings(payload.get("bear_arguments")),
            "risk_findings": _list_of_strings(payload.get("risk_findings")),
            "conditions": _list_of_strings(payload.get("conditions")),
            "evidence_references": _list_of_strings(payload.get("evidence_references")),
            "raw_report": raw_report,
            "metadata": {
                "duration_seconds": duration_seconds,
                "token_input": (token_usage or {}).get("input"),
                "token_output": (token_usage or {}).get("output"),
                "token_total": (token_usage or {}).get("total"),
                "upstream_vibe_run_id": payload.get("vibe_run_id"),
            },
        }

    @staticmethod
    def _unknown_output(
        *,
        target: str,
        market: str,
        horizon_days: int,
        raw_report: str,
        duration_seconds: float,
        token_usage: dict[str, int] | None,
    ) -> dict[str, Any]:
        return VibeTradingCLIAdapter._normalise_parsed_output(
            payload={},
            raw_report=raw_report,
            target=target,
            market=market,
            horizon_days=horizon_days,
            duration_seconds=duration_seconds,
            token_usage=token_usage,
        )

    @staticmethod
    def _validate_output(
        *,
        parsed: dict[str, Any],
        target: str,
        market: str,
        horizon_days: int,
    ) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        report = str(parsed.get("raw_report") or "")
        lowered = report.lower()
        detected_horizon = VibeTradingCLIAdapter._detect_horizon(report)
        if parsed.get("target") != target:
            errors.append("parsed target does not match request")
        if parsed.get("market") != market:
            errors.append("parsed market does not match request")
        if parsed.get("horizon_days") != horizon_days:
            errors.append("parsed horizon_days does not match request")
        if parsed.get("decision") == "UNKNOWN":
            errors.append("report does not explicitly provide a final decision")
        if horizon_days == 3 and detected_horizon is not None and detected_horizon > 30:
            warnings.append("three day request produced a long-term decision")
        if "6-12" in lowered or "6 to 12" in lowered or "6个月" in lowered:
            warnings.append("report mainly discusses 6-12 months")
        if ("5 year" in lowered or "5-year" in lowered or "10 year" in lowered) and (
            "3 day" not in lowered and "three day" not in lowered
        ):
            warnings.append(
                "report uses 5 year or 10 year conclusions without relating them "
                "to the request horizon"
            )
        if "current price" not in lowered and "当前价格" not in lowered:
            warnings.append("report is missing a current price data source")
        if "backtest" in lowered and not re.search(
            r"sample|parameter|window|样本|参数", lowered
        ):
            warnings.append("backtest lacks parameter or sample explanation")
        if re.search(
            r"\brsi\b|\bmacd\b|\bma\d+\b|indicator|指标", lowered
        ) and not re.search(
            r"formula|parameter|source|window|可复现|参数|来源", lowered
        ):
            warnings.append("indicators lack reproducible basis")
        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "request_horizon_days": horizon_days,
            "detected_horizon": detected_horizon,
        }

    @staticmethod
    def _extract_last_json_object(stdout: str) -> dict[str, Any] | None:
        stripped = stdout.strip()
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            return payload
        decoder = json.JSONDecoder()
        last_payload: dict[str, Any] | None = None
        for index, character in enumerate(stdout):
            if character != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(stdout[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and (
                "target" in candidate
                or "symbol" in candidate
                or "decision" in candidate
                or "final_decision" in candidate
                or "raw_report" in candidate
            ):
                last_payload = candidate
        return last_payload

    @staticmethod
    def _extract_final_report(stdout: str) -> str:
        match = re.search(r"(?is)(Final Report.*?)(?:\n\s*COMPLETED\b|\Z)", stdout)
        if match:
            return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_decision(payload: dict[str, Any], raw_report: str) -> str:
        value: Any = payload.get("decision") or payload.get("action")
        final_decision = payload.get("final_decision")
        if value is None and isinstance(final_decision, dict):
            value = final_decision.get("signal") or final_decision.get("action")
        if value is None:
            decision_terms = (
                r"CAUTIOUS\s+LONG|INITIATE|LONG|SHORT|BUY|SELL|WAIT|HOLD|"
                r"NO[_ -]?TRADE|战术性做多|做多|买入|做空|卖出|观望|等待|不交易"
            )
            match = re.search(
                r"(?i)(?:final\s+decision|decision|recommendation|action|"
                r"决定|决策类型|决策|方向)"
                r"(?:\*\*)?\s*[:\uFF1A]\s*(?:\*\*)?\s*"
                rf"({decision_terms})",
                raw_report,
            )
            if match:
                value = match.group(1)
        if value is None:
            value = VibeTradingCLIAdapter._decision_from_report_opening(raw_report)
        normalized = (
            str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
        )
        mapping = {
            "BUY": "BUY",
            "CAUTIOUS_LONG": "BUY",
            "INITIATE": "BUY",
            "LONG": "BUY",
            "战术性做多": "BUY",
            "SELL": "SELL",
            "SHORT": "SELL",
            "WAIT": "WAIT",
            "HOLD": "WAIT",
            "WATCH": "WAIT",
            "NO_TRADE": "NO_TRADE",
            "做多": "BUY",
            "买入": "BUY",
            "做空": "SELL",
            "卖出": "SELL",
            "观望": "WAIT",
            "等待": "WAIT",
            "不交易": "NO_TRADE",
        }
        return mapping.get(normalized, "UNKNOWN")

    @staticmethod
    def _decision_from_report_opening(raw_report: str) -> str | None:
        opening = raw_report[:1500].lower()
        if not any(
            marker in opening
            for marker in (
                "final investment decision",
                "decision statement",
                "最终投资决策",
                "pm 决策",
                "pm最终决定",
            )
        ):
            return None
        if re.search(r"no[_ -]?trade|不交易", opening):
            return "NO_TRADE"
        if re.search(r"\bwait\b|\bhold\b|观望|等待", opening):
            return "WAIT"
        if re.search(r"\bshort\b|\bsell\b|做空|卖出", opening):
            return "SELL"
        if re.search(r"\blong\b|\bbuy\b|\binitiate\b|做多|买入", opening):
            return "BUY"
        return None

    @staticmethod
    def _extract_token_usage(text: str) -> dict[str, int] | None:
        token_lines = "\n".join(
            line for line in text.splitlines() if "token" in line.lower()
        )
        lower = token_lines.lower()
        if "token" not in lower and "tokens" not in lower:
            return None
        values: dict[str, int] = {}
        patterns = {
            "input": r"\b(?:input|prompt|in)\b[^\d]{0,12}([\d,]+)",
            "output": r"\b(?:output|completion|out)\b[^\d]{0,12}([\d,]+)",
            "total": r"\btotal\b[^\d]{0,12}([\d,]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, lower)
            if match:
                values[key] = int(match.group(1).replace(",", ""))
        if "total" not in values:
            total = re.search(r"tokens?[^\d]{0,12}~?\s*([\d,]+)", lower)
            if total:
                values["total"] = int(total.group(1).replace(",", ""))
        if not values:
            plain = re.search(r"tokens?[^\d]{0,12}([\d,]+)", lower)
            if plain:
                values["total"] = int(plain.group(1).replace(",", ""))
        return values or None

    @staticmethod
    def _classify_nonzero_error(stderr: str, stdout: str) -> str:
        text = f"{stderr}\n{stdout}".lower()
        if any(term in text for term in ("auth", "api key", "unauthorized", "401")):
            return "authentication_error"
        if any(term in text for term in ("provider_error", "rate limit")):
            return "provider_error"
        return "nonzero_exit"

    @staticmethod
    def _detect_horizon(report: str) -> int | None:
        lowered = report.lower()
        if "6-12" in lowered or "6 to 12" in lowered:
            return 180
        day_match = re.search(r"(\d+)\s*(?:个)?(?:交易日|天|day|days|d)", lowered)
        if day_match is not None:
            value = int(day_match.group(1))
            return value if value <= 365 else None
        month_match = re.search(r"(\d+)\s*(?:个月|月)", lowered)
        if month_match is not None:
            value = int(month_match.group(1))
            return value * 30 if value <= 60 else None
        match = re.search(r"(\d+)\s*(year|years|年)", lowered)
        if match is None:
            return None
        value = int(match.group(1))
        return value * 365 if value <= 50 else None

    @staticmethod
    def _first_non_empty_line(text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    @staticmethod
    def _persist_run_record(record: VibeTradingRunRecord, results_dir: Path) -> None:
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / f"{record.run_id}.json"
        if path.exists():
            msg = f"run record already exists: {path}"
            raise VibeTradingRuntimeError(msg, error_type="unknown_error")
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")


class VibeTradingAdapter(VibeTradingCLIAdapter):
    """Backward-compatible adapter name used by existing AIOS callers."""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _coerce_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list | tuple):
        return [str(item) for item in value if str(item).strip()]
    return []


def _looks_like_result_payload(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    return any(
        key in payload
        for key in (
            "decision",
            "action",
            "final_decision",
            "raw_report",
            "final_report",
            "report",
            "summary",
        )
    )
