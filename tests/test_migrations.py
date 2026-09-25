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
        conn.execute("DROP TABLE member_locations")  # and 0016's column with it
        conn.execute("DROP TABLE calendar_links")
        conn.execute("DROP TABLE spend_holds")
        conn.execute("DROP TABLE calendar_unfinished")
        conn.execute("DROP TABLE reminders")
        conn.execute("DROP TABLE tasks")
        conn.execute("ALTER TABLE messages DROP COLUMN cancelled_at")
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
        conn.execute("DROP TABLE member_logins")
        conn.execute("ALTER TABLE ideas DROP COLUMN happens_from")
        conn.execute("ALTER TABLE ideas DROP COLUMN happens_until")
        assert db.migrate(conn) == [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(llm_calls)")}
        assert {"provider", "web_searches", "cost_usd", "cost_estimated"} <= columns


def _up_to(monkeypatch, conn, last: int) -> None:
    """Migrate as a copy of FamilyDB from before `last + 1` would have."""
    every = db.list_migrations()
    monkeypatch.setattr(db, "list_migrations", lambda: [m for m in every if m[0] <= last])
    db.migrate(conn)
    monkeypatch.setattr(db, "list_migrations", lambda: every)


def test_a_member_becomes_a_parent_and_nobody_loses_their_history(tmp_path, monkeypatch):
    """0018 rebuilds members, which half the tables point at, one with ON DELETE SET NULL."""
    import sqlite3
    from contextlib import closing

    import pytest

    now = "2026-09-20T21:03:00Z"
    with closing(db.connect(tmp_path / "old.sqlite3")) as conn:
        _up_to(monkeypatch, conn, 17)
        conn.executescript(
            "INSERT INTO members (id, display_name, role, channel, channel_user_id, active, "
            f"created_at) VALUES (1, 'Sam', 'admin', 'telegram', '1001', 1, '{now}'), "
            f"(2, 'Alex', 'member', 'telegram', '1002', 1, '{now}'), "
            f"(3, 'the girls', 'kid', NULL, NULL, 1, '{now}'), "
            f"(4, 'Pat', 'member', NULL, NULL, 0, '{now}');"
            "INSERT INTO settings_log (key, old_value, new_value, secret, changed_at, changed_by, "
            f"source) VALUES ('web_title', NULL, '\"X\"', 0, '{now}', 2, 'web');"
            "INSERT INTO app_settings (key, value, updated_at, updated_by) "
            f"VALUES ('web_title', '\"X\"', '{now}', 2);"
            "INSERT INTO messages (channel, chat_id, member_id, direction, text, received_at) "
            f"VALUES ('web', 'web', 2, 'in', 'hi', '{now}');"
            "INSERT INTO member_logins (member_id, password_hash, temporary, set_at, set_by) "
            f"VALUES (2, 'scrypt$x', 0, '{now}', 1);"
        )
        assert db.migrate(conn)[0] == 18
        rows = conn.execute("SELECT id, display_name, role, active FROM members ORDER BY id")
        assert [tuple(row) for row in rows] == [
            (1, "Sam", "admin", 1),
            (2, "Alex", "parent", 1),
            (3, "the girls", "kid", 1),
            (4, "Pat", "parent", 0),
        ]
        # Who changed what is still known: dropping the old table ran no ON DELETE SET NULL.
        assert conn.execute("SELECT changed_by FROM settings_log").fetchone()[0] == 2
        assert conn.execute("SELECT updated_by FROM app_settings").fetchone()[0] == 2
        assert conn.execute("SELECT member_id FROM messages").fetchone()[0] == 2
        login = conn.execute("SELECT member_id, set_by FROM member_logins").fetchone()
        assert tuple(login) == (2, 1)
        # And the lock is back on the door: foreign keys enforced, the new roles, unique names.
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.execute(
                "INSERT INTO messages (channel, chat_id, member_id, direction, text, received_at) "
                "VALUES ('web', 'web', 99, 'in', 'x', 'now')"
            )
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                "INSERT INTO members (display_name, role, created_at) VALUES ('Jo', 'member', 'n')"
            )
        with pytest.raises(sqlite3.IntegrityError, match="members_name_idx"):
            conn.execute(
                "INSERT INTO members (display_name, role, created_at) VALUES ('ALEX', 'kid', 'n')"
            )


def test_foreign_keys_are_off_only_for_a_migration_that_asks(tmp_path, monkeypatch):
    from contextlib import closing

    import pytest

    probe = (
        db.FOREIGN_KEYS_OFF
        + "\nCREATE TABLE probe AS SELECT foreign_keys AS seen FROM pragma_foreign_keys;"
    )
    broken = db.FOREIGN_KEYS_OFF + "\nCREATE TABLE not valid sql;"
    with closing(db.connect(tmp_path / "db.sqlite3")) as conn:
        _up_to(monkeypatch, conn, 18)
        monkeypatch.setattr(db, "list_migrations", lambda: [(9001, "9001_probe.sql", probe)])
        assert db.migrate(conn) == [9001]
        assert conn.execute("SELECT seen FROM probe").fetchone()[0] == 0
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        monkeypatch.setattr(db, "list_migrations", lambda: [(9002, "9002_broken.sql", broken)])
        with pytest.raises(Exception, match="syntax error"):
            db.migrate(conn)
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1  # back on after a failure
        assert db.schema_version(conn) == 9001


def test_a_rebuild_that_would_leave_a_reference_to_nobody_is_rolled_back(tmp_path, monkeypatch):
    """The check at the end of 0018: here the copy is made to drop Alex, whom a message names."""
    from contextlib import closing

    import pytest

    every = db.list_migrations()
    version, name, sql = next(m for m in every if m[0] == 18)
    assert name == "0018_parent_role.sql"
    lossy = sql.replace("    FROM members;", "    FROM members WHERE display_name != 'Alex';")
    assert lossy != sql
    with closing(db.connect(tmp_path / "db.sqlite3")) as conn:
        _up_to(monkeypatch, conn, 17)
        conn.executescript(
            "INSERT INTO members (id, display_name, role, active, created_at) "
            "VALUES (2, 'Alex', 'member', 1, 'now');"
            "INSERT INTO messages (channel, chat_id, member_id, direction, text, received_at) "
            "VALUES ('web', 'web', 2, 'in', 'hi', 'now');"
        )
        monkeypatch.setattr(db, "list_migrations", lambda: [(version, name, lossy)])
        with pytest.raises(Exception, match="CHECK constraint failed"):
            db.migrate(conn)
        assert db.schema_version(conn) == 17
        assert conn.execute("SELECT role FROM members WHERE id = 2").fetchone()[0] == "member"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
