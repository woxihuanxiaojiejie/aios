from __future__ import annotations

import pytest


def test_provider_rate_limiter_rejects_when_wait_strategy_is_fail_fast() -> None:
    from aios.integrations.http_rate_limit import (
        ProviderRateLimitConfig,
        ProviderRateLimiter,
        ProviderRateLimitExceeded,
    )

    limiter = ProviderRateLimiter(
        {
            "rss": ProviderRateLimitConfig(
                max_requests=1,
                window_seconds=60,
                wait_strategy="fail_fast",
            )
        }
    )

    limiter.acquire("rss")
    with pytest.raises(ProviderRateLimitExceeded, match="rss"):
        limiter.acquire("rss")


def test_provider_rate_limiter_supports_different_provider_configs() -> None:
    from aios.integrations.http_rate_limit import (
        ProviderRateLimitConfig,
        ProviderRateLimiter,
        ProviderRateLimitExceeded,
    )

    limiter = ProviderRateLimiter(
        {
            "rss": ProviderRateLimitConfig(
                max_requests=1,
                window_seconds=60,
                wait_strategy="fail_fast",
            ),
            "webpage": ProviderRateLimitConfig(
                max_requests=2,
                window_seconds=60,
                wait_strategy="fail_fast",
            ),
        }
    )

    limiter.acquire("rss")
    limiter.acquire("webpage")
    limiter.acquire("webpage")

    with pytest.raises(ProviderRateLimitExceeded):
        limiter.acquire("rss")


def test_http_client_acquires_rate_limit_before_each_retry_attempt() -> None:
    from aios.integrations.http_client import HTTPClientConfig, RequestsHTTPClient

    class Limiter:
        def __init__(self) -> None:
            self.providers: list[str] = []

        def acquire(self, provider_name: str) -> None:
            self.providers.append(provider_name)

    class Response:
        from_cache = False
        content = b"ok"

        def raise_for_status(self) -> None:
            return None

    class Session:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, _url: str, timeout: float) -> Response:
            self.calls += 1
            if self.calls == 1:
                raise OSError("temporary")
            return Response()

    limiter = Limiter()
    session = Session()
    client = RequestsHTTPClient(
        config=HTTPClientConfig(provider_name="rss"),
        session=session,
        rate_limiter=limiter,
        retry_attempts=2,
        retry_wait_seconds=0,
    )

    response = client.fetch_response("https://example.test/feed.xml")

    assert response.body == b"ok"
    assert session.calls == 2
    assert limiter.providers == ["rss", "rss"]
