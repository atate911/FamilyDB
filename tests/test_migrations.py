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


# PR #2 shipped a 0007_web.sql that was not taken. The number stays unused so that a database
# which ran it never mistakes a new 0007 for one it already has.
RETIRED = {7}


def test_migration_files_are_well_formed() -> None:
    migrations = db.list_migrations()
    versions = [version for version, _, _ in migrations]
    expected = [v for v in range(1, max(versions) + 1) if v not in RETIRED]
    assert versions == expected
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


def test_recovery_migration_does_not_resend_historical_replies(tmp_path):
    from contextlib import closing

    from familydb.store import messages

    with closing(db.connect(tmp_path / "old.sqlite3")) as conn:
        db.schema_version(conn)
        for version, _name, sql in db.list_migrations():
            if version >= 6:
                break
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_version VALUES (?, '2026-09-20')", (version,))
        old = messages.insert_out(conn, channel="telegram", chat_id="1", text="Old reply")
        assert db.migrate(conn)[0] == 6
        assert messages.get(conn, old.id).delivered_at is not None
        new = messages.insert_out(conn, channel="telegram", chat_id="1", text="New reply")
        assert messages.get(conn, new.id).delivered_at is None


def test_a_database_that_ran_the_retired_0007_still_gets_what_follows(tmp_path):
    from contextlib import closing

    with closing(db.connect(tmp_path / "pr2.sqlite3")) as conn:
        db.migrate(conn)
        conn.execute("DELETE FROM schema_version WHERE version > 6")
        conn.execute("INSERT INTO schema_version VALUES (7, '2026-09-21')")
        conn.execute("ALTER TABLE llm_calls DROP COLUMN cost_usd")
        conn.execute("ALTER TABLE llm_calls DROP COLUMN provider")
        conn.execute("ALTER TABLE llm_calls DROP COLUMN web_searches")
        conn.execute("ALTER TABLE llm_calls DROP COLUMN cost_estimated")
        conn.execute("DROP INDEX llm_calls_created_idx")
        conn.execute("DROP TABLE knocks")
        conn.execute("ALTER TABLE llm_calls DROP COLUMN kind")
        conn.execute("ALTER TABLE llm_calls DROP COLUMN sections")
        assert db.migrate(conn) == [8, 9, 10, 11]
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(llm_calls)")}
        assert {"provider", "web_searches", "cost_usd", "cost_estimated"} <= columns
