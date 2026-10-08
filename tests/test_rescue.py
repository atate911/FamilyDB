"""`maintain.sh rescue`: the ways out for the day the usual fixes are not enough
(scripts/lib/rescue.sh). Each is read from a real install on a temporary folder, with a terminal
for the answers that need a person and none for the ones that must never be given by --yes.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import time
from contextlib import closing

import pytest

from familydb.store.db import list_migrations
from tests.install_fixture import (
    age_file,
    corrupt,
    database_behind,
    drop_last_migration,
    git,
    healthy_install,
    logging_stub,
    maintain,
    maintain_on_tty,
    stub,
)

pytestmark = pytest.mark.skipif(not shutil.which("bash") or os.name == "nt", reason="needs bash")


# -- the menu


def test_the_menu_lists_the_five_ways_and_changes_nothing_without_a_terminal(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = maintain(target, env, "rescue")
    assert done.returncode == 0, done.stdout + done.stderr
    for way in (
        "Nobody can sign in",
        "will not start",
        "upgrade broke it",
        "database is damaged",
        "disk is full",
    ):
        assert way in done.stdout
    assert "rescue locked-out | wont-start | rollback | database | space" in done.stdout
    assert "[ OK ] Nothing was changed" in done.stdout


def test_the_menu_runs_the_way_that_is_picked(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    code, shown = maintain_on_tty(target, env, "rescue", keys="4\n")
    assert code == 0, shown
    assert "Nothing to repair" in shown  # the database is sound
    code, shown = maintain_on_tty(target, env, "rescue", keys="\n")
    assert "Nothing was changed" in shown


def test_an_unknown_way_names_the_ones_there_are(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = maintain(target, env, "rescue", "frobnicate")
    assert done.returncode == 1
    assert "locked-out, wont-start, rollback, database, space" in done.stderr


# -- nobody can get in


def test_a_page_that_is_switched_off_is_switched_on_again_and_the_tunnel_is_shown(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").write_text("WEB_ENABLED=false\nWEB_PORT=8080\n")
    done = maintain(target, env, "rescue", "locked-out", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "switched OFF in .env" in done.stdout
    assert "Set WEB_ENABLED=true in .env" in done.stdout
    assert "WEB_ENABLED=true" in (target / ".env").read_text()
    assert "ssh -L 8080:127.0.0.1:8080" in done.stdout
    assert "http://127.0.0.1:8080/" in done.stdout


def test_a_new_password_is_made_for_the_person_named_and_shown_once(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    code, shown = maintain_on_tty(target, env, "rescue", "locked-out", keys="n\ny\nSam\nn\n")
    assert code == 0, shown
    assert "Sam [admin]" in shown  # who can sign in is listed
    assert "Sam's password is now: correct-horse-battery" in shown
    assert "cannot be shown again" in shown


def test_signing_everyone_out_needs_a_typed_yes_and_is_never_given_by_yes(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    secret = target / "data" / "web_secret"
    secret.write_text("key")
    done = maintain(target, env, "rescue", "locked-out", "--yes")
    assert secret.exists(), "--yes must not sign everyone out"
    assert "never done without a person at a terminal" in done.stdout + done.stderr

    _code, shown = maintain_on_tty(target, env, "rescue", "locked-out", keys="n\nn\nno\n")
    assert secret.exists()
    _code, shown = maintain_on_tty(target, env, "rescue", "locked-out", keys="n\nn\nyes\n")
    assert not secret.exists(), shown
    assert "Signed everyone out" in shown


def test_a_restart_is_offered_for_the_too_many_tries_lockout(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    log = tmp_path / "calls.log"
    logging_stub(env, "systemctl", log)
    unit = tmp_path / "familydb.service"
    unit.write_text("[Service]\n")
    env["FAMILYDB_SERVICE_UNIT"] = str(unit)
    code, shown = maintain_on_tty(target, env, "rescue", "locked-out", keys="y\nn\n")
    assert code == 0, shown
    assert "Too many tries" in shown
    assert (
        "systemctl stop familydb" in log.read_text()
        and "systemctl start familydb" in log.read_text()
    )


# -- it will not start


def test_a_python_that_is_gone_is_built_again_from_the_lock(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".venv/bin/python").unlink()
    log = tmp_path / "calls.log"
    logging_stub(env, "uv", log)
    done = maintain(target, env, "rescue", "wont-start", "--yes")
    assert "✗ interpreter" in done.stdout
    assert "Installing the packages from uv.lock" in done.stdout
    assert f"uv sync --frozen --no-dev --project {target}" in log.read_text()


def test_program_files_that_are_gone_are_put_back_by_git(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    css = target / "src/familydb/web/static/style.css"
    css.unlink()
    done = maintain(target, env, "rescue", "wont-start", "--yes")
    assert (
        "Put back the program files" in done.stdout or "Restoring the program files" in done.stdout
    )
    assert css.exists()


def test_a_database_behind_the_code_is_migrated_after_a_backup(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    database_behind(target / "data/familydb.sqlite3")
    before = set((target / "backups").iterdir())
    done = maintain(target, env, "rescue", "wont-start", "--yes")
    assert "Applying the migrations" in done.stdout
    assert set((target / "backups").iterdir()) - before, "a backup is taken before the migration"


def test_a_setting_saved_on_the_page_can_be_forgotten_by_name(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    db = target / "data/familydb.sqlite3"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute(
            "insert into app_settings (key, value, updated_at, updated_by) values "
            "('daily_spend_limit', '9999', 'x', 'test')"
        )
        conn.commit()
    code, shown = maintain_on_tty(
        target, env, "rescue", "wont-start", keys="y\ndaily_spend_limit\n"
    )
    assert code == 0, shown
    assert "daily_spend_limit" in shown
    assert "Forgot daily_spend_limit" in shown
    with closing(sqlite3.connect(db)) as conn:
        assert (
            conn.execute(
                "select count(*) from app_settings where key = 'daily_spend_limit'"
            ).fetchone()[0]
            == 0
        )
    assert list((target / "backups").glob("familydb-*.sqlite3")), "kept a backup first"


# -- an upgrade broke it


def _two_versions(target, env, *, without_newest_migration: bool = False):
    """The install at an older commit, then at the one the 'upgrade' moved it to; returns both."""
    migrations = sorted((target / "src/familydb/store/migrations").glob("[0-9]*.sql"))
    newest = migrations[-1]
    if without_newest_migration:
        text = newest.read_text()
        newest.unlink()
        git(target, "add", "-A")
        git(target, "commit", "-qm", "before the newest migration")
        older = git(target, "rev-parse", "HEAD")
        newest.write_text(text)
    else:
        older = git(target, "rev-parse", "HEAD")
        (target / "NOTES").write_text("changed by the upgrade\n")
    git(target, "add", "-A")
    git(target, "commit", "-qm", "the upgrade")
    ledger = tmp = target.parent / "ledger"
    ledger.mkdir(exist_ok=True)
    return older, tmp


def test_an_upgrade_that_changed_no_data_is_undone_by_putting_the_code_back(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    older, ledger = _two_versions(target, env)
    (ledger / "last-upgrade").write_text(
        f"at={int(time.time()) - 600}\nfrom={older}\nfrom_label=older\n"
        "to=x\nto_label=newer\nbackup=/none\n"
    )
    log = tmp_path / "calls.log"
    logging_stub(env, "uv", log)
    done = maintain(target, env, "rescue", "rollback", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "only the code goes back" in " ".join(done.stdout.split())
    assert git(target, "rev-parse", "HEAD") == older
    assert not (target / "NOTES").exists()
    assert "uv sync --frozen --no-dev" in log.read_text()
    assert not (ledger / "last-upgrade").exists(), "a second rollback must not flip back"
    assert "[ OK ] Back on" in done.stdout


def test_an_upgrade_that_migrated_the_data_puts_the_old_database_back_only_on_a_typed_yes(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    older, ledger = _two_versions(target, env, without_newest_migration=True)
    db = target / "data/familydb.sqlite3"
    saved = target / "backups/before-the-upgrade.sqlite3"
    shutil.copy(db, saved)
    drop_last_migration(saved)
    (ledger / "last-upgrade").write_text(
        f"at={int(time.time()) - 600}\nfrom={older}\nfrom_label=older\n"
        f"to=x\nto_label=newer\nbackup={saved}\n"
    )
    logging_stub(env, "uv", tmp_path / "calls.log")
    refused = maintain(target, env, "rescue", "rollback", "--yes")
    assert "has to go back too" in " ".join(refused.stdout.split())
    assert "Nothing was changed" in refused.stdout
    assert git(target, "rev-parse", "HEAD") != older

    code, shown = maintain_on_tty(target, env, "rescue", "rollback", keys="yes\n")
    assert code == 0, shown
    assert "Everything saved since then is lost" in shown
    assert git(target, "rev-parse", "HEAD") == older
    with closing(sqlite3.connect(db)) as conn:
        newest = list_migrations()[-1][0]
        assert conn.execute("select max(version) from schema_version").fetchone()[0] < newest
    assert "restore" in shown  # and the copy of the database as it was is named, to undo this


def test_without_a_record_it_says_how_to_go_back_by_hand(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = maintain(target, env, "rescue", "rollback", "--yes")
    assert done.returncode == 1
    assert "does not know what to go back to" in done.stderr
    assert "git -C" in done.stderr and "checkout --detach" in done.stderr


def test_an_upgrade_that_stopped_part_way_is_the_one_undone(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    older, ledger = _two_versions(target, env)
    (ledger / "upgrade-pending").write_text(f"target=main\nbefore={older}\nbackup=/none\n")
    logging_stub(env, "uv", tmp_path / "calls.log")
    done = maintain(target, env, "rescue", "rollback", "--yes")
    assert "an upgrade that stopped part-way" in done.stdout
    assert git(target, "rev-parse", "HEAD") == older
    assert not (ledger / "upgrade-pending").exists()


# -- the database is damaged


def test_a_sound_database_is_not_touched(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    before = (target / "data/familydb.sqlite3").read_bytes()
    done = maintain(target, env, "rescue", "database", "--yes")
    assert "Nothing to repair" in done.stdout
    assert (target / "data/familydb.sqlite3").read_bytes() == before


def test_a_damaged_database_is_replaced_by_the_newest_sound_backup_and_kept_aside(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    db = target / "data/familydb.sqlite3"
    corrupt(db)
    older = target / "backups/familydb-20260101000000.sqlite3"
    shutil.copy(target / "backups/familydb-20260914030000.sqlite3", older)
    age_file(older, 24 * 30)
    code, shown = maintain_on_tty(target, env, "rescue", "database", keys="\nyes\n")
    assert code == 0, shown
    assert "SQLite cannot read it as a FamilyDB database" in shown
    assert "familydb-20260914030000.sqlite3" in shown
    assert "Kept the damaged database in" in shown
    aside = list((target / "backups").glob("set-aside-*"))
    assert aside and (aside[0] / "familydb.sqlite3").read_bytes().startswith(
        b"this is not a database"
    )
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("pragma quick_check").fetchone()[0] == "ok"
    assert "[ OK ] Restored from" in shown


def test_a_damaged_database_is_never_replaced_by_yes_alone(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    db = target / "data/familydb.sqlite3"
    corrupt(db)
    done = maintain(target, env, "rescue", "database", "--yes")
    assert db.read_bytes().startswith(b"this is not a database")
    assert f"sudo {target}/scripts/maintain.sh restore" in done.stdout
    assert (
        "not sound" not in done.stdout.split("Backups, newest first")[1].split("familydb-2026")[0]
    )


def test_a_backup_that_is_itself_damaged_is_not_offered(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    corrupt(target / "data/familydb.sqlite3")
    corrupt(target / "backups/familydb-20260914030000.sqlite3")
    _code, shown = maintain_on_tty(target, env, "rescue", "database", keys="n\n")
    assert "not sound" in shown
    assert "Restore which?" not in shown


SQLITE3 = r"""#!{python}
import os, sqlite3, sys

# `sqlite3 FILE .recover` writes SQL; `sqlite3 FILE` reads SQL from its input into FILE.
if sys.argv[2:3] == [".recover"]:
    sys.stdout.write(open(os.environ["FAKE_RECOVER_SQL"]).read())
else:
    sqlite3.connect(sys.argv[1]).executescript(sys.stdin.read())
"""


def test_what_can_be_read_of_a_damaged_file_is_salvaged_into_a_new_one_beside_it(tmp_path) -> None:
    import sys

    target, env = healthy_install(tmp_path)
    db = target / "data/familydb.sqlite3"
    with closing(sqlite3.connect(db)) as conn:
        dump = tmp_path / "recovered.sql"
        dump.write_text("\n".join(conn.iterdump()))
        conn.execute("drop table members")  # a FamilyDB database without its family: not one to run
        conn.commit()
    (target / "backups/familydb-20260914030000.sqlite3").unlink()
    stub(env, "sqlite3", SQLITE3.format(python=sys.executable))
    before = db.read_bytes()
    code, shown = maintain_on_tty(
        target, env, "rescue", "database", keys="\n", FAKE_RECOVER_SQL=str(dump)
    )
    assert code == 0, shown
    assert "None in" in shown  # no backup to go back to, so salvage is the way
    assert "Salvaged into" in shown and "passes SQLite's check" in shown
    salvaged = list((target / "backups").glob("salvaged-*.sqlite3"))
    assert len(salvaged) == 1
    assert db.read_bytes() == before, "the original is never touched"
    with closing(sqlite3.connect(salvaged[0])) as conn:
        assert conn.execute("select count(*) from members").fetchone()[0] == 0
    assert f"sudo {target}/scripts/maintain.sh restore {salvaged[0]}" in shown


# -- the disk is full


def test_what_can_be_freed_is_listed_and_the_safe_things_are_done_on_yes(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    log = tmp_path / "calls.log"
    logging_stub(
        env,
        "journalctl",
        log,
        'echo "Archived and active journals take up 512.0M in the file system."',
    )
    logging_stub(env, "apt-get", log)
    stub(
        env,
        "du",
        '#!/bin/sh\ncase "$*" in *-sm*apt*) echo "300\t/var/cache/apt/archives" ;;'
        ' *) exec /usr/bin/du "$@" ;; esac\n',
    )
    done = maintain(target, env, "rescue", "space", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "512 MB of system logs" in done.stdout
    assert "journalctl --vacuum-size=200M" in log.read_text()
    assert "apt-get clean" in log.read_text()


def test_old_backups_are_deleted_only_on_a_typed_yes_and_the_newest_stay(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    for day in (20, 25, 30):
        old = target / f"backups/familydb-202501{day:02d}000000.sqlite3"
        old.write_text("x")
        age_file(old, 24 * day)
    maintain(target, env, "rescue", "space", "--yes")
    assert len(list((target / "backups").glob("familydb-*.sqlite3"))) == 4, (
        "--yes must not delete backups"
    )
    code, shown = maintain_on_tty(target, env, "rescue", "space", keys="yes\n")
    assert code == 0, shown
    left = sorted(p.name for p in (target / "backups").glob("familydb-*.sqlite3"))
    assert left == ["familydb-20260914030000.sqlite3"], left


def test_a_dry_run_says_what_it_would_do_and_does_none_of_it(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").write_text("WEB_ENABLED=false\n")
    done = maintain(target, env, "rescue", "locked-out", "--dry-run", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "[dry run] would set WEB_ENABLED=true" in done.stdout
    assert "WEB_ENABLED=false" in (target / ".env").read_text()
