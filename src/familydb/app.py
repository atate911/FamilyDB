"""Application wiring: settings, clock and database connections."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

import anthropic

from familydb.agent.client import make_client
from familydb.availability import calendar_available, weather_available
from familydb.clock import Clock, SystemClock
from familydb.config import Settings, load_settings
from familydb.store import db
from familydb.tools import ToolRegistry, build_registry

log = logging.getLogger(__name__)


class App:
    """Everything a command or channel needs, built once per process."""

    def __init__(
        self,
        settings: Settings,
        clock: Clock | None = None,
        *,
        calendar: Any = None,
        weather: Any = None,
        geocoder: Any = None,
    ) -> None:
        self.settings = settings
        self._calendar = calendar
        self._weather = weather
        self._geocoder = geocoder
        # Channels register how to deliver a text to one of their chats, keyed by channel name.
        self.senders: dict[str, Callable[[str, str], None]] = {}
        # Web discovery results per window, kept for a while (see suggest/discover.py).
        self.discover_cache: dict[str, Any] = {}
        self.clock = clock or SystemClock(settings.tzinfo, southern=settings.southern_hemisphere)
        self._registry: ToolRegistry | None = None
        self._client: anthropic.Anthropic | None = None

    @property
    def registry(self) -> ToolRegistry:
        if self._registry is None:
            self._registry = build_registry()
        return self._registry

    @property
    def calendar(self) -> Any:
        """The Google Calendar client when configured, else None (tools then say so)."""
        if self._calendar is None and calendar_available(self.settings):
            from familydb.integrations.google_calendar import GoogleCalendar

            self._calendar = GoogleCalendar(self.settings)
        return self._calendar

    @property
    def weather(self) -> Any:
        """The Open-Meteo client when coordinates are set, else None."""
        if self._weather is None and weather_available(self.settings):
            from familydb.integrations.open_meteo import OpenMeteo

            self._weather = OpenMeteo(self.settings)
        return self._weather

    @property
    def geocoder(self) -> Any:
        """The keyless geocoder; always constructible."""
        if self._geocoder is None:
            from familydb.integrations.geocode import Geocoder

            self._geocoder = Geocoder(self.settings)
        return self._geocoder

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = make_client(self.settings)
        return self._client

    def connect(self) -> sqlite3.Connection:
        """A fresh connection. SQLite connections are per thread; do not share them."""
        return db.connect(self.settings.familydb_path)

    def migrate(self) -> list[int]:
        with closing(self.connect()) as conn:
            applied = db.migrate(conn)
        if applied:
            log.info("applied migrations %s", applied)
        return applied


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def build_app(env_file: str | Path | None = ".env", **overrides: Any) -> App:
    settings = load_settings(env_file, **overrides)
    configure_logging(settings.log_level)
    return App(settings)
