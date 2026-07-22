from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import requests_cache

DEFAULT_CACHE_EXPIRE_SECONDS = 900
DEFAULT_RUNTIME_DIR = Path("runtime") / "brain001"


@dataclass(frozen=True)
class HTTPClientConfig:
    cache_enabled: bool = False
    cache_name: Path = DEFAULT_RUNTIME_DIR / "http-cache"
    expire_after_seconds: int = DEFAULT_CACHE_EXPIRE_SECONDS
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class HTTPFetchResponse:
    body: bytes
    from_cache: bool


class RequestsHTTPClient:
    def __init__(
        self,
        *,
        config: HTTPClientConfig | None = None,
        session: Any | None = None,
    ) -> None:
        self._config = config or HTTPClientConfig()
        self._cache_enabled = False
        self.last_from_cache: bool | None = None
        if session is not None:
            self._session = session
            self._cache_enabled = self._config.cache_enabled
            return
        if self._config.cache_enabled:
            try:
                self._config.cache_name.parent.mkdir(parents=True, exist_ok=True)
                self._session = requests_cache.CachedSession(
                    cache_name=str(self._config.cache_name),
                    backend="sqlite",
                    expire_after=self._config.expire_after_seconds,
                )
                self._cache_enabled = True
            except Exception:
                self._session = requests.Session()
                self._cache_enabled = False
        else:
            self._session = requests.Session()

    @property
    def cache_enabled(self) -> bool:
        return self._cache_enabled

    def fetch(self, url: str) -> bytes:
        return self.fetch_response(url).body

    def fetch_response(self, url: str) -> HTTPFetchResponse:
        response = self._session.get(url, timeout=self._config.timeout_seconds)
        response.raise_for_status()
        from_cache = bool(getattr(response, "from_cache", False))
        self.last_from_cache = from_cache
        return HTTPFetchResponse(body=response.content, from_cache=from_cache)
