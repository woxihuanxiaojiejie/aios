from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from aios.integrations.akshare.client import AKShareClient
from aios.integrations.fingerprint import content_fingerprint
from aios.integrations.provider_records import AnnouncementIntakeRecord

SOURCE_FUNCTION = "stock_zh_a_disclosure_report_cninfo"


class AKShareAnnouncementClient(Protocol):
    def stock_zh_a_disclosure_report_cninfo(
        self,
        *,
        symbol: str,
        market: str,
        category: str,
        start_date: str,
        end_date: str,
    ) -> Any:
        """Fetch CNInfo disclosure report rows through AKShare."""


class AKShareAnnouncementItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_name: str = "akshare"
    source_function: str = SOURCE_FUNCTION
    symbol: str = Field(min_length=1)
    short_name: str
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    published_at: datetime
    collected_at: datetime
    fingerprint: str = Field(min_length=64, max_length=64)
    raw_row: dict[str, Any]
    source_trace: dict[str, Any]

    @field_validator("published_at", "collected_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "announcement datetimes must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)


class AKShareAnnouncementsResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    provider_name: str = "akshare"
    source_function: str = SOURCE_FUNCTION
    symbol: str = Field(min_length=1)
    market: str
    category: str
    start_date: date
    end_date: date
    fetched_at: datetime
    raw_response_path: Path | None = None
    pre_normalized_path: Path | None = None
    intake_records: tuple[AnnouncementIntakeRecord, ...] = ()
    items: tuple[AKShareAnnouncementItem, ...]

    @field_validator("fetched_at")
    @classmethod
    def validate_fetched_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "fetched_at must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)


class AKShareAnnouncementCollectionError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_name: str = "akshare"
    source_function: str = SOURCE_FUNCTION
    symbol: str
    category: str
    message: str


class AKShareAnnouncementBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_name: str = "akshare"
    source_function: str = SOURCE_FUNCTION
    results: tuple[AKShareAnnouncementsResult, ...]
    errors: tuple[AKShareAnnouncementCollectionError, ...]


class AKShareAnnouncementsAdapter:
    def __init__(self, client: AKShareAnnouncementClient | None = None) -> None:
        self._client = client or AKShareClient()

    def fetch_cninfo_disclosures(
        self,
        *,
        symbol: str,
        market: str,
        category: str,
        start_date: date,
        end_date: date,
        fetched_at: datetime | None = None,
        persist_dir: Path | None = None,
    ) -> AKShareAnnouncementsResult:
        collected_at = fetched_at or datetime.now(UTC)
        rows = _records_from_frame(
            self._client.stock_zh_a_disclosure_report_cninfo(
                symbol=symbol,
                market=market,
                category=category,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )
        )
        raw_path, pre_normalized_path = self._persist(
            rows=rows,
            symbol=symbol,
            market=market,
            category=category,
            start_date=start_date,
            end_date=end_date,
            fetched_at=collected_at,
            persist_dir=persist_dir,
        )
        items = tuple(_row_to_item(row, collected_at=collected_at) for row in rows)
        try:
            intake_records = tuple(
                _item_to_intake_record(item, raw_path=raw_path) for item in items
            )
        except ValidationError as exc:
            msg = f"invalid AKShare announcement intake record for {symbol}"
            raise ValueError(msg) from exc
        return AKShareAnnouncementsResult(
            symbol=symbol,
            market=market,
            category=category,
            start_date=start_date,
            end_date=end_date,
            fetched_at=collected_at,
            raw_response_path=raw_path,
            pre_normalized_path=pre_normalized_path,
            intake_records=intake_records,
            items=items,
        )

    def fetch_many_cninfo_disclosures(
        self,
        requests: list[tuple[str, str]] | tuple[tuple[str, str], ...],
        *,
        market: str,
        start_date: date,
        end_date: date,
        fetched_at: datetime | None = None,
        persist_dir: Path | None = None,
    ) -> AKShareAnnouncementBatch:
        results: list[AKShareAnnouncementsResult] = []
        errors: list[AKShareAnnouncementCollectionError] = []
        collected_at = fetched_at or datetime.now(UTC)
        for symbol, category in requests:
            try:
                results.append(
                    self.fetch_cninfo_disclosures(
                        symbol=symbol,
                        market=market,
                        category=category,
                        start_date=start_date,
                        end_date=end_date,
                        fetched_at=collected_at,
                        persist_dir=persist_dir,
                    )
                )
            except Exception as exc:
                errors.append(
                    AKShareAnnouncementCollectionError(
                        symbol=symbol,
                        category=category,
                        message=str(exc),
                    )
                )
        return AKShareAnnouncementBatch(results=tuple(results), errors=tuple(errors))

    def _persist(
        self,
        *,
        rows: list[dict[str, Any]],
        symbol: str,
        market: str,
        category: str,
        start_date: date,
        end_date: date,
        fetched_at: datetime,
        persist_dir: Path | None,
    ) -> tuple[Path | None, Path | None]:
        if persist_dir is None:
            return None, None

        persist_dir.mkdir(parents=True, exist_ok=True)
        suffix = _artifact_suffix(symbol, category, fetched_at)
        raw_path = persist_dir / f"{suffix}.akshare_raw.json"
        pre_normalized_path = persist_dir / f"{suffix}.pre_normalized.json"
        payload = {
            "provider_name": "akshare",
            "source_function": SOURCE_FUNCTION,
            "symbol": symbol,
            "market": market,
            "category": category,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "fetched_at": fetched_at.astimezone(UTC).isoformat(),
            "rows": rows,
        }
        raw_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        pre_normalized_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return raw_path, pre_normalized_path


def _records_from_frame(frame: Any) -> list[dict[str, Any]]:
    if isinstance(frame, list):
        return [dict(row) for row in frame]
    if hasattr(frame, "to_dict"):
        records = frame.to_dict(orient="records")
        if isinstance(records, list):
            return [dict(row) for row in records]
    return [dict(row) for row in frame]


def _row_to_item(
    row: dict[str, Any],
    *,
    collected_at: datetime,
) -> AKShareAnnouncementItem:
    symbol = str(row.get("代码") or "")
    title = str(row.get("公告标题") or "")
    url = str(row.get("公告链接") or "")
    published_at = datetime.combine(
        date.fromisoformat(str(row.get("公告时间"))),
        datetime.min.time(),
        tzinfo=UTC,
    )
    return AKShareAnnouncementItem(
        symbol=symbol,
        short_name=str(row.get("简称") or ""),
        title=title,
        url=url,
        published_at=published_at,
        collected_at=collected_at,
        fingerprint=content_fingerprint(f"{symbol}\n{title}\n{url}"),
        raw_row=row,
        source_trace={
            "provider_name": "akshare",
            "source_function": SOURCE_FUNCTION,
            "symbol": symbol,
            "announcement_url": url,
            "announcement_time": row.get("公告时间"),
        },
    )


def _item_to_intake_record(
    item: AKShareAnnouncementItem,
    *,
    raw_path: Path | None,
) -> AnnouncementIntakeRecord:
    return AnnouncementIntakeRecord(
        source="akshare",
        source_type="announcement",
        source_url=item.url,
        source_identifier=item.symbol,
        published_at=item.published_at,
        collected_at=item.collected_at,
        raw_artifact_path=raw_path or Path(""),
        title=item.title,
        summary=None,
        content=item.title,
        fingerprint=item.fingerprint,
    )


def _artifact_suffix(symbol: str, category: str, fetched_at: datetime) -> str:
    safe_symbol = re.sub(r"[^A-Za-z0-9_.-]+", "-", symbol).strip("-")
    digest = hashlib.sha256(category.encode("utf-8")).hexdigest()[:12]
    timestamp = fetched_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{safe_symbol}-{timestamp}-{digest}"
