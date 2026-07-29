"""RSS feed integration backed by feedparser."""

from aios.integrations.rss.adapter import (
    FeedparserRSSAdapter,
    RSSCollectionBatch,
    RSSCollectionError,
    RSSFeedFetchError,
    RSSFeedParseError,
    RSSFeedResult,
    RSSNewsItem,
)

__all__ = [
    "FeedparserRSSAdapter",
    "RSSCollectionBatch",
    "RSSCollectionError",
    "RSSFeedFetchError",
    "RSSFeedParseError",
    "RSSFeedResult",
    "RSSNewsItem",
]
