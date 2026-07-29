from __future__ import annotations

import pytest


def test_tenacity_fetcher_retries_transient_http_failures() -> None:
    from aios.integrations.http_retry import RetryingHTTPFetcher

    calls = 0

    def fetch_once(_url: str) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("temporary network failure")
        return b"real response body"

    result = RetryingHTTPFetcher(fetch_once, attempts=3, wait_seconds=0).fetch(
        "https://example.test/feed.xml"
    )

    assert result == b"real response body"
    assert calls == 2


def test_tenacity_fetcher_reraises_after_retry_budget() -> None:
    from aios.integrations.http_retry import RetryingHTTPFetcher

    calls = 0

    def fetch_once(_url: str) -> bytes:
        nonlocal calls
        calls += 1
        raise OSError("provider still unavailable")

    with pytest.raises(OSError, match="provider still unavailable"):
        RetryingHTTPFetcher(fetch_once, attempts=2, wait_seconds=0).fetch(
            "https://example.test/feed.xml"
        )

    assert calls == 2
