"""Map Vibe-Trading outputs into an AIOS-owned VibeTradingRawResult.

The mapper is intentionally read-only: it inspects the upstream graph output
but does not create or modify any AIOS kernel entities (Prediction, TradePlan,
Experiment, etc.).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from aios.kernel.enums import AgentRole


class VibeTradingRawResult(BaseModel):
    """Canonical, AIOS-owned container for a Vibe-Trading run.

    Every field is populated from the actual upstream AgentState; no fields
    are invented or synthesised.
    """

    symbol: str = Field(
        min_length=1,
        description="Ticker symbol supplied to the upstream graph.",
    )
    vibe_run_id: str = Field(
        default="vibe_manual",
        min_length=1,
        description="External Vibe-Trading run identifier.",
    )
    workflow: str = Field(
        default="manual",
        min_length=1,
        description="Vibe-Trading workflow or swarm preset used for this run.",
    )
    raw_output_reference: str | None = Field(
        default=None,
        description="Stable reference to the raw upstream output artifact.",
    )
    market: str = Field(
        min_length=1,
        description="Market identifier (currently always 'CN_A').",
    )
    as_of: datetime = Field(
        description=("Point-in-time as-of date (the trade_date passed to propagate)."),
    )

    analyst_reports: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Mapping of analyst type name (e.g. 'market', 'sentiment', "
            "'news', 'fundamentals') to the full text report produced by "
            "that analyst."
        ),
    )
    investment_debate: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Key fields from the Bull/Bear investment debate state: "
            "{'bull_history', 'bear_history', 'judge_decision'}."
        ),
    )
    trader_plan: str = Field(
        default="",
        description="Raw trader investment plan text.",
    )
    risk_assessment: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Risk-manager output including the raw final_trade_decision "
            "text and structured final_trade_recommendation payload."
        ),
    )
    final_decision: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Serialised TradeRecommendation (signal, size_fraction, "
            "target_price, stop_loss, time_horizon_days, confidence, "
            "currency, rationale) or None when unavailable."
        ),
    )

    upstream_version: str | None = Field(
        default=None,
        description="VibeTrading package version used for this run.",
    )
    model_provider: str = Field(
        min_length=1,
        description="LLM provider used (e.g. 'openai', 'deepseek').",
    )
    model_name: str = Field(
        min_length=1,
        description="LLM model name used for deep-thinking nodes.",
    )

    started_at: datetime = Field(description="Wall-clock start of the graph run.")
    completed_at: datetime = Field(description="Wall-clock end of the graph run.")
    raw_state: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Full AgentState serialised to dict for auditability. "
            "Contains every field present in the upstream state at "
            "graph completion."
        ),
    )


class VibeTradingAgentReportInput(BaseModel):
    role: AgentRole
    summary: str
    stance: str
    confidence: float | None = None
    evidence_ids: tuple[str, ...] = ()
    source: str = "vibe_trading"
    raw_reference: str


_REPORT_LABELS = (
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
)

_REPORT_ROLE_MAP = {
    "market": AgentRole.TECHNICAL,
    "fundamentals": AgentRole.FUNDAMENTAL,
    "news": AgentRole.NEWS,
    "sentiment": AgentRole.SENTIMENT,
}

_DEBATE_FIELDS = ("bull_history", "bear_history", "judge_decision")


def map_agent_state_to_result(
    *,
    agent_state: Any,
    symbol: str,
    market: str,
    as_of: datetime,
    model_provider: str,
    model_name: str,
    started_at: datetime,
    completed_at: datetime,
    upstream_version: str | None = None,
) -> VibeTradingRawResult:
    """Build a VibeTradingRawResult from an upstream result-like object.

    The mapping is mechanical and does not interpret or enrich any field
    beyond what is present on the graph output.
    """
    raw_state = _safe_serialise(agent_state)

    analyst_reports: dict[str, str] = {}
    for label in _REPORT_LABELS:
        value = getattr(agent_state, label, "") or ""
        if isinstance(value, str) and value.strip():
            key = label.removesuffix("_report")
            analyst_reports[key] = value

    invest = getattr(agent_state, "investment_debate_state", None)
    investment_debate: dict[str, str] = {}
    if invest is not None:
        for field in _DEBATE_FIELDS:
            value = getattr(invest, field, "") or ""
            if isinstance(value, str) and value.strip():
                investment_debate[field] = value

    trader_plan = getattr(agent_state, "trader_investment_plan", "") or ""
    if not isinstance(trader_plan, str):
        trader_plan = ""

    final_trade_decision = getattr(agent_state, "final_trade_decision", "") or ""
    recommendation = getattr(agent_state, "final_trade_recommendation", None)
    final_decision: dict[str, Any] | None = None
    if recommendation is not None:
        final_decision = _object_to_dict(recommendation)

    risk_assessment: dict[str, str] = {}
    if isinstance(final_trade_decision, str) and final_trade_decision.strip():
        risk_assessment["final_trade_decision"] = final_trade_decision
    risk = getattr(agent_state, "risk_debate_state", None)
    if risk is not None:
        judge = getattr(risk, "judge_decision", "") or ""
        if isinstance(judge, str) and judge.strip():
            risk_assessment["risk_judge_decision"] = judge

    return VibeTradingRawResult(
        symbol=symbol,
        market=market,
        as_of=as_of,
        vibe_run_id=f"vibe-{symbol}-{as_of.date().isoformat()}",
        workflow="investment_committee",
        raw_output_reference=None,
        analyst_reports=analyst_reports,
        investment_debate=investment_debate,
        trader_plan=trader_plan,
        risk_assessment=risk_assessment,
        final_decision=final_decision,
        upstream_version=upstream_version,
        model_provider=model_provider,
        model_name=model_name,
        started_at=started_at,
        completed_at=completed_at,
        raw_state=raw_state,
    )


def map_vibe_trading_result_to_agent_report_inputs(
    result: VibeTradingRawResult,
    *,
    default_confidence: float | None = None,
) -> list[VibeTradingAgentReportInput]:
    """Map existing Vibe-Trading analyst report text to AgentReport inputs.

    The mapper does not infer evidence, stance, confidence, or hypotheses from
    free text. Callers may provide a default confidence explicitly.
    """
    payloads: list[VibeTradingAgentReportInput] = []
    for report_key, report_text in result.analyst_reports.items():
        role = _REPORT_ROLE_MAP.get(report_key)
        if role is None or not report_text.strip():
            continue
        payloads.append(
            VibeTradingAgentReportInput(
                role=role,
                summary=report_text.strip(),
                stance="unspecified",
                confidence=default_confidence,
                evidence_ids=(),
                source="vibe_trading",
                raw_reference=f"analyst_reports.{report_key}",
            )
        )
    return payloads


def _safe_serialise(obj: Any) -> dict[str, Any]:
    """Serialise AgentState to dict, degrading gracefully."""
    try:
        return dict(obj.model_dump())
    except Exception:
        pass
    try:
        if hasattr(obj, "_asdict"):
            return dict(obj._asdict())
    except Exception:
        pass
    try:
        return dict(obj)
    except Exception:
        return {"_error": "unable to serialise AgentState"}


def _object_to_dict(obj: Any) -> dict[str, Any]:
    """Convert an arbitrary object to a dict using best-effort methods."""
    try:
        return dict(obj.model_dump())
    except Exception:
        pass
    if hasattr(obj, "_asdict"):
        try:
            return dict(obj._asdict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {"_repr": str(obj)}
