"""Daily forecasts from Open-Meteo: free, no key, sixteen days ahead."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from familydb.config import Settings
from familydb.errors import ToolError

log = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_FIELDS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
)
CACHE_SECONDS = 3600
MAX_DAYS_AHEAD = 16

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
class DayForecast:
    date: date
    code: int | None
    summary: str
    high: float | None
    low: float | None
    rain_chance: int | None  # percent
    precipitation: float | None  # mm or inches, per settings

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


def parse_daily(payload: dict[str, Any]) -> list[DayForecast]:
    """The `daily` block of an Open-Meteo response to one record per day."""
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
    out: list[DayForecast] = []
    for i, day in enumerate(dates):
        code = codes[i]
        out.append(
            DayForecast(
                date=date.fromisoformat(day),
                code=None if code is None else int(code),
                summary=summarize_code(code),
                high=None if highs[i] is None else float(highs[i]),
                low=None if lows[i] is None else float(lows[i]),
                rain_chance=None if chances[i] is None else int(chances[i]),
                precipitation=None if sums[i] is None else float(sums[i]),
            )
        )
    return out


class OpenMeteo:
    """ForecastAPI for the home coordinates, with a short in-memory cache."""

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
