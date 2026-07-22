from __future__ import annotations

import calendar
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from time import struct_time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import feedparser  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RSSFeedFetchError(Exception):
    """Raised when an RSS feed cannot be fetched."""


class RSSFeedParseError(Exception):
    """Raised when feedparser cannot produce usable RSS entries."""


class RSSHTTPClient(Protocol):
    def fetch(self, url: str) -> bytes:
        """Fetch raw feed bytes."""


class UrllibRSSHTTPClient:
    def fetch(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": "aios-brain001/0.1"})
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            msg = f"RSS feed request failed for {url}"
            raise RSSFeedFetchError(msg) from exc
        if not isinstance(body, bytes):
            msg = f"RSS feed response was not bytes for {url}"
            raise RSSFeedFetchError(msg)
        return body


class RSSNewsItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    provider_name: str = "feedparser"
    feed_url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    published_at: datetime | None = None
    collected_at: datetime
    raw_content: str = Field(min_length=1)
    raw_entry: dict[str, Any]
    source_trace: dict[str, Any]

    @field_validator("published_at", "collected_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "RSS datetimes must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)


class RSSFeedResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    provider_name: str = "feedparser"
    source_id: str = Field(min_length=1)
    feed_url: str = Field(min_length=1)
    feed_title: str
    fetched_at: datetime
    raw_response_path: Path | None = None
    pre_normalized_path: Path | None = None
    items: tuple[RSSNewsItem, ...]

    @field_validator("fetched_at")
    @classmethod
    def validate_fetched_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "fetched_at must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)


class RSSCollectionError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_name: str = "feedparser"
    source_id: str
    feed_url: str
    message: str


class RSSCollectionBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_name: str = "feedparser"
    results: tuple[RSSFeedResult, ...]
    errors: tuple[RSSCollectionError, ...]


class FeedparserRSSAdapter:
    def __init__(self, http_client: RSSHTTPClient | None = None) -> None:
        self._http_client = http_client or UrllibRSSHTTPClient()

    def fetch(
        self,
        *,
        feed_url: str,
        source_id: str,
        persist_dir: Path | None = None,
    ) -> RSSFeedResult:
        fetched_at = datetime.now(UTC)
        raw_bytes = self._http_client.fetch(feed_url)
        return self.parse_bytes(
            raw_bytes,
            feed_url=feed_url,
            source_id=source_id,
            fetched_at=fetched_at,
            persist_dir=persist_dir,
        )

    def fetch_many(
        self,
        feeds: list[tuple[str, str]] | tuple[tuple[str, str], ...],
        *,
        fetched_at: datetime | None = None,
        persist_dir: Path | None = None,
    ) -> RSSCollectionBatch:
        results: list[RSSFeedResult] = []
        errors: list[RSSCollectionError] = []
        collected_at = fetched_at or datetime.now(UTC)
        for source_id, feed_url in feeds:
            try:
                raw_bytes = self._http_client.fetch(feed_url)
                results.append(
                    self.parse_bytes(
                        raw_bytes,
                        feed_url=feed_url,
                        source_id=source_id,
                        fetched_at=collected_at,
                        persist_dir=persist_dir,
                    )
                )
            except Exception as exc:
                errors.append(
                    RSSCollectionError(
                        source_id=source_id,
                        feed_url=feed_url,
                        message=str(exc),
                    )
                )
        return RSSCollectionBatch(results=tuple(results), errors=tuple(errors))

    def parse_bytes(
        self,
        raw_bytes: bytes,
        *,
        feed_url: str,
        source_id: str,
        fetched_at: datetime,
        persist_dir: Path | None = None,
    ) -> RSSFeedResult:
        parsed = feedparser.parse(raw_bytes)
        entries = [_plain_entry(entry) for entry in parsed.entries]
        if not entries:
            msg = f"feedparser produced no entries for {feed_url}"
            raise RSSFeedParseError(msg)

        feed_title = str(parsed.feed.get("title", ""))
        raw_path, pre_normalized_path = self._persist(
            raw_bytes=raw_bytes,
            entries=entries,
            feed_url=feed_url,
            source_id=source_id,
            fetched_at=fetched_at,
            persist_dir=persist_dir,
        )
        items = tuple(
            _entry_to_item(
                entry,
                source_id=source_id,
                feed_url=feed_url,
                fetched_at=fetched_at,
            )
            for entry in entries
        )
        return RSSFeedResult(
            source_id=source_id,
            feed_url=feed_url,
            feed_title=feed_title,
            fetched_at=fetched_at,
            raw_response_path=raw_path,
            pre_normalized_path=pre_normalized_path,
            items=items,
        )

    def _persist(
        self,
        *,
        raw_bytes: bytes,
        entries: list[dict[str, Any]],
        feed_url: str,
        source_id: str,
        fetched_at: datetime,
        persist_dir: Path | None,
    ) -> tuple[Path | None, Path | None]:
        if persist_dir is None:
            return None, None

        persist_dir.mkdir(parents=True, exist_ok=True)
        suffix = _artifact_suffix(source_id, feed_url, fetched_at)
        raw_path = persist_dir / f"{suffix}.xml"
        pre_normalized_path = persist_dir / f"{suffix}.pre_normalized.json"
        raw_path.write_bytes(raw_bytes)
        pre_normalized_path.write_text(
            json.dumps(
                {
                    "provider_name": "feedparser",
                    "source_id": source_id,
                    "feed_url": feed_url,
                    "fetched_at": fetched_at.astimezone(UTC).isoformat(),
                    "entries": entries,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return raw_path, pre_normalized_path


def _entry_to_item(
    entry: dict[str, Any],
    *,
    source_id: str,
    feed_url: str,
    fetched_at: datetime,
) -> RSSNewsItem:
    title = str(entry.get("title") or "").strip()
    link = str(entry.get("link") or entry.get("id") or "").strip()
    raw_content = _raw_content(entry)
    return RSSNewsItem(
        source_id=source_id,
        feed_url=feed_url,
        title=title,
        url=link,
        published_at=_published_at(entry),
        collected_at=fetched_at,
        raw_content=raw_content,
        raw_entry=entry,
        source_trace={
            "provider_name": "feedparser",
            "feed_url": feed_url,
            "source_id": source_id,
            "entry_id": entry.get("id"),
            "entry_link": link,
        },
    )


def _plain_entry(entry: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in dict(entry).items():
        result[str(key)] = _plain_value(value)
    return result


def _plain_value(value: Any) -> Any:
    if isinstance(value, struct_time):
        return list(value)
    if isinstance(value, list):
        return [_plain_value(item) for item in value]
    if isinstance(value, tuple):
        return [_plain_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _published_at(entry: dict[str, Any]) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if isinstance(parsed, list | tuple) and len(parsed) >= 9:
        return datetime.fromtimestamp(calendar.timegm(tuple(parsed[:9])), tz=UTC)
    return None


def _raw_content(entry: dict[str, Any]) -> str:
    for key in ("summary", "description", "title"):
        value = str(entry.get(key) or "").strip()
        if value:
            return value
    return str(entry)


def _artifact_suffix(source_id: str, feed_url: str, fetched_at: datetime) -> str:
    safe_source = re.sub(r"[^A-Za-z0-9_.-]+", "-", source_id).strip("-")
    digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()[:12]
    timestamp = fetched_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{safe_source}-{timestamp}-{digest}"
