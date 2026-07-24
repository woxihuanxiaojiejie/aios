from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from aios.application.brain002 import SkillInput, SkillPrompt
from aios.kernel.brain002 import SkillDefinition, SkillResultPayload

SUPPORTED_MARKETS = ("cn", "us")
SUPPORTED_ASSET_TYPES = ("stock", "etf")
SUPPORTED_HORIZONS = ("intraday", "swing", "position")


@dataclass(frozen=True)
class PromptSkill:
    definition: SkillDefinition
    prompt_version: str
    system_prompt: str

    response_schema = SkillResultPayload

    def build_prompt(self, skill_input: SkillInput) -> SkillPrompt:
        return SkillPrompt(
            system_prompt=self.system_prompt,
            user_prompt=self._user_prompt(skill_input),
            prompt_version=self.prompt_version,
        )

    def _user_prompt(self, skill_input: SkillInput) -> str:
        payload: dict[str, Any] = {
            "task_id": skill_input.task_id,
            "symbol": skill_input.symbol,
            "market": skill_input.market,
            "asset_type": skill_input.asset_type,
            "analysis_horizon": skill_input.analysis_horizon,
            "as_of": skill_input.as_of.isoformat(),
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "evidence_type": item.evidence_type,
                    "source": item.source,
                    "available_at": item.available_at.isoformat(),
                    "summary": item.summary,
                    "reliability": item.reliability,
                    "metadata": item.metadata,
                }
                for item in skill_input.evidence
            ],
            "market_context": skill_input.market_context,
            "user_constraints": skill_input.user_constraints,
            "skill_context": skill_input.skill_context,
        }
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)


class TechnicalTrendSkill(PromptSkill):
    def __init__(self) -> None:
        super().__init__(
            definition=SkillDefinition(
                skill_id="technical_trend",
                name="Technical Trend",
                version="1.0.0",
                description=(
                    "Independent analysis of price trend, moving averages, "
                    "volume, support/resistance, and trend strength."
                ),
                supported_markets=SUPPORTED_MARKETS,
                supported_asset_types=SUPPORTED_ASSET_TYPES,
                supported_horizons=SUPPORTED_HORIZONS,
                required_evidence_types=("market_daily_bar",),
                input_schema=SkillInput.model_json_schema(),
                output_schema=SkillResultPayload.model_json_schema(),
            ),
            prompt_version="technical_trend_v1",
            system_prompt=(
                "You are the technical_trend skill. Analyze only price trend, "
                "moving averages, volume, support/resistance, and trend strength. "
                "Do not analyze policy, company announcements, governance, "
                "sector semantics, or market sentiment. Do not make final trading "
                "decisions, position sizing, orders, take-profit, or stop-loss. "
                "Return structured JSON matching the SkillResultPayload schema. "
                "Use direction only as bullish, bearish, neutral, or uncertain. "
                "Confidence must be a number from 0 to 1. Every non-uncertain "
                "conclusion must cite at least one supporting_evidence_id. Always "
                "include risk_factors, invalid_conditions, and missing_information."
            ),
        )


class SectorStrengthSkill(PromptSkill):
    def __init__(self) -> None:
        super().__init__(
            definition=SkillDefinition(
                skill_id="sector_strength",
                name="Sector Strength",
                version="1.0.0",
                description=(
                    "Independent analysis of sector strength, relative performance, "
                    "sector turnover/breadth, and leader/follower relationships."
                ),
                supported_markets=SUPPORTED_MARKETS,
                supported_asset_types=SUPPORTED_ASSET_TYPES,
                supported_horizons=SUPPORTED_HORIZONS,
                required_evidence_types=("sector_snapshot",),
                input_schema=SkillInput.model_json_schema(),
                output_schema=SkillResultPayload.model_json_schema(),
            ),
            prompt_version="sector_strength_v1",
            system_prompt=(
                "You are the sector_strength skill. Analyze only sector strength, "
                "relative performance, sector turnover, breadth, diffusion, and "
                "leader/follower relationships. Do not directly decide individual "
                "stock buys or sells. Do not perform final decision fusion, position "
                "sizing, orders, take-profit, or stop-loss. Return structured JSON "
                "matching the SkillResultPayload schema. Use direction only as "
                "bullish, bearish, neutral, or uncertain. Confidence must be a "
                "number from 0 to 1. Every non-uncertain conclusion must cite at "
                "least one supporting_evidence_id. Always include risk_factors, "
                "invalid_conditions, and missing_information."
            ),
        )


class PolicyImpactSkill(PromptSkill):
    def __init__(self) -> None:
        super().__init__(
            definition=SkillDefinition(
                skill_id="policy_impact",
                name="Policy Impact",
                version="1.0.0",
                description=(
                    "Independent analysis of policy content, policy level, impact "
                    "chain, beneficiary/damaged directions, cycle, and uncertainty."
                ),
                supported_markets=SUPPORTED_MARKETS,
                supported_asset_types=SUPPORTED_ASSET_TYPES,
                supported_horizons=SUPPORTED_HORIZONS,
                required_evidence_types=("policy",),
                input_schema=SkillInput.model_json_schema(),
                output_schema=SkillResultPayload.model_json_schema(),
                trigger_conditions={"metadata_equals": {"source_domain": "policy"}},
            ),
            prompt_version="policy_impact_v1",
            system_prompt=(
                "You are the policy_impact skill. Analyze only policy content, "
                "policy level, impact chain, likely beneficiary and damaged "
                "directions, impact cycle, and policy uncertainty. Treat policy "
                "evidence as analytically important. Do not update skill "
                "weights or final decision weights in this stage. Do not perform "
                "technical trend analysis, announcement risk analysis, position "
                "sizing, orders, take-profit, or stop-loss. Return structured JSON "
                "matching the SkillResultPayload schema. Use direction only as "
                "bullish, bearish, neutral, or uncertain. Confidence must be a "
                "number from 0 to 1. Every non-uncertain conclusion must cite at "
                "least one supporting_evidence_id. Always include risk_factors, "
                "invalid_conditions, and missing_information."
            ),
        )


class AnnouncementRiskSkill(PromptSkill):
    def __init__(self) -> None:
        super().__init__(
            definition=SkillDefinition(
                skill_id="announcement_risk",
                name="Announcement Risk",
                version="1.0.0",
                description=(
                    "Independent analysis of company announcements, financial and "
                    "governance risk, reductions, pledges, lawsuits, penalties, "
                    "earnings previews, and material events."
                ),
                supported_markets=SUPPORTED_MARKETS,
                supported_asset_types=SUPPORTED_ASSET_TYPES,
                supported_horizons=SUPPORTED_HORIZONS,
                required_evidence_types=("company_announcement",),
                input_schema=SkillInput.model_json_schema(),
                output_schema=SkillResultPayload.model_json_schema(),
            ),
            prompt_version="announcement_risk_v1",
            system_prompt=(
                "You are the announcement_risk skill. Analyze only company "
                "announcements, financial and governance risk, shareholder "
                "reductions, share pledges, lawsuits, penalties, earnings previews, "
                "and other material events. Distinguish facts from speculation in "
                "the reasoning_summary and assumptions. Do not analyze price trend, "
                "moving averages, policy impact, sector strength, position sizing, "
                "orders, take-profit, or stop-loss. Return structured JSON matching "
                "the SkillResultPayload schema. Use direction only as bullish, "
                "bearish, neutral, or uncertain. Confidence must be a number from "
                "0 to 1. Every non-uncertain conclusion must cite at least one "
                "supporting_evidence_id. Always include risk_factors, "
                "invalid_conditions, and missing_information."
            ),
        )
