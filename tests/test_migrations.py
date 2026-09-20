from pathlib import Path

from familydb.config import Settings
from familydb.store import db

EXPECTED_TABLES = {
    "members",
    "ideas",
    "places",
    "plans",
    "outcomes",
    "suggestions",
    "messages",
    "tool_calls",
    "llm_calls",
    "ideas_fts",
    "schema_version",
}


def test_fresh_database_reaches_latest_version(settings: Settings) -> None:
    conn = db.connect(settings.familydb_path)
    applied = db.migrate(conn)
    versions = [version for version, _, _ in db.list_migrations()]
    assert applied == versions
    assert db.schema_version(conn) == versions[-1]
    assert db.migrate(conn) == []  # second run is a no-op
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables >= EXPECTED_TABLES
    conn.close()


def test_migration_files_are_well_formed() -> None:
    migrations = db.list_migrations()
    versions = [version for version, _, _ in migrations]
    assert versions == list(range(1, len(versions) + 1))
    for _, name, sql in migrations:
        assert "COMMIT" not in sql.upper(), f"{name} must not manage its own transaction"


def test_connect_creates_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "db.sqlite3"
    conn = db.connect(path)
    assert path.exists()
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    conn.close()


def test_phase2_columns_exist(conn) -> None:
    def columns(table: str) -> set[str]:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}

    assert "enrichment_note" in columns("ideas")
    assert {"followed_up_at", "channel", "chat_id"} <= columns("plans")
