from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aios.adapters.market_data import Adjustment, MarketBar, MarketDataAdapter
from aios.adapters.market_errors import (
    MarketDataDateRangeError,
    UnsupportedAdjustmentError,
)
from aios.adapters.market_evidence import (
    market_bar_content_hash,
    market_bar_to_evidence,
)
from aios.kernel.evidence import Evidence
from aios.workflows.decision_lifecycle import DecisionLifecycleService


@dataclass(frozen=True)
class MarketEvidenceImportResult:
    symbol: str
    requested: int
    created: int
    existing: int
    evidence_ids: list[str]


class MarketEvidenceImportService:
    def __init__(
        self,
        *,
        adapter: MarketDataAdapter,
        lifecycle: DecisionLifecycleService,
        reliability: float = 0.95,
    ) -> None:
        self._adapter = adapter
        self._lifecycle = lifecycle
        self._reliability = reliability

    def preview_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: str | Adjustment,
    ) -> list[MarketBar]:
        parsed_adjustment = self._parse_request(
            symbol, start_date, end_date, adjustment
        )
        return self._adapter.fetch_daily_bars(
            symbol,
            start_date,
            end_date,
            parsed_adjustment,
        )

    def import_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: str | Adjustment,
    ) -> MarketEvidenceImportResult:
        bars = self.preview_daily_bars(symbol, start_date, end_date, adjustment)
        existing_by_hash = {
            evidence.content_hash: evidence
            for evidence in self._lifecycle.list_entities(Evidence)
            if evidence.evidence_type == "market_daily_bar"
        }
        existing_by_key = {
            self._idempotency_key(evidence): evidence
            for evidence in existing_by_hash.values()
        }

        evidence_ids: list[str] = []
        created = 0
        existing = 0
        for bar in bars:
            content_hash = market_bar_content_hash(bar)
            key = (
                bar.source,
                bar.symbol,
                bar.trade_date.isoformat(),
                bar.adjustment.value,
            )
            if content_hash in existing_by_hash:
                evidence = existing_by_hash[content_hash]
                evidence_ids.append(evidence.evidence_id)
                existing += 1
                continue

            evidence = market_bar_to_evidence(bar, reliability=self._reliability)
            if key in existing_by_key:
                evidence = Evidence(
                    **{
                        **evidence.model_dump(),
                        "metadata": {
                            **evidence.metadata,
                            "possible_revision": True,
                        },
                    }
                )
            registered = self._lifecycle.register_evidence(evidence)
            existing_by_hash[registered.content_hash] = registered
            existing_by_key[key] = registered
            evidence_ids.append(registered.evidence_id)
            created += 1

        return MarketEvidenceImportResult(
            symbol=symbol,
            requested=len(bars),
            created=created,
            existing=existing,
            evidence_ids=evidence_ids,
        )

    def _parse_request(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: str | Adjustment,
    ) -> Adjustment:
        if start_date > end_date:
            msg = "start_date must not be later than end_date"
            raise MarketDataDateRangeError(msg)
        try:
            return (
                adjustment
                if isinstance(adjustment, Adjustment)
                else Adjustment(adjustment)
            )
        except ValueError as exc:
            msg = f"Unsupported adjustment: {adjustment}"
            raise UnsupportedAdjustmentError(msg) from exc

    def _idempotency_key(self, evidence: Evidence) -> tuple[str, str, str, str]:
        market_bar = evidence.metadata.get("market_bar", {})
        return (
            evidence.source,
            str(market_bar.get("symbol", "")),
            str(market_bar.get("trade_date", "")),
            str(market_bar.get("adjustment", "")),
        )
