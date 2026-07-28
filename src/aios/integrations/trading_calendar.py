from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal


class MarketTradingCalendar:
    def __init__(self, *, calendar_name: str = "SSE") -> None:
        self._calendar = mcal.get_calendar(_calendar_name(calendar_name))

    def is_research_time(
        self,
        *,
        as_of: datetime,
        schedule_time: time,
        timezone_name: str,
    ) -> bool:
        local_as_of = as_of.astimezone(ZoneInfo(timezone_name))
        return self._is_session(local_as_of) and local_as_of.time() >= schedule_time

    def next_research_at(
        self,
        *,
        after: datetime,
        schedule_time: time,
        timezone_name: str,
    ) -> datetime:
        zone = ZoneInfo(timezone_name)
        local_after = after.astimezone(zone)
        candidate_date = local_after.date()
        if local_after.time() >= schedule_time:
            candidate_date += timedelta(days=1)
        for offset in range(370):
            candidate = candidate_date + timedelta(days=offset)
            candidate_dt = datetime.combine(candidate, schedule_time, zone)
            if self._is_session(candidate_dt):
                return candidate_dt.astimezone(UTC)
        msg = "could not find next trading session within 370 days"
        raise ValueError(msg)

    def _is_session(self, value: datetime) -> bool:
        day = value.date().isoformat()
        return bool(self._calendar.valid_days(day, day).size)


def _calendar_name(calendar_name: str) -> str:
    normalized = calendar_name.strip().upper()
    if normalized in {"SZ", "SZSE", "XSHE"}:
        return "SSE"
    return normalized
