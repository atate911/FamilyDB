"""Keyless geocoding: Nominatim for addresses, Open-Meteo's geocoder for town-level names."""

from __future__ import annotations

import json
import logging
import math
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from familydb.base.config import Settings

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
# The parts of a Nominatim address a family would say: neighbourhood, then town.
AREA_KEYS = ("neighbourhood", "suburb", "quarter", "city_district")
TOWN_KEYS = ("city", "town", "village", "hamlet")
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "familydb/0.1 (self-hosted family planning bot)"


def user_agent(contact: str) -> str:
    """Nominatim's policy wants the application and, when given, a contact (GEOCODER_CONTACT)."""
    contact = " ".join(contact.split())
    return f"{USER_AGENT[:-1]}; {contact})" if contact else USER_AGENT


MIN_INTERVAL = 1.0  # Nominatim's policy: at most one request per second
EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float
    label: str
    source: str  # "nominatim" or "open-meteo"


def is_short_name(query: str) -> bool:
    """A town or landmark name rather than a street address."""
    return not re.search(r"\d", query) and len(query.split()) <= 4


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def estimate_travel(
    settings: Settings, lat: float, lon: float, *, start: tuple[float, float] | None = None
) -> tuple[int, float] | None:
    """(minutes, km) by road, estimated from home or `start`; None without a starting point."""
    if start is None:
        if settings.home_lat is None or settings.home_lon is None:
            return None
        start = (settings.home_lat, settings.home_lon)
    km = haversine_km(start[0], start[1], lat, lon) * settings.road_factor
    minutes = round(km / max(settings.travel_speed_kmh, 1.0) * 60)
    return minutes, round(km, 1)


class Geocoder:
    """`geocode` and `reverse` over Nominatim, Open-Meteo for short names. Never raises."""

    def __init__(
        self,
        settings: Settings,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_call: float | None = None
        self._cache: dict[str, GeoPoint | None] = {}
        self._names: dict[tuple[float, float], str | None] = {}
        self._agent = user_agent(getattr(settings, "geocoder_contact", "") or "")

    @staticmethod
    def _fetch(url: str, headers: dict[str, str]) -> Any:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def _throttle(self) -> None:
        if self._last_call is not None:
            wait = MIN_INTERVAL - (self._monotonic() - self._last_call)
            if wait > 0:
                self._sleep(wait)
        self._last_call = self._monotonic()

    def _nominatim(self, query: str) -> GeoPoint | None:
        params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 1})
        self._throttle()
        try:
            rows = self._fetch(
                f"{NOMINATIM_URL}?{params}", {"User-Agent": self._agent, "Accept-Language": "en"}
            )
        except Exception as exc:
            log.warning("nominatim lookup failed for %r: %s", query, exc)
            return None
        if not rows:
            return None
        row = rows[0]
        try:
            label = str(row.get("display_name") or query)
            return GeoPoint(float(row["lat"]), float(row["lon"]), label, "nominatim")
        except (KeyError, TypeError, ValueError):
            return None

    def _open_meteo(self, query: str) -> GeoPoint | None:
        params = urllib.parse.urlencode(
            {"name": query, "count": 1, "language": "en", "format": "json"}
        )
        try:
            payload = self._fetch(f"{OPEN_METEO_GEOCODE_URL}?{params}", {"User-Agent": USER_AGENT})
        except Exception as exc:
            log.warning("open-meteo geocoding failed for %r: %s", query, exc)
            return None
        results = payload.get("results") or [] if isinstance(payload, dict) else []
        if not results:
            return None
        row = results[0]
        try:
            parts = [row.get("name"), row.get("admin1"), row.get("country")]
            label = ", ".join(str(p) for p in parts if p)
            return GeoPoint(float(row["latitude"]), float(row["longitude"]), label, "open-meteo")
        except (KeyError, TypeError, ValueError):
            return None

    def reverse(self, lat: float, lon: float) -> str | None:
        """What a family would call a point ("Pearl District, Portland"), or None. Cached to about
        a hundred metres."""
        key = (round(lat, 3), round(lon, 3))
        if key in self._names:
            return self._names[key]
        params = urllib.parse.urlencode(
            {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "format": "json", "zoom": 16}
        )
        self._throttle()
        try:
            row = self._fetch(
                f"{NOMINATIM_REVERSE_URL}?{params}",
                {"User-Agent": self._agent, "Accept-Language": "en"},
            )
        except Exception as exc:
            log.warning("nominatim reverse lookup failed: %s", exc)
            return None  # not cached: the next share may reach it
        address = row.get("address") if isinstance(row, dict) else None
        name = _area_name(address) if isinstance(address, dict) else None
        self._names[key] = name
        return name

    def forget(self, query: str) -> None:
        """Drop what was remembered of a place, so asking again asks the map again."""
        self._cache.pop(" ".join(query.split()).casefold(), None)

    def geocode(self, query: str) -> GeoPoint | None:
        key = " ".join(query.split()).casefold()
        if not key:
            return None
        if key in self._cache:
            return self._cache[key]
        point = self._nominatim(query)
        if point is None and is_short_name(query):
            point = self._open_meteo(query)
        self._cache[key] = point
        return point


def _area_name(address: dict[str, Any]) -> str | None:
    area = next((address[k] for k in AREA_KEYS if address.get(k)), None)
    town = next((address[k] for k in TOWN_KEYS if address.get(k)), None)
    parts = [str(p) for p in (area, town) if p]
    return ", ".join(dict.fromkeys(parts)) or None
