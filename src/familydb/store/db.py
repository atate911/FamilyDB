"""SQLite connection handling, transactions, JSON helpers and migrations."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any

from familydb.base.errors import MigrationError

MIGRATION_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
# 0007 was shipped once and never kept, so a database may record it with nothing to show for it
# (tests/test_migrations.py): never used again, and never a gap.
RESERVED = frozenset({7})


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
    # The runner's own record of each file as applied (never a migration's business): an applied
    # migration edited since is caught before anything else runs on the database.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_checksums "
        "(version INTEGER PRIMARY KEY, checksum TEXT NOT NULL)"
    )
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    return int(row["v"] or 0)


def checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def _check_applied(
    conn: sqlite3.Connection, bundled: list[tuple[int, str, str]], current: int
) -> None:
    """Refuse a database whose applied migrations are not the bundled ones: a file changed after
    it was applied (by its checksum, recorded as applied; a record from before checksums were
    kept is taken on trust once), or a bundled file numbered below the newest applied that was
    never applied (merged late: applying it now, after what came later, is not what it was
    written for)."""
    applied = {int(row["version"]) for row in conn.execute("SELECT version FROM schema_version")}
    recorded = {
        int(row["version"]): row["checksum"]
        for row in conn.execute("SELECT version, checksum FROM schema_checksums")
    }
    changed, missing, unrecorded = [], [], []
    for version, name, sql in bundled:
        if version > current:
            continue
        if version not in applied:
            if version not in RESERVED:
                missing.append(name)
            continue
        if version not in recorded:
            unrecorded.append((version, checksum(sql)))
        elif recorded[version] != checksum(sql):
            changed.append(name)
    if changed:
        raise MigrationError(
            "applied migrations were changed since: "
            + ", ".join(changed)
            + "; a migration is never edited once applied, so put the file back as it was and add "
            "a new one"
        )
    if missing:
        raise MigrationError(
            "never applied, though later ones were: "
            + ", ".join(missing)
            + "; a migration numbered below the newest applied cannot be run after it, so give it "
            "the next number"
        )
    if unrecorded:
        conn.executemany(
            "INSERT OR IGNORE INTO schema_checksums (version, checksum) VALUES (?, ?)", unrecorded
        )


# A migration rebuilding a table others point at starts with this: dropping the old table would
# otherwise run every ON DELETE. Foreign keys cannot be switched inside a transaction, so the
# runner switches them around the migration's own (which checks its work; see 0018).
FOREIGN_KEYS_OFF = "-- foreign_keys: off"


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Apply pending migrations in order, each in its own transaction; returns versions applied."""
    current = schema_version(conn)
    bundled = list_migrations()
    _check_applied(conn, bundled, current)
    applied: list[int] = []
    for version, name, sql in bundled:
        if version <= current:
            continue
        script = (
            f"BEGIN;\n{sql}\n"
            "INSERT INTO schema_version (version, applied_at) "
            f"VALUES ({version}, '{utcnow_iso()}');\n"
            "INSERT OR REPLACE INTO schema_checksums (version, checksum) "
            f"VALUES ({version}, '{checksum(sql)}');\n"
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


def dump_table(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    """Every row of a table by id, as dicts: for the family's export."""
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id")]


def answers(conn: sqlite3.Connection) -> bool:
    """Whether the database answers at all (the health check's first question)."""
    return conn.execute("SELECT 1").fetchone() is not None


def write_probe(conn: sqlite3.Connection) -> None:
    """Make and drop a table, so a file nobody may write to says so here (the doctor)."""
    conn.execute("CREATE TABLE IF NOT EXISTS _doctor_write_probe (x INTEGER)")
    conn.execute("DROP TABLE _doctor_write_probe")


def quick_check(conn: sqlite3.Connection) -> list[str]:
    """SQLite's own check of the file: ["ok"], or what it found."""
    return [str(row[0]) for row in conn.execute("PRAGMA quick_check").fetchall()]


def table_counts(conn: sqlite3.Connection, tables: Iterable[str]) -> dict[str, int]:
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables
    }
