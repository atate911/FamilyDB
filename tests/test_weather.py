import json
from datetime import date

from familydb.integrations.open_meteo import (
    DayForecast,
    OpenMeteo,
    local_minutes,
    parse_daily,
    summarize_code,
)
from familydb.tools import ToolContext
from tests import fakes

SAMPLE = {
    "daily": {
        "time": ["2026-09-26", "2026-09-27"],
        "weather_code": [1, 61],
        "temperature_2m_max": [19.4, 14.0],
        "temperature_2m_min": [9.1, 8.2],
        "precipitation_probability_max": [5, 80],
        "precipitation_sum": [0.0, 6.5],
        "sunrise": ["2026-09-26T07:05", "2026-09-27T07:06"],
        "sunset": ["2026-09-26T19:01", "2026-09-27T18:59"],
    }
}


def test_parse_daily_and_codes() -> None:
    days = parse_daily(SAMPLE)
    assert [d.summary for d in days] == ["mainly clear", "light rain"]
    assert days[0].high == 19.4 and days[1].rain_chance == 80
    assert days[0].daylight == (7 * 60 + 5, 19 * 60 + 1)
    assert (days[1].sunrise, days[1].sunset) == (7 * 60 + 6, 18 * 60 + 59)
    assert summarize_code(None) == "unknown"
    assert summarize_code(42) == "weather code 42"
    short = parse_daily({"daily": {"time": ["2026-09-26"], "weather_code": []}})
    assert short[0].code is None and short[0].high is None and short[0].daylight is None


def test_sunrise_and_sunset_are_read_only_for_their_own_day() -> None:
    day = date(2026, 9, 26)
    assert local_minutes("2026-09-26T19:01", day) == 19 * 60 + 1
    assert local_minutes("2026-09-27T00:12", day) is None  # another day: not this one's sunset
    assert local_minutes("sunset", day) is None and local_minutes(None, day) is None
    # A day with no sunset before its sunrise, near a pole, has no daylight to go by.
    assert DayForecast(day, None, "clear", None, None, None, None, 600, 600).daylight is None


def test_open_meteo_url_and_cache(settings, monkeypatch) -> None:
    configured = settings.model_copy(
        update={"home_lat": 45.63, "home_lon": -122.67, "weather_units": "imperial"}
    )
    client = OpenMeteo(configured)
    url = client._url(date(2026, 9, 26), date(2026, 9, 27))
    assert "latitude=45.6300" in url and "temperature_unit=fahrenheit" in url
    assert "timezone=America%2FVancouver" in url  # so sunrise and sunset come in local time
    assert "sunrise%2Csunset" in url
    calls: list[str] = []

    def fake_fetch(url: str):
        calls.append(url)
        return SAMPLE

    monkeypatch.setattr(OpenMeteo, "_fetch", staticmethod(fake_fetch))
    first = client.daily(date(2026, 9, 26), date(2026, 9, 27))
    second = client.daily(date(2026, 9, 26), date(2026, 9, 27))
    assert first == second and len(calls) == 1  # served from cache the second time


def _forecast_ctx(conn, settings, clock, family, days):
    configured = settings.model_copy(update={"home_lat": 45.63, "home_lon": -122.67})
    return ToolContext(
        conn=conn,
        settings=configured,
        clock=clock,
        member=family["sam"],
        weather=fakes.FakeForecast(days),
    )


def test_get_forecast_tool(registry, conn, settings, clock, family) -> None:
    days = [
        DayForecast(date(2026, 9, 20), 3, "overcast", 17.0, 10.0, 20, 0.2),
        DayForecast(date(2026, 9, 26), 1, "mainly clear", 19.4, 9.1, 5, 0.0),
        DayForecast(date(2026, 9, 27), 61, "light rain", 14.0, 8.2, 80, 6.5),
    ]
    ctx = _forecast_ctx(conn, settings, clock, family, days)
    result = registry.dispatch("get_forecast", {"start": "2026-09-26", "end": "2026-09-27"}, ctx)
    data = json.loads(result.content)
    assert not result.is_error, data
    assert data["units"] == "metric"
    assert [d["summary"] for d in data["days"]] == ["mainly clear", "light rain"]
    assert data["days"][1] == {
        "date": "2026-09-27",
        "weekday": "Sunday",
        "summary": "light rain",
        "high_c": 14.0,
        "low_c": 8.2,
        "rain_chance_pct": 80,
        "precipitation_mm": 6.5,
    }
    # ranges are clamped to today..today+16
    result = registry.dispatch("get_forecast", {"start": "2026-09-01", "end": "2026-12-01"}, ctx)
    assert ctx.weather.calls[-1] == (date(2026, 9, 20), date(2026, 10, 5))
    result = registry.dispatch("get_forecast", {"start": "2026-09-01", "end": "2026-09-10"}, ctx)
    data = json.loads(result.content)
    assert result.is_error and "covers" in data["error"]


def test_get_forecast_unavailable_without_coordinates(
    registry, conn, settings, clock, family
) -> None:
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    result = registry.dispatch("get_forecast", {"start": "2026-09-26", "end": "2026-09-27"}, ctx)
    data = json.loads(result.content)
    assert not result.is_error and data["available"] is False
