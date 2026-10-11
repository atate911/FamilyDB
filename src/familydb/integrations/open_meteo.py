"""Daily forecasts from Open-Meteo, with sunrise and sunset: free, no key, 16 days ahead. For a
day or two it also brings each hour, so "now", "this afternoon" or a plan at ten is judged by its
own hours rather than the day's worst (`DayForecast.between`), in the same request."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any, Protocol

from familydb.base.config import Settings
from familydb.base.errors import ToolError

log = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_FIELDS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
    "sunrise",
    "sunset",
)
HOURLY_FIELDS = ("weather_code", "temperature_2m", "precipitation_probability")
# Hour by hour when the request covers at most this many days: now, today, tomorrow, a weekend.
HOURLY_DAYS = 2
CACHE_SECONDS = 3600
# Open-Meteo serves 16 forecast days including today, so the last one is today + 15.
MAX_DAYS_AHEAD = 15

WEATHER_CODES: dict[int, str] = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}


@dataclass(frozen=True)
class Hour:
    minute: int  # when the hour starts, in minutes after midnight, in the family's timezone
    code: int | None
    rain_chance: int | None  # percent
    temp: float | None


@dataclass(frozen=True)
class DayForecast:
    date: date
    code: int | None
    summary: str
    high: float | None
    low: float | None
    rain_chance: int | None  # percent
    precipitation: float | None  # mm or inches, per settings
    sunrise: int | None = None  # minutes after midnight, in the family's timezone
    sunset: int | None = None
    hours: tuple[Hour, ...] = ()
    # On a forecast for part of the day (`between`): its first and last minute.
    span: tuple[int, int] | None = None

    @property
    def daylight(self) -> tuple[int, int] | None:
        """Sunrise to sunset in minutes after midnight, when both are given."""
        if self.sunrise is None or self.sunset is None or self.sunrise >= self.sunset:
            return None
        return self.sunrise, self.sunset

    def between(self, start: int, end: int) -> DayForecast:
        """The day as its hours from `start` to `end` (minutes after midnight) have it: the worst
        hour's weather (the highest code is the wettest), the highest chance of rain, the warmest
        and the coldest. The whole day when no hours came, or none fall in the stretch."""
        inside = [hour for hour in self.hours if hour.minute < end and hour.minute + 60 > start]
        if not inside:
            return self
        codes = [hour.code for hour in inside if hour.code is not None]
        chances = [hour.rain_chance for hour in inside if hour.rain_chance is not None]
        temps = [hour.temp for hour in inside if hour.temp is not None]
        code = max(codes) if codes else self.code
        return replace(
            self,
            code=code,
            summary=summarize_code(code),
            rain_chance=max(chances) if chances else self.rain_chance,
            high=max(temps) if temps else self.high,
            low=min(temps) if temps else self.low,
            span=(start, end),
        )

    def to_public(self, units: str) -> dict[str, Any]:
        temp = "F" if units == "imperial" else "C"
        return {
            "date": self.date.isoformat(),
            "weekday": self.date.strftime("%A"),
            "summary": self.summary,
            f"high_{temp.lower()}": self.high,
            f"low_{temp.lower()}": self.low,
            "rain_chance_pct": self.rain_chance,
            "precipitation_" + ("in" if units == "imperial" else "mm"): self.precipitation,
        }


class ForecastAPI(Protocol):
    def daily(self, start: date, end: date) -> list[DayForecast]: ...


def summarize_code(code: int | None) -> str:
    if code is None:
        return "unknown"
    return WEATHER_CODES.get(int(code), f"weather code {code}")


def local_minutes(value: Any, day: date) -> int | None:
    """A local "YYYY-MM-DDTHH:MM" in minutes after midnight of `day`; None if missing, unreadable
    or on another day."""
    if value is None:
        return None
    try:
        moment = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return moment.hour * 60 + moment.minute if moment.date() == day else None


def parse_daily(payload: dict[str, Any]) -> list[DayForecast]:
    """One record per day from an Open-Meteo response's `daily` block."""
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []

    def column(name: str) -> list[Any]:
        values = daily.get(name) or []
        return list(values) + [None] * (len(dates) - len(values))

    codes = column("weather_code")
    highs = column("temperature_2m_max")
    lows = column("temperature_2m_min")
    chances = column("precipitation_probability_max")
    sums = column("precipitation_sum")
    sunrises = column("sunrise")
    sunsets = column("sunset")
    hours = parse_hourly(payload)
    out: list[DayForecast] = []
    for i, day in enumerate(dates):
        code = codes[i]
        when = date.fromisoformat(day)
        out.append(
            DayForecast(
                date=when,
                code=None if code is None else int(code),
                summary=summarize_code(code),
                high=None if highs[i] is None else float(highs[i]),
                low=None if lows[i] is None else float(lows[i]),
                rain_chance=None if chances[i] is None else int(chances[i]),
                precipitation=None if sums[i] is None else float(sums[i]),
                sunrise=local_minutes(sunrises[i], when),
                sunset=local_minutes(sunsets[i], when),
                hours=tuple(hours.get(when, ())),
            )
        )
    return out


def parse_hourly(payload: dict[str, Any]) -> dict[date, list[Hour]]:
    """Each day's hours from an Open-Meteo response's `hourly` block, when it has one."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []

    def column(name: str) -> list[Any]:
        values = hourly.get(name) or []
        return list(values) + [None] * (len(times) - len(values))

    codes = column("weather_code")
    temps = column("temperature_2m")
    chances = column("precipitation_probability")
    days: dict[date, list[Hour]] = {}
    for i, stamp in enumerate(times):
        try:
            moment = datetime.fromisoformat(str(stamp))
        except ValueError:
            continue
        days.setdefault(moment.date(), []).append(
            Hour(
                minute=moment.hour * 60 + moment.minute,
                code=None if codes[i] is None else int(codes[i]),
                rain_chance=None if chances[i] is None else int(chances[i]),
                temp=None if temps[i] is None else float(temps[i]),
            )
        )
    return days


class OpenMeteo:
    """Forecasts for the home coordinates, cached in memory."""

    def __init__(self, settings: Settings) -> None:
        if settings.home_lat is None or settings.home_lon is None:
            raise ToolError("HOME_LAT and HOME_LON are not set")
        self.lat = settings.home_lat
        self.lon = settings.home_lon
        self.tz = settings.tz
        self.units = settings.weather_units
        self._cache: dict[tuple[str, str], tuple[float, list[DayForecast]]] = {}

    def _url(self, start: date, end: date) -> str:
        params = {
            "latitude": f"{self.lat:.4f}",
            "longitude": f"{self.lon:.4f}",
            "daily": ",".join(DAILY_FIELDS),
            "timezone": self.tz,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        if (end - start).days < HOURLY_DAYS:
            params["hourly"] = ",".join(HOURLY_FIELDS)
        if self.units == "imperial":
            params["temperature_unit"] = "fahrenheit"
            params["precipitation_unit"] = "inch"
        return f"{BASE_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def _fetch(url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": "familydb/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ToolError(f"weather service returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise ToolError(f"weather service unavailable: {exc}") from exc

    def daily(self, start: date, end: date) -> list[DayForecast]:
        key = (start.isoformat(), end.isoformat())
        cached = self._cache.get(key)
        now = time.monotonic()
        if cached and now - cached[0] < CACHE_SECONDS:
            return cached[1]
        days = parse_daily(self._fetch(self._url(start, end)))
        self._cache[key] = (now, days)
        return days
