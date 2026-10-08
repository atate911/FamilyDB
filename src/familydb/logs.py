"""What the server logs, who may turn it up, and the problem log an admin reads.

Three controls, all on the Troubleshooting page: how much the server writes (`log_level`), how
much of that is kept in the database to read there (`problem_log_level`), and a different level
for one area (`log_areas`, a line each: `models=DEBUG`), so chasing a Telegram problem needs no
flood from everything else.

Keeping a line must never slow or break the code that logged it, and a log call can come from
inside a database transaction, so the handler only queues the line; one thread of its own writes
the queue, on its own connection."""

from __future__ import annotations

import atexit
import logging
import queue
import re
import sqlite3
import threading
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

from familydb.store import db, problems

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

# The family's words for the parts of the program, and the loggers each is. A name with a dot in
# it is taken as a logger's own name.
AREAS: dict[str, tuple[str, tuple[str, ...]]] = {
    "models": ("Asking the models", ("familydb.agent",)),
    "messages": ("Messages in and out", ("familydb.pipeline", "familydb.delivery")),
    "telegram": ("Telegram", ("familydb.channels", "telegram")),
    "jobs": ("Background jobs", ("familydb.jobs", "apscheduler")),
    "web": ("The web page", ("familydb.web", "waitress")),
    "tools": ("What the models do", ("familydb.tools",)),
    "calendar": ("Calendar and weather", ("familydb.integrations", "familydb.calendar_sync")),
    "suggestions": ("Suggestions", ("familydb.suggest",)),
}
MAX_QUEUED = 500
BATCH = 50


def parse_areas(text: str) -> dict[str, str]:
    """`models=DEBUG` lines as {area: LEVEL}; raises ValueError with a sentence for the page."""
    found: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, level = line.partition("=")
        name, level = name.strip(), level.strip().upper()
        if "." not in name:
            name = name.lower()
        if not name or level not in LEVELS:
            raise ValueError(
                f"each line is an area, an equals sign and a level ({', '.join(LEVELS)}), "
                f"such as models=DEBUG: {line}"
            )
        if name not in AREAS and "." not in name:
            raise ValueError(f"{name} is not an area; they are {', '.join(AREAS)}")
        found[name] = level
    return found


def _loggers(area: str) -> tuple[str, ...]:
    return AREAS[area][1] if area in AREAS else (area,)


def area_of(logger: str) -> str:
    """The family's name for the part of the program a logger belongs to, else the logger's own."""
    for words, names in AREAS.values():
        if any(logger == name or logger.startswith(name + ".") for name in names):
            return words
    return logger


_set_here: set[str] = set()
_areas_lock = threading.Lock()


def apply_areas(text: str) -> None:
    """Set each area's loggers to its level, and put back any an earlier line had set."""
    try:
        wanted = parse_areas(text)
    except ValueError:
        wanted = {}
    with _areas_lock:
        names: dict[str, str] = {}
        for area, level in wanted.items():
            for name in _loggers(area):
                names[name] = level
        for name in _set_here - set(names):
            logging.getLogger(name).setLevel(logging.NOTSET)
        for name, level in names.items():
            logging.getLogger(name).setLevel(getattr(logging, level))
        _set_here.clear()
        _set_here.update(names)


TOKENS = (
    re.compile(r"bot\d{5,}:[A-Za-z0-9_-]{20,}"),
    # A company's key, wherever an error quoted it, or a key in a web address.
    re.compile(r"\b(?:sk|AIza|ya29)[A-Za-z0-9_.-]{20,}"),
    re.compile(r"(?i)\b((?:api_?)?key|token|apikey)=[^&\s'\"]+"),
)


def redact(text: str) -> str:
    text = TOKENS[0].sub("bot<token>", text)
    text = TOKENS[1].sub("<key>", text)
    return TOKENS[2].sub(lambda found: f"{found.group(1)}=<hidden>", text)


class ProblemLog(logging.Handler):
    """Keeps log lines at or above its level in the problem log, written by a thread of its own."""

    def __init__(self, path: str | Path, level: int = logging.WARNING) -> None:
        super().__init__(level)
        self.path = str(path)
        self._queue: queue.Queue[tuple[str, str, str, str | None, datetime]] = queue.Queue(
            MAX_QUEUED
        )
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._write, name="problem-log", daemon=True)
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(("familydb.logs", "familydb.store")) and record.levelno < 40:
            return
        try:
            detail = None
            if record.exc_info and record.exc_info[0] is not None:
                detail = "".join(traceback.format_exception(*record.exc_info))
            self._queue.put_nowait(
                (
                    record.levelname,
                    record.name,
                    redact(record.getMessage()),
                    redact(detail) if detail else None,
                    datetime.fromtimestamp(record.created, UTC),
                )
            )
        except Exception:  # a full queue, a line that will not format: the log is not the news
            pass

    def _write(self) -> None:
        conn: sqlite3.Connection | None = None
        last_trim = 0.0
        while not self._stop.is_set() or not self._queue.empty():
            try:
                batch = [self._queue.get(timeout=0.5)]
            except queue.Empty:
                continue
            while len(batch) < BATCH:
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            try:
                if conn is None:
                    conn = db.connect(self.path)
                with db.transaction(conn):
                    for level, source, message, detail, when in batch:
                        problems.record(
                            conn,
                            level=level,
                            source=source,
                            message=message,
                            detail=detail,
                            now=when,
                        )
                    if time.monotonic() - last_trim > 3600:
                        problems.trim(conn)
                        last_trim = time.monotonic()
            except sqlite3.Error:
                # Not migrated yet, or busy: these lines are lost; the next batch tries again.
                if conn is not None:
                    conn.close()
                conn = None
        if conn is not None:
            conn.close()

    def flush_and_stop(self, wait: float = 2.0) -> None:
        self._stop.set()
        self._thread.join(wait)

    def close(self) -> None:
        self.flush_and_stop(0.5)
        super().close()


_installed: ProblemLog | None = None


def install(path: str | Path, level: str = "WARNING") -> ProblemLog:
    """Start keeping log lines in the database at `path`; once per process and place."""
    global _installed
    if _installed is not None and _installed.path == str(path):
        set_capture(level)
        return _installed
    if _installed is not None:
        logging.getLogger().removeHandler(_installed)
        _installed.flush_and_stop(0.5)
    _installed = ProblemLog(path, getattr(logging, level, logging.WARNING))
    logging.getLogger().addHandler(_installed)
    atexit.register(_installed.flush_and_stop)
    return _installed


def set_capture(level: str) -> None:
    if _installed is not None:
        _installed.setLevel(getattr(logging, level.upper(), logging.WARNING))
