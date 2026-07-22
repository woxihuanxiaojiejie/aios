from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def test_requests_cache_http_client_is_disabled_by_default() -> None:
    from aios.integrations.http_client import HTTPClientConfig, RequestsHTTPClient

    config = HTTPClientConfig()
    client = RequestsHTTPClient(config=config)

    assert config.cache_enabled is False
    assert client.cache_enabled is False


def test_requests_cache_http_client_reports_cache_hits(tmp_path: Path) -> None:
    from aios.integrations.http_client import HTTPClientConfig, RequestsHTTPClient

    calls = 0

    class Response:
        from_cache = False
        content = b"network body"

        def raise_for_status(self) -> None:
            return None

    class Session:
        def get(self, url: str, timeout: float) -> Response:
            nonlocal calls
            calls += 1
            assert url == "https://example.test/feed.xml"
            assert timeout == 30.0
            response = Response()
            response.from_cache = calls > 1
            return response

    client = RequestsHTTPClient(
        config=HTTPClientConfig(
            cache_enabled=True,
            cache_name=tmp_path / "http-cache",
            expire_after_seconds=60,
        ),
        session=Session(),
    )

    first = client.fetch_response("https://example.test/feed.xml")
    second = client.fetch_response("https://example.test/feed.xml")

    assert first.from_cache is False
    assert second.from_cache is True
    assert second.body == b"network body"


def test_requests_cache_http_client_falls_back_when_cache_setup_fails(
    tmp_path: Path,
) -> None:
    from aios.integrations.http_client import HTTPClientConfig, RequestsHTTPClient

    with patch(
        "aios.integrations.http_client.requests_cache.CachedSession",
        side_effect=OSError("sqlite unavailable"),
    ):
        client = RequestsHTTPClient(
            config=HTTPClientConfig(
                cache_enabled=True,
                cache_name=tmp_path / "http-cache",
            )
        )

    assert client.cache_enabled is False


def test_feedparser_result_exposes_cache_status(tmp_path: Path) -> None:
    from aios.integrations.rss.adapter import FeedparserRSSAdapter

    class Client:
        last_from_cache = True

        def fetch(self, _url: str) -> bytes:
            return Path("tests/fixtures/rss/bbc_business.xml").read_bytes()

    result = FeedparserRSSAdapter(http_client=Client()).fetch(
        feed_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        source_id="bbc-business",
        persist_dir=tmp_path,
    )

    assert result.response_from_cache is True


def test_webpage_result_exposes_cache_status(tmp_path: Path) -> None:
    from aios.integrations.webpage.adapter import TrafilaturaWebpageAdapter

    class Client:
        last_from_cache = True

        def fetch(self, _url: str) -> bytes:
            return Path(
                "tests/fixtures/html/bbc_business_food_prices.html"
            ).read_bytes()

    result = TrafilaturaWebpageAdapter(http_client=Client()).fetch(
        page_url="https://www.bbc.co.uk/news/articles/ckg4xj8j5vjo",
        source_id="bbc-business",
        persist_dir=tmp_path,
    )

    assert result.response_from_cache is True
