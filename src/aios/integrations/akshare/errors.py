from __future__ import annotations


class MarketDataError(Exception):
    """Base class for market data adapter errors."""


class UnsupportedMarketSymbolError(MarketDataError):
    """Raised when a requested symbol is outside the supported market."""


class UnsupportedAdjustmentError(MarketDataError):
    """Raised when the adjustment mode is not supported."""


class MarketDataDateRangeError(MarketDataError):
    """Raised when the requested date range is invalid."""


class EmptyMarketDataError(MarketDataError):
    """Raised when the upstream source returns no rows."""


class MissingMarketDataFieldError(MarketDataError):
    """Raised when required upstream columns are absent."""


class InvalidMarketDataError(MarketDataError):
    """Raised when upstream rows fail normalization."""


class UpstreamMarketDataError(MarketDataError):
    """Raised when AKShare or its upstream source fails."""
