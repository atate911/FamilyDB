"""Application wiring: settings, clock and database connections."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from familydb.clock import Clock, SystemClock
from familydb.config import Settings, load_settings
from familydb.store import db

log = logging.getLogger(__name__)


class App:
    """Everything a command or channel needs, built once per process."""

    def __init__(self, settings: Settings, clock: Clock | None = None) -> None:
        self.settings = settings
        self.clock = clock or SystemClock(settings.tzinfo, southern=settings.southern_hemisphere)

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
