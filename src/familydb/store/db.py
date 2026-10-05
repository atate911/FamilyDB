"""SQLite connection handling, transactions, JSON helpers and migrations."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any

MIGRATION_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a connection with the app's pragmas; one connection per thread."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE ... COMMIT, rolling back on any exception. Not re-entrant."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def to_json(value: Any) -> str:
    """The one way JSON is written: sorted keys, compact (deterministic, for the cache)."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def from_json(text: str | None, default: Any = None) -> Any:
    if text is None:
        return default
    return json.loads(text)


def utcnow_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_migrations() -> list[tuple[int, str, str]]:
    """(version, file name, sql) for every bundled migration, sorted by version."""
    folder = resources.files("familydb.store") / "migrations"
    found: list[tuple[int, str, str]] = []
    for entry in folder.iterdir():
        match = MIGRATION_RE.match(entry.name)
        if match:
            found.append((int(match.group(1)), entry.name, entry.read_text(encoding="utf-8")))
    found.sort()
    return found


def schema_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    return int(row["v"] or 0)


# A migration rebuilding a table others point at starts with this: dropping the old table would
# otherwise run every ON DELETE. Foreign keys cannot be switched inside a transaction, so the
# runner switches them around the migration's own (which checks its work; see 0018).
FOREIGN_KEYS_OFF = "-- foreign_keys: off"


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Apply pending migrations in order, each in its own transaction; returns versions applied."""
    current = schema_version(conn)
    applied: list[int] = []
    for version, name, sql in list_migrations():
        if version <= current:
            continue
        script = (
            f"BEGIN;\n{sql}\n"
            "INSERT INTO schema_version (version, applied_at) "
            f"VALUES ({version}, '{utcnow_iso()}');\n"
            "COMMIT;"
        )
        keys_off = sql.startswith(FOREIGN_KEYS_OFF)
        if keys_off:
            conn.execute("PRAGMA foreign_keys=OFF")
            if conn.execute("PRAGMA foreign_keys").fetchone()[0]:
                raise RuntimeError(f"{name} needs foreign keys off, and they would not switch off")
        try:
            conn.executescript(script)
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            if keys_off:
                conn.execute("PRAGMA foreign_keys=ON")
        applied.append(version)
    return applied


def table_counts(conn: sqlite3.Connection, tables: Iterable[str]) -> dict[str, int]:
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables
    }
