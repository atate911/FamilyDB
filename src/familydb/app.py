"""Application wiring: settings, clock and database connections."""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

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
        self._base = settings  # what the environment said, before anything stored on top
        self._overrides_stamp: str | None = None
        self._reload = threading.Lock()
        self._calendar = calendar
        self._weather = weather
        self._geocoder = geocoder
        # Anything handed in (a test's fake, a command's client) is not ours to replace when the
        # settings move; anything we built lazily from them is.
        self._given = {
            name
            for name, value in (
                ("calendar", calendar),
                ("weather", weather),
                ("geocoder", geocoder),
                ("clock", clock),
            )
            if value is not None
        }
        # Channels register how to deliver a text to one of their chats, keyed by channel name.
        # The web page's chat reads the message log, so storing a reply is delivering it. That
        # sender is here rather than on the page so a web message can be retried, and a web
        # digest sent, by a process that is not serving the page.
        self.senders: dict[str, Callable[[str, str], None]] = {"web": lambda _chat, _text: None}
        # What each long-running channel last said about itself, for the status page.
        self.channel_states: dict[str, str] = {}
        # Web discovery results per window, kept for a while (see suggest/discover.py).
        self.discover_cache: dict[str, Any] = {}
        self.clock = clock or SystemClock(settings.tzinfo, southern=settings.southern_hemisphere)
        self._registry: ToolRegistry | None = None

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
    def base_settings(self) -> Settings:
        """What the environment and the .env file said, before anything stored on top.

        The settings page needs this to say what a box falls back to when it is emptied.
        """
        return self._base

    def provider(self, surface: str = "chat", api: Any = None) -> Any:
        """The model provider for this surface, built fresh so a settings change takes effect."""
        from familydb.agent import providers

        return providers.for_surface(self.settings, surface, api=api)

    def fallback(self, surface: str, primary: str) -> Any:
        """Somewhere else to ask when the chosen provider cannot take a message right now."""
        from familydb.agent import providers

        return providers.fallback_for(self.settings, surface, primary)

    def refresh(self, conn: sqlite3.Connection | None = None) -> bool:
        """Pick up settings changed from the page. True when something actually moved.

        Cheap: one query for the newest change, and a rebuild only when that has moved on. Every
        entry point calls this, so a change made on the page reaches the next message, the next
        job and the next page view without a restart. Callers already holding a connection
        should pass it rather than paying for a second one.
        """
        from familydb.config import apply_overrides
        from familydb.store import settings as settings_store

        if conn is None:
            try:
                own = self.connect()
            except (sqlite3.Error, OSError) as exc:
                log.warning("could not open the database to read the settings: %s", exc)
                return False
            with closing(own):
                return self.refresh(own)
        with self._reload:
            try:
                stamp = settings_store.stamp(conn)
                if stamp == self._overrides_stamp:
                    return False
                values = settings_store.overrides(conn)
            except sqlite3.Error as exc:
                log.warning("could not read the stored settings: %s", exc)
                return False
            try:
                fresh = apply_overrides(self._base, values)
            except Exception as exc:
                log.error(
                    "stored settings are not usable, keeping the ones in the environment: %s", exc
                )
                self._overrides_stamp = stamp
                return False
            self._overrides_stamp = stamp
            if fresh == self.settings:
                return False  # a log line moved, the values did not
            self.settings = fresh
            self._forget_built()
            log.info("settings reloaded (%d stored)", len(values))
            return True

    def _forget_built(self) -> None:
        """Drop what was built from the settings that just changed, so it is built again.

        Coordinates, units and the timezone are baked into these at construction. Anything
        handed to the constructor stays: it belongs to whoever passed it.
        """
        # A find depends on home and the models as well as the window, and both can have moved.
        self.discover_cache.clear()
        for name in ("calendar", "weather", "geocoder"):
            if name not in self._given:
                setattr(self, f"_{name}", None)
        if "clock" not in self._given and self.clock.southern != self.settings.southern_hemisphere:
            self.clock = SystemClock(
                self.settings.tzinfo, southern=self.settings.southern_hemisphere
            )
        # Turning the log up is most of the reason anyone opens the settings page in a hurry.
        wanted = getattr(logging, self.settings.log_level, logging.INFO)
        if logging.getLogger().level != wanted:
            set_log_level(wanted)
            log.info("log level is now %s", self.settings.log_level)

    def connect(self) -> sqlite3.Connection:
        """A fresh connection. SQLite connections are per thread; do not share them."""
        return db.connect(self.settings.familydb_path)

    def migrate(self) -> list[int]:
        with closing(self.connect()) as conn:
            applied = db.migrate(conn)
        if applied:
            log.info("applied migrations %s", applied)
        return applied


# httpx logs every request at INFO with its full URL, and a Telegram URL carries the bot token
# in its path, so at INFO these would put the token in the journal on every poll. The vendor SDKs
# send their keys in headers, which are never logged, so only the transport needs quietening.
QUIET_LOGGERS = ("httpx", "httpcore")


def set_log_level(wanted: int) -> None:
    """Move the root logger, and the transport loggers with it.

    Called again whenever the level changes on the settings page, so the two never drift: a
    family that turns DEBUG on to read the traffic, and then turns it back down, must not be
    left with the transport still logging the Telegram token.
    """
    logging.getLogger().setLevel(wanted)
    # LOG_LEVEL=DEBUG is someone deliberately looking at the traffic, and is told in the runbook
    # that the token comes with it. Every other level keeps it out.
    transport = logging.DEBUG if wanted <= logging.DEBUG else logging.WARNING
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(transport)


# A Telegram bot token travels in the request URL, which the HTTP transport logs at DEBUG. The
# settings page can turn DEBUG on, so the token is taken out of every line instead of relying on
# the level: with it, anyone who can read the journal could run the family's bot.
TELEGRAM_TOKEN = re.compile(r"bot\d{5,}:[A-Za-z0-9_-]{20,}")


class RedactSecrets(logging.Filter):
    """Replaces a bot token in a log line with a marker. Attached to handlers, so it sees every
    record whichever logger it came from."""

    def filter(self, record: logging.LogRecord) -> bool:
        text = record.getMessage()
        if TELEGRAM_TOKEN.search(text):
            record.msg = TELEGRAM_TOKEN.sub("bot<token>", text)
            record.args = None
        return True


def configure_logging(level: str) -> None:
    wanted = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=wanted, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for handler in logging.getLogger().handlers:
        if not any(isinstance(one, RedactSecrets) for one in handler.filters):
            handler.addFilter(RedactSecrets())
    # basicConfig does nothing once a handler exists, and this is called again after a reload.
    set_log_level(wanted)


def build_app(env_file: str | Path | None = ".env", **overrides: Any) -> App:
    settings = load_settings(env_file, **overrides)
    configure_logging(settings.log_level)
    return App(settings)
