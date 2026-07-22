from __future__ import annotations

from collections.abc import Callable

from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed


class RetryingHTTPFetcher:
    def __init__(
        self,
        fetch_once: Callable[[str], bytes],
        *,
        attempts: int = 3,
        wait_seconds: float = 1.0,
    ) -> None:
        self._fetch_once = fetch_once
        self._attempts = attempts
        self._wait_seconds = wait_seconds

    def fetch(self, url: str) -> bytes:
        retryer = Retrying(
            stop=stop_after_attempt(self._attempts),
            wait=wait_fixed(self._wait_seconds),
            retry=retry_if_exception_type(OSError),
            reraise=True,
        )
        return retryer(self._fetch_once, url)
