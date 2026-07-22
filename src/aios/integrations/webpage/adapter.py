from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import trafilatura
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aios.integrations.http_client import HTTPClientConfig, RequestsHTTPClient
from aios.integrations.http_retry import RetryingHTTPFetcher


class TrafilaturaFetchError(Exception):
    """Raised when a webpage cannot be fetched."""


class TrafilaturaExtractionError(Exception):
    """Raised when trafilatura cannot extract useful text."""


class WebpageHTTPClient(Protocol):
    def fetch(self, url: str) -> bytes:
        """Fetch raw webpage bytes."""


class UrllibWebpageHTTPClient:
    def __init__(
        self,
        attempts: int = 3,
        wait_seconds: float = 1.0,
        http_config: HTTPClientConfig | None = None,
    ) -> None:
        self._client = RequestsHTTPClient(config=http_config)
        self.last_from_cache: bool | None = None
        self._fetcher = RetryingHTTPFetcher(
            self._fetch_once,
            attempts=attempts,
            wait_seconds=wait_seconds,
        )

    def fetch(self, url: str) -> bytes:
        try:
            body = self._fetcher.fetch(url)
            self.last_from_cache = self._client.last_from_cache
            return body
        except OSError as exc:
            msg = f"Webpage request failed for {url}"
            raise TrafilaturaFetchError(msg) from exc

    def _fetch_once(self, url: str) -> bytes:
        try:
            body = self._client.fetch(url)
        except Exception as exc:
            raise OSError(str(exc)) from exc
        return body


class WebpageExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    provider_name: str = "trafilatura"
    source_id: str = Field(min_length=1)
    page_url: str = Field(min_length=1)
    title: str
    published_at: datetime | None = None
    fetched_at: datetime
    response_from_cache: bool | None = None
    extracted_text: str = Field(min_length=1)
    extracted_metadata: dict[str, Any]
    raw_response_path: Path | None = None
    pre_normalized_path: Path | None = None
    source_trace: dict[str, Any]

    @field_validator("published_at", "fetched_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "webpage datetimes must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)


class WebpageCollectionError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_name: str = "trafilatura"
    source_id: str
    page_url: str
    message: str


class WebpageCollectionBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_name: str = "trafilatura"
    results: tuple[WebpageExtractionResult, ...]
    errors: tuple[WebpageCollectionError, ...]


class TrafilaturaWebpageAdapter:
    def __init__(self, http_client: WebpageHTTPClient | None = None) -> None:
        self._http_client = http_client or UrllibWebpageHTTPClient()

    def fetch(
        self,
        *,
        page_url: str,
        source_id: str,
        persist_dir: Path | None = None,
    ) -> WebpageExtractionResult:
        fetched_at = datetime.now(UTC)
        raw_bytes = self._http_client.fetch(page_url)
        return self.extract_bytes(
            raw_bytes,
            page_url=page_url,
            source_id=source_id,
            fetched_at=fetched_at,
            persist_dir=persist_dir,
        )

    def fetch_many(
        self,
        pages: list[tuple[str, str]] | tuple[tuple[str, str], ...],
        *,
        fetched_at: datetime | None = None,
        persist_dir: Path | None = None,
    ) -> WebpageCollectionBatch:
        results: list[WebpageExtractionResult] = []
        errors: list[WebpageCollectionError] = []
        collected_at = fetched_at or datetime.now(UTC)
        for source_id, page_url in pages:
            try:
                raw_bytes = self._http_client.fetch(page_url)
                results.append(
                    self.extract_bytes(
                        raw_bytes,
                        page_url=page_url,
                        source_id=source_id,
                        fetched_at=collected_at,
                        persist_dir=persist_dir,
                    )
                )
            except Exception as exc:
                errors.append(
                    WebpageCollectionError(
                        source_id=source_id,
                        page_url=page_url,
                        message=str(exc),
                    )
                )
        return WebpageCollectionBatch(results=tuple(results), errors=tuple(errors))

    def extract_bytes(
        self,
        raw_bytes: bytes,
        *,
        page_url: str,
        source_id: str,
        fetched_at: datetime,
        persist_dir: Path | None = None,
    ) -> WebpageExtractionResult:
        raw_html = raw_bytes.decode("utf-8", errors="replace")
        extracted = trafilatura.extract(
            raw_html,
            url=page_url,
            output_format="json",
            with_metadata=True,
            include_comments=False,
            include_tables=True,
        )
        if not extracted:
            msg = f"trafilatura could not extract text for {page_url}"
            raise TrafilaturaExtractionError(msg)
        payload = json.loads(extracted)
        text = str(payload.get("text") or "").strip()
        if not text:
            msg = f"trafilatura could not extract text for {page_url}"
            raise TrafilaturaExtractionError(msg)

        raw_path, pre_normalized_path = self._persist(
            raw_bytes=raw_bytes,
            payload=payload,
            page_url=page_url,
            source_id=source_id,
            fetched_at=fetched_at,
            persist_dir=persist_dir,
        )
        return WebpageExtractionResult(
            source_id=source_id,
            page_url=page_url,
            title=str(payload.get("title") or ""),
            published_at=_published_at(payload),
            fetched_at=fetched_at,
            response_from_cache=_response_from_cache(self._http_client),
            extracted_text=text,
            extracted_metadata=payload,
            raw_response_path=raw_path,
            pre_normalized_path=pre_normalized_path,
            source_trace={
                "provider_name": "trafilatura",
                "page_url": page_url,
                "source_id": source_id,
                "hostname": payload.get("hostname"),
                "fingerprint": payload.get("fingerprint"),
            },
        )

    def _persist(
        self,
        *,
        raw_bytes: bytes,
        payload: dict[str, Any],
        page_url: str,
        source_id: str,
        fetched_at: datetime,
        persist_dir: Path | None,
    ) -> tuple[Path | None, Path | None]:
        if persist_dir is None:
            return None, None

        persist_dir.mkdir(parents=True, exist_ok=True)
        suffix = _artifact_suffix(source_id, page_url, fetched_at)
        raw_path = persist_dir / f"{suffix}.html"
        pre_normalized_path = persist_dir / f"{suffix}.trafilatura.json"
        raw_path.write_bytes(raw_bytes)
        pre_normalized_path.write_text(
            json.dumps(
                {
                    "provider_name": "trafilatura",
                    "source_id": source_id,
                    "page_url": page_url,
                    "fetched_at": fetched_at.astimezone(UTC).isoformat(),
                    "payload": payload,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return raw_path, pre_normalized_path


def _published_at(payload: dict[str, Any]) -> datetime | None:
    date_value = payload.get("date")
    if not isinstance(date_value, str) or not date_value:
        return None
    try:
        parsed = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _artifact_suffix(source_id: str, page_url: str, fetched_at: datetime) -> str:
    safe_source = re.sub(r"[^A-Za-z0-9_.-]+", "-", source_id).strip("-")
    digest = hashlib.sha256(page_url.encode("utf-8")).hexdigest()[:12]
    timestamp = fetched_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{safe_source}-{timestamp}-{digest}"


def _response_from_cache(client: WebpageHTTPClient) -> bool | None:
    value = getattr(client, "last_from_cache", None)
    if isinstance(value, bool):
        return value
    return None
