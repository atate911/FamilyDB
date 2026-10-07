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


# 0007 stays unused: a database may have run a 0007_web.sql that FamilyDB never kept, and must
# not mistake a new 0007 for it.
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
        conn.execute("DROP TABLE spend_holds")
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
        conn.execute("DROP TABLE memories")
        conn.execute("ALTER TABLE messages DROP COLUMN buttons")
        conn.execute("ALTER TABLE plans DROP COLUMN checked_at")
        conn.execute("DROP TABLE telegram_invites")
        conn.execute("DROP TABLE alerts")
        conn.execute("ALTER TABLE ideas DROP COLUMN lookup_wanted_at")
        conn.execute("DROP INDEX messages_sent_as_idx")
        conn.execute("ALTER TABLE messages DROP COLUMN sent_as")
        for index in ("llm_calls_turn_idx", "tool_calls_turn_idx"):
            conn.execute(f"DROP INDEX {index}")
        conn.execute("ALTER TABLE llm_calls DROP COLUMN turn")
        conn.execute("ALTER TABLE llm_calls DROP COLUMN about")
        conn.execute("ALTER TABLE tool_calls DROP COLUMN turn")
        conn.execute("DROP TABLE judgements")
        for table in ("models", "model_changes", "model_sources"):
            conn.execute(f"DROP TABLE {table}")
        conn.execute("ALTER TABLE members DROP COLUMN birth_date")
        conn.execute("ALTER TABLE members DROP COLUMN gender")
        conn.execute("DROP TABLE wishes")
        conn.execute("DROP TABLE wish_days")
        conn.execute("DROP TABLE calendar_sync_state")
        conn.execute("DROP INDEX plans_google_event_idx")
        conn.execute("ALTER TABLE ideas DROP COLUMN hidden_from")
        conn.execute("ALTER TABLE members DROP COLUMN look")
        # tasks, dropped above, comes back with 0012 and takes 0022's repeats, 0023's gift_for
        # and 0024's nudged_at on again.
        assert db.migrate(conn) == [v for v, _, _ in db.list_migrations() if v >= 8]
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


def test_the_alerts_already_noted_outlast_the_model_watch_rebuild(tmp_path, monkeypatch):
    """0031 rebuilds alerts to take the new kinds; a trouble noted before it, and who was told,
    are still there after."""
    from contextlib import closing

    with closing(db.connect(tmp_path / "old.sqlite3")) as conn:
        _up_to(monkeypatch, conn, 30)
        conn.execute(
            "INSERT INTO alerts (kind, subject, detail, first_at, last_at, times, told_at) "
            "VALUES ('credit', 'openai', 'insufficient_quota', '2026-09-20T21:03:00Z', "
            "'2026-09-20T22:03:00Z', 3, '2026-09-20T21:04:00Z')"
        )
        conn.commit()
        assert db.migrate(conn)[:2] == [31, 32]
        row = conn.execute("SELECT * FROM alerts").fetchone()
        assert (row["kind"], row["subject"], row["times"], row["told_at"]) == (
            "credit",
            "openai",
            3,
            "2026-09-20T21:04:00Z",
        )
        conn.execute(
            "INSERT INTO alerts (kind, subject, first_at, last_at) "
            "VALUES ('shift', 'chat:2026-W39', '2026-09-27T05:17:00Z', '2026-09-27T05:17:00Z')"
        )


def test_calendar_attempts_keep_their_meaning_in_one_table(tmp_path, monkeypatch):
    """0038 folds `calendar_unfinished` and `calendar_links` into `calendar_creations`: an
    unfinished attempt is still found, and a form that had taken one over still finds its event.
    """
    from contextlib import closing

    from familydb.store import calendar_ops

    with closing(db.connect(tmp_path / "old.sqlite3")) as conn:
        _up_to(monkeypatch, conn, 37)
        conn.executescript(
            "INSERT INTO calendar_creations (operation_key, event_id, result) VALUES "
            "('done', 'evt-done', '{}'), ('lost', 'evt-lost', NULL), ('lost2', 'evt-lost2', NULL);"
            "INSERT INTO calendar_unfinished (resume_key, event_id) VALUES "
            "('session-lost', 'evt-lost');"
            "INSERT INTO calendar_links (operation_key, adopted_key) VALUES ('redrawn', 'done');"
        )
        assert 38 in db.migrate(conn)
        assert calendar_ops.get(conn, "done") == "evt-done"
        assert calendar_ops.get(conn, "redrawn") == "evt-done"  # the form that took it over
        assert calendar_ops.unfinished(conn, "session-lost") == "evt-lost"
        assert calendar_ops.unfinished(conn, "nobody") is None
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert not {"calendar_unfinished", "calendar_links"} & tables
        # Two forms may now point at one event, which the old unique column forbade.
        calendar_ops.reserve(conn, "another-form", "evt-done")
        assert calendar_ops.get(conn, "another-form") == "evt-done"


def test_each_person_keeps_a_colour_from_the_day_0039_gave_them_one(tmp_path, monkeypatch):
    """0039 gives everyone already on the list a slot (1 to 8) in the order they were added, and
    a person added afterwards gets the lowest slot nobody has."""
    from contextlib import closing

    from familydb.store import members

    with closing(db.connect(tmp_path / "old.sqlite3")) as conn:
        _up_to(monkeypatch, conn, 38)
        for name in ("Sam", "Alex", "Maya", "Theo"):
            conn.execute(
                "INSERT INTO members (display_name, role, active, created_at) "
                "VALUES (?, 'parent', 1, '2026-01-01T00:00:00Z')",
                (name,),
            )
        assert 39 in db.migrate(conn)
        assert [m.slot for m in members.list_all(conn)] == [1, 2, 3, 4]
        conn.execute("DELETE FROM members WHERE display_name = 'Alex'")
        assert members.add(conn, "Robin", "kid").slot == 2  # the freed colour, not a fifth
        for name in ("a", "b", "c", "d", "e"):
            members.add(conn, name, "kid")
        assert members.add(conn, "ninth", "kid").slot in range(1, 9)  # all eight in use: shared


def test_a_present_is_kept_from_kids_by_role_after_0043(tmp_path, monkeypatch):
    """0043 takes kids out of every chosen `hidden_from` list (a present is kept from every kid,
    always), leaves NULL as the default, and says "gift" for any way of saying present."""
    from contextlib import closing

    with closing(db.connect(tmp_path / "old.sqlite3")) as conn:
        _up_to(monkeypatch, conn, 42)
        for name, role in (("Sam", "admin"), ("Alex", "parent"), ("Maya", "kid")):
            conn.execute(
                "INSERT INTO members (display_name, role, active, created_at) "
                "VALUES (?, ?, 1, '2026-01-01T00:00:00Z')",
                (name, role),
            )
        for title, kind, kept in (
            ("a", "gift", "[1,3]"),  # Sam, and Maya, a kid
            ("b", "gift", "[3]"),  # only a kid: now kept from no grown-up
            ("c", "gift", None),  # the default
            ("d", "Present", None),
        ):
            conn.execute(
                "INSERT INTO ideas (title, title_norm, kind, hidden_from, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
                (title, title, kind, kept),
            )
        assert 43 in db.migrate(conn)
        rows = conn.execute("SELECT title, kind, hidden_from FROM ideas ORDER BY id").fetchall()
        assert [(r["title"], r["kind"], r["hidden_from"]) for r in rows] == [
            ("a", "gift", "[1]"),
            ("b", "gift", "[]"),
            ("c", "gift", None),
            ("d", "gift", None),
        ]
        conn.execute("SELECT idea_id FROM tasks")  # the column is there
