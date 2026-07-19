from __future__ import annotations


class MarketDataError(Exception):
    """Base error for external market data adapters."""


class UnsupportedMarketSymbolError(MarketDataError):
    """Raised when a provider does not support a requested symbol."""


class UnsupportedAdjustmentError(MarketDataError):
    """Raised when a provider does not support a requested adjustment."""


class MarketDataDateRangeError(MarketDataError):
    """Raised when a market data date range is invalid."""


class EmptyMarketDataError(MarketDataError):
    """Raised when a provider returns no rows for a request."""


class MissingMarketDataFieldError(MarketDataError):
    """Raised when provider data is missing a required field."""


class InvalidMarketDataError(MarketDataError):
    """Raised when provider data cannot be normalized."""


class UpstreamMarketDataError(MarketDataError):
    """Raised when an upstream provider request fails."""
