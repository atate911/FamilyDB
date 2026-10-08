from __future__ import annotations

import logging
import re
import sqlite3
import threading
import traceback
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

from familydb import logs
from familydb.availability import calendar_available, weather_available
from familydb.clock import Clock, SystemClock
from familydb.config import Settings, load_settings
from familydb.store import db
from familydb.tools import ToolRegistry, build_registry
from familydb.voice import Holds

log = logging.getLogger(__name__)
MODELS_OFF = "off"


class App:
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
        self._base = settings
        self._put_companies_in_force()
        self._overrides_stamp: str | None = None
        self._models_stamp: str | None = None
        self._reload = threading.Lock()
        self._calendar = calendar
        self._weather = weather
        self._geocoder = geocoder
        # Anything handed in (a test's fake, a command's client) is not ours to replace when
        # settings move; anything built lazily from them is.
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
        # Channels register how to deliver a text to one of their chats. The web chat reads the
        # message log, so storing a reply is delivering it; kept here so a process not serving the
        # page can retry a web message or send a web digest.
        self.senders: dict[str, Callable[[str, str], None]] = {"web": lambda _chat, _text: None}
        # A channel that can show buttons registers how; elsewhere a message's words go alone
        # (buttons.py).
        self.button_senders: dict[str, Callable[[str, str, list[dict[str, str]]], None]] = {}
        self.channel_states: dict[str, str] = {}
        self.channel_facts: dict[str, dict[str, Any]] = {}
        self.discover_cache: dict[str, Any] = {}
        self.held = Holds()
        # Told once one of her messages is delivered on a channel, to reach a device the channel
        # cannot (familydb/push.py for the page): never changes whether it counts as delivered.
        from familydb.push import Pusher

        self.notifiers: dict[str, Callable[[sqlite3.Connection, Any], None]] = {"web": Pusher(self)}
        self.clock = clock or SystemClock(settings.tzinfo, southern=settings.southern_hemisphere)
        self._registry: ToolRegistry | None = None

    @property
    def registry(self) -> ToolRegistry:
        if self._registry is None:
            self._registry = build_registry()
        return self._registry

    @property
    def calendar(self) -> Any:
        if self._calendar is None and calendar_available(self.settings):
            from familydb.integrations.google_calendar import GoogleCalendar

            self._calendar = GoogleCalendar(self.settings)
            self._calendar.report = self._calendar_said
        return self._calendar

    def _calendar_said(self, trouble: str | None) -> None:
        """Google would not let the bot in (what it said), or answered again (None): noted for an
        admin or forgotten (alerts.py).
        """
        from familydb import alerts

        try:
            with closing(self.connect()) as conn:
                if trouble is None:
                    alerts.working(conn, "calendar")
                else:
                    alerts.note(conn, "calendar", "", trouble, self.clock.now())
        except (sqlite3.Error, OSError) as exc:
            log.warning("could not note what Google Calendar said: %s", exc)

    @property
    def weather(self) -> Any:
        if self._weather is None and weather_available(self.settings):
            from familydb.integrations.open_meteo import OpenMeteo

            self._weather = OpenMeteo(self.settings)
        return self._weather

    @property
    def geocoder(self) -> Any:
        if self._geocoder is None:
            from familydb.integrations.geocode import Geocoder

            self._geocoder = Geocoder(self.settings)
        return self._geocoder

    @property
    def base_settings(self) -> Settings:
        """What the environment and .env said, before anything stored on top: the settings page says
        what an emptied box falls back to.
        """
        return self._base

    def provider(self, surface: str = "chat", api: Any = None) -> Any:
        """The model provider, built fresh so a settings change takes effect."""
        from familydb.agent import providers

        return providers.for_surface(self.settings, surface, api=api)

    def can_ask(self, surface: str = "chat", api: Any = None) -> bool:
        """Whether any model can be asked here. The worker surface is the lookups, which search
        the web, so it needs a company that can."""
        from familydb.agent import providers

        return providers.ready(self.settings, surface, api=api, web=surface == "worker")  # type: ignore[arg-type]

    def fallback(self, surface: str, primary: str) -> Any:
        from familydb.agent import providers

        return providers.fallback_for(
            self.settings,
            surface,  # type: ignore[arg-type]
            primary,
            web=surface == "worker",
        )

    def refresh(self, conn: sqlite3.Connection | None = None) -> bool:
        """Pick up settings changed from the page. True when something moved.

        One query for the newest change, a rebuild only when it has moved. Every entry point
        calls it so a page change reaches the next message, job and page view; pass a connection
        you already hold.
        """
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
                return self._reload_settings(conn)
            finally:
                self._keep_up_with_models(conn)

    def _put_companies_in_force(self) -> None:
        """The companies the settings define, for the places that name one without settings to
        hand (a notice's wording, a price)."""
        from familydb.agent.providers import companies

        companies.use(self.settings.companies)

    def _reload_settings(self, conn: sqlite3.Connection) -> bool:
        from familydb.config import apply_overrides
        from familydb.store import settings as settings_store

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
            return False
        self.settings = fresh
        self._put_companies_in_force()
        self._forget_built()
        log.info("settings reloaded (%d stored)", len(values))
        return True

    def _keep_up_with_models(self, conn: sqlite3.Connection) -> None:
        """Put in force what the daily check of models and prices found since this process last
        looked (model_watch.py), or the built-in prices while it is off. One small query
        otherwise.
        """
        from familydb import model_watch
        from familydb.agent.providers import prices
        from familydb.store import model_watch as watch_store

        if not self.settings.model_watch:
            if self._models_stamp != MODELS_OFF:
                prices.use({}, {})
                self._models_stamp = MODELS_OFF
            return
        from familydb.store import judgements as judgement_store

        try:
            stamp = f"{watch_store.stamp(conn)}|{judgement_store.last_answered(conn)}"
            if stamp == self._models_stamp:
                return
            model_watch.load(conn, today=self.clock.today())
        except sqlite3.Error as exc:
            log.warning("could not load the models and prices last found: %s", exc)
            return
        self._models_stamp = stamp

    def forget_calendar(self) -> None:
        if "calendar" not in self._given:
            self._calendar = None

    def _forget_built(self) -> None:
        """Drop what was built from the changed settings so it is built again (coordinates, units
        and the timezone are baked in). Anything handed to the constructor stays.
        """
        self.discover_cache.clear()
        for name in ("calendar", "weather", "geocoder"):
            if name not in self._given:
                setattr(self, f"_{name}", None)
        if "clock" not in self._given and (
            self.clock.southern != self.settings.southern_hemisphere
            or self.clock.tz != self.settings.tzinfo
        ):
            self.clock = SystemClock(
                self.settings.tzinfo, southern=self.settings.southern_hemisphere
            )
        wanted = getattr(logging, self.settings.log_level, logging.INFO)
        moved = logging.getLogger().level != wanted
        if moved:
            set_log_level(wanted)
            log.info("log level is now %s", self.settings.log_level)
        # Areas go after the whole server's level, which would otherwise put them back.
        logs.apply_areas(self.settings.log_areas)
        logs.set_capture(self.settings.problem_log_level)

    def connect(self) -> sqlite3.Connection:
        """A fresh connection: SQLite connections are per thread, do not share them."""
        return db.connect(self.settings.familydb_path)

    def migrate(self) -> list[int]:
        with closing(self.connect()) as conn:
            applied = db.migrate(conn)
        if applied:
            log.info("applied migrations %s", applied)
        return applied


# httpx logs every request at INFO with its full URL, which holds the Telegram bot token on every
# poll. Vendor SDKs send keys in headers, so only the transport needs quietening; `RedactSecrets`
# takes the token out of whatever gets through.
QUIET_LOGGERS = ("httpx", "httpcore")


def set_log_level(wanted: int) -> None:
    """Move the root logger and the transport loggers with it, so turning DEBUG back down leaves no
    transport logging every request.
    """
    logging.getLogger().setLevel(wanted)
    # LOG_LEVEL=DEBUG is someone deliberately reading the traffic; every other level keeps it out.
    transport = logging.DEBUG if wanted <= logging.DEBUG else logging.WARNING
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(transport)


# A bot token travels in the request URL, which the transport logs at DEBUG, and the page can turn
# DEBUG on: so the token is taken out of every line, or anyone who can read the journal could run
# the family's bot.
TELEGRAM_TOKEN = re.compile(r"bot\d{5,}:[A-Za-z0-9_-]{20,}")


class RedactSecrets(logging.Filter):
    """Replaces a bot token in a log line, and in the traceback under it, with a marker; attached
    to handlers so it sees every record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        text = record.getMessage()
        if TELEGRAM_TOKEN.search(text):
            record.msg = TELEGRAM_TOKEN.sub("bot<token>", text)
            record.args = None
        # An exception's text (an httpx error quotes its URL) is formatted here, scrubbed, and left
        # as exc_text with exc_info cleared, so no formatter or handler formats the raw one again.
        if record.exc_info and record.exc_info[0] is not None:
            record.exc_text = logs.redact(
                "".join(traceback.format_exception(*record.exc_info)).rstrip("\n")
            )
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = logs.redact(record.exc_text)
        if record.stack_info:
            record.stack_info = logs.redact(record.stack_info)
        return True


def configure_logging(level: str) -> None:
    wanted = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=wanted, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for handler in logging.getLogger().handlers:
        if not any(isinstance(one, RedactSecrets) for one in handler.filters):
            handler.addFilter(RedactSecrets())
    set_log_level(wanted)


def build_app(env_file: str | Path | None = ".env", **overrides: Any) -> App:
    settings = load_settings(env_file, **overrides)
    configure_logging(settings.log_level)
    logs.install(settings.familydb_path, settings.problem_log_level)
    logs.apply_areas(settings.log_areas)
    return App(settings)
