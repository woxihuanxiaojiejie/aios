from __future__ import annotations

from datetime import UTC, datetime, time

from aios.integrations.trading_calendar import MarketTradingCalendar


def test_market_trading_calendar_skips_weekends_and_returns_utc() -> None:
    calendar = MarketTradingCalendar(calendar_name="SSE")

    next_run = calendar.next_research_at(
        after=datetime(2026, 8, 1, 7, 0, tzinfo=UTC),
        schedule_time=time(15, 0),
        timezone_name="Asia/Shanghai",
    )

    assert next_run == datetime(2026, 8, 3, 7, 0, tzinfo=UTC)
    assert calendar.is_research_time(
        as_of=next_run,
        schedule_time=time(15, 0),
        timezone_name="Asia/Shanghai",
    )
    assert not calendar.is_research_time(
        as_of=datetime(2026, 8, 1, 7, 0, tzinfo=UTC),
        schedule_time=time(15, 0),
        timezone_name="Asia/Shanghai",
    )
