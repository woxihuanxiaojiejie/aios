"""Vibe-Trading upstream boundary for AIOS.

Provides the :class:`VibeTradingAdapter` that wraps
`HKUDS/Vibe-Trading`_ as an optional external research capability. The adapter
keeps AIOS-side imports stable without directly depending on Vibe-Trading
internal modules.

This module is intentionally narrow: it does not reproduce Vibe-Trading core
logic, does not bypass AIOS lifecycle, and does not write AIOS kernel entities.
"""

from aios.vibe_trading.adapter import VibeTradingAdapter
from aios.vibe_trading.output_mapper import VibeTradingRawResult

__all__ = ["VibeTradingAdapter", "VibeTradingRawResult"]
