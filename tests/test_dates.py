from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from familydb.clock import FixedClock, season_for
from familydb.dates import ensure_not_past, parse_date, parse_datetime, utc_iso, weekend_window
from familydb.errors import ToolError

TZ = ZoneInfo("America/Vancouver")


def test_parse_date_and_errors() -> None:
    assert parse_date("2026-09-26") == date(2026, 9, 26)
    with pytest.raises(ToolError):
        parse_date("26/09/2026")


def test_parse_datetime_naive_uses_family_zone_and_respects_dst() -> None:
    winter = parse_datetime("2026-03-07T12:00", TZ)
    summer = parse_datetime("2026-03-08T12:00", TZ)  # DST starts 8 March 2026
    assert winter.utcoffset() == timedelta(hours=-8)
    assert summer.utcoffset() == timedelta(hours=-7)


def test_parse_datetime_aware_is_converted() -> None:
    moment = parse_datetime("2026-09-26T03:00:00+00:00", TZ)
    assert (moment.day, moment.hour) == (25, 20)  # 03:00 UTC is 20:00 the evening before, PDT


def test_ensure_not_past(clock: FixedClock) -> None:
    ensure_not_past(date(2026, 9, 20), clock)
    ensure_not_past(datetime(2026, 9, 20, 14, 30, tzinfo=TZ), clock)
    with pytest.raises(ToolError):
        ensure_not_past(date(2026, 9, 19), clock)
    with pytest.raises(ToolError):
        ensure_not_past(datetime(2026, 9, 20, 13, 0, tzinfo=TZ), clock)


def test_utc_iso() -> None:
    assert utc_iso(datetime(2026, 9, 20, 14, 3, tzinfo=TZ)) == "2026-09-20T21:03:00Z"


def test_weekend_window() -> None:
    assert weekend_window(date(2026, 9, 20)) == (date(2026, 9, 20), date(2026, 9, 20))  # Sunday
    assert weekend_window(date(2026, 9, 19)) == (date(2026, 9, 19), date(2026, 9, 20))  # Saturday
    assert weekend_window(date(2026, 9, 21)) == (date(2026, 9, 26), date(2026, 9, 27))  # Monday


def test_clock_describe_and_season() -> None:
    clock = FixedClock(datetime(2026, 9, 20, 14, 3), TZ)
    assert clock.describe() == "Sunday 20 September 2026, 14:03 (America/Vancouver), autumn"
    assert season_for(date(2026, 1, 15)) == "winter"
    assert season_for(date(2026, 1, 15), southern=True) == "summer"
