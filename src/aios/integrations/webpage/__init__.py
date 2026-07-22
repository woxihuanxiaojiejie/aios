"""Webpage extraction integration backed by trafilatura."""

from aios.integrations.webpage.adapter import (
    TrafilaturaExtractionError,
    TrafilaturaFetchError,
    TrafilaturaWebpageAdapter,
    WebpageCollectionBatch,
    WebpageCollectionError,
    WebpageExtractionResult,
)

__all__ = [
    "TrafilaturaExtractionError",
    "TrafilaturaFetchError",
    "TrafilaturaWebpageAdapter",
    "WebpageCollectionBatch",
    "WebpageCollectionError",
    "WebpageExtractionResult",
]
