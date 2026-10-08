"""`maintain.sh doctor`: it looks, says what is wrong and why, shows what it will do and what only
the person can do, does the safe steps on one Enter, looks again and says what came right
(scripts/lib/repair.sh). Each case breaks an install that is well in one way and reads the whole
run.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from contextlib import closing

import pytest

from tests.install_fixture import (
    corrupt,
    database_behind,
    healthy_install,
    logging_stub,
    maintain,
    maintain_on_tty,
    stub,
    unit_file,
)

pytestmark = pytest.mark.skipif(not shutil.which("bash") or os.name == "nt", reason="needs bash")
IS_ROOT = os.geteuid() == 0 if hasattr(os, "geteuid") else False


def flat(text: str) -> str:
    return " ".join(text.split())


def rebuilding_uv(env, log, program=None) -> None:
    """A uv that makes the environment again, as `uv sync` does, and notes that it was asked."""
    stub(
        env,
        "uv",
        "#!/bin/sh\n"
        f'echo "uv $*" >> "{log}"\n'
        'while [ $# -gt 0 ]; do [ "$1" = --project ] && { project="$2"; break; }; shift; done\n'
        'mkdir -p "$project/.venv/bin"\n'
        f'printf \'#!/bin/sh\\nexec "{sys.executable}" "$@"\\n\' > "$project/.venv/bin/python"\n'
        'chmod +x "$project/.venv/bin/python"\n'
        + (f'cp "{program}" "$project/.venv/bin/familydb"\n' if program else ""),
    )


def test_an_install_that_is_well_is_left_alone_and_said_to_be(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = maintain(target, env, "doctor", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "It is running, and every check is fine." in done.stdout
    assert "[ OK ] Nothing is wrong" in done.stdout
    assert "What I will do" not in done.stdout


def test_missing_files_are_explained_then_put_back_and_the_run_ends_restored(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / "src/familydb/web/static/themes.css").unlink()
    (target / "src/familydb/web/templates/base.html").unlink()
    done = maintain(target, env, "doctor", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    out = flat(done.stdout)
    # why first, then what it will do, then it does it, then it says what is better
    order = [
        out.index(w)
        for w in (
            "What is wrong, from the bottom up",
            "What I will do",
            "Put back the missing program files",
            "What is better now",
            "[ OK ] Restored",
        )
    ]
    assert order == sorted(order), out
    assert "themes.css" in out and "so pages cannot be drawn" in out
    assert (target / "src/familydb/web/static/themes.css").exists()
    assert (target / "src/familydb/web/templates/base.html").exists()
    assert "✓ program files" in out and "✓ missing files" in out


def test_a_python_environment_that_is_gone_is_built_again_and_the_download_is_said_first(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".venv/bin/python").unlink()
    program = tmp_path / "familydb.program"
    shutil.copy(target / ".venv/bin/familydb", program)
    log = tmp_path / "calls.log"
    rebuilding_uv(env, log, program)
    done = maintain(target, env, "doctor", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    out = flat(done.stdout)
    assert "Rebuild the Python environment" in out and "downloads" in out
    assert f"uv sync --frozen --no-dev --project {target}" in log.read_text()
    assert (target / ".venv/bin/python").exists()
    assert "[ OK ] Restored" in out


def test_a_database_behind_the_code_is_migrated_after_a_backup(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    database_behind(target / "data/familydb.sqlite3")
    before = set((target / "backups").iterdir())
    done = maintain(target, env, "doctor", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Bring the database up to date" in done.stdout
    assert set((target / "backups").iterdir()) - before
    with closing(sqlite3.connect(target / "data/familydb.sqlite3")) as conn:
        assert conn.execute("select max(version) from schema_version").fetchone()[0] >= 57


def test_a_byte_order_mark_and_windows_line_ends_are_cleaned_and_the_old_file_kept(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").write_bytes(b"\xef\xbb\xbfWEB_ENABLED=true\r\nWEB_PORT=8080\r\n")
    done = maintain(target, env, "doctor", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert (target / ".env").read_bytes() == b"WEB_ENABLED=true\nWEB_PORT=8080\n"
    kept = list(target.glob(".env.before-doctor-*"))
    assert len(kept) == 1 and kept[0].read_bytes().startswith(b"\xef\xbb\xbf")
    assert oct(kept[0].stat().st_mode & 0o777) == "0o600", (
        "a copy of a file of secrets is private too"
    )


def test_a_missing_env_file_is_started_again_from_the_example(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").unlink()
    done = maintain(target, env, "doctor", "--yes")
    assert "Start a new .env from the example" in done.stdout
    assert (target / ".env").exists()
    assert oct((target / ".env").stat().st_mode & 0o777) == "0o600"


def test_a_service_file_that_points_at_nothing_is_written_again_with_the_old_one_kept(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    unit = unit_file(tmp_path, env, target, ExecStart=f"{target}/.venv/bin/no-such-program run")
    log = tmp_path / "systemctl.log"
    env["FAKE_SYSTEMCTL_LOG"] = str(log)
    done = maintain(target, env, "doctor", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Write the service file again" in done.stdout
    assert f"ExecStart={target}/.venv/bin/familydb run" in unit.read_text()
    assert "no-such-program" in (unit.parent / "familydb.service.before-doctor").read_text()
    assert "daemon-reload" in log.read_text()


def test_the_log_names_what_the_checks_could_not_so_the_cause_is_found_anyway(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    unit_file(tmp_path, env, target)
    log = tmp_path / "calls.log"
    rebuilding_uv(env, log)
    stub(env, "journalctl", "#!/bin/sh\necho \"ModuleNotFoundError: No module named 'waitress'\"\n")
    done = maintain(
        target,
        env,
        "doctor",
        "--yes",
        FAKE_SYSTEMD=json.dumps({"active": "failed", "SubState": "failed"}),
    )
    out = flat(done.stdout)
    assert "What its log says" in out and "No module named 'waitress'" in out
    assert "Rebuild the Python environment" in out
    assert "uv sync" in log.read_text()


def test_what_only_the_person_can_do_is_said_with_the_command_and_the_rest_goes_on(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").write_text("WEB_ENABLED=true\nWEB_PORT=8080\nWEB_DOMAIN=family.example.com\n")
    stub(env, "getent", "#!/bin/sh\nexit 2\n")
    stub(env, "caddy", "#!/bin/sh\nexit 0\n")
    done = maintain(target, env, "doctor", "--yes")
    out = flat(done.stdout)
    assert "What only you can do" in out
    assert "does not resolve from this machine" in out
    assert "an A record for the name pointing at this server" in out
    assert done.returncode == 1  # nothing for it to do, and the page is not reachable by name
    assert "There is nothing I can do for this from here" in out


def test_a_dry_run_shows_the_plan_and_changes_nothing(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    css = target / "src/familydb/web/static/themes.css"
    css.unlink()
    done = maintain(target, env, "doctor", "--dry-run")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "What I will do" in done.stdout
    assert "Dry run finished: nothing was changed" in done.stdout
    assert not css.exists()


def test_without_a_terminal_and_without_yes_it_says_so_and_changes_nothing_and_fails(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    css = target / "src/familydb/web/static/themes.css"
    css.unlink()
    done = maintain(target, env, "doctor")
    assert not css.exists()
    assert done.returncode == 1
    assert "run it at a terminal, or with --yes" in flat(done.stdout)


def test_at_a_terminal_enter_goes_ahead_and_n_does_not(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    css = target / "src/familydb/web/static/themes.css"
    css.unlink()
    code, shown = maintain_on_tty(target, env, "doctor", keys="n\n")
    assert code == 0 and not css.exists() and "Nothing was changed." in shown
    code, shown = maintain_on_tty(target, env, "doctor", keys="\n")
    assert code == 0, shown
    assert css.exists() and "[ OK ] Restored" in shown


def test_a_damaged_database_is_the_one_step_that_asks_again_and_never_on_yes_alone(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    db = target / "data/familydb.sqlite3"
    corrupt(db)
    skipped = maintain(target, env, "doctor", "--yes")
    assert db.read_bytes().startswith(b"this is not a database"), "--yes never replaces a database"
    assert skipped.returncode == 1
    assert "Not fully restored" in skipped.stdout
    assert "asks you first" in skipped.stdout

    code, shown = maintain_on_tty(target, env, "doctor", keys="\n\nyes\n")
    assert code == 0, shown
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("pragma quick_check").fetchone()[0] == "ok"
    assert "[ OK ] Restored" in shown
    assert list((target / "backups").glob("set-aside-*")), "the damaged file was kept"


def test_when_it_cannot_put_things_right_it_says_what_is_left_and_what_to_try_next(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".venv/bin/python").unlink()
    logging_stub(
        env, "uv", tmp_path / "calls.log"
    )  # a uv that does nothing: the environment stays gone
    done = maintain(target, env, "doctor", "--yes")
    out = flat(done.stdout)
    assert done.returncode == 1
    assert "What is still not right" in out and "interpreter" in out
    assert "Not fully restored" in out
    assert "What to do next" in out and "maintain.sh logs" in out and "check --all" in out


def test_the_optional_things_are_asked_after_the_repair_and_one_at_a_time(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    stub(env, "crontab", "#!/bin/sh\nexit 1\n")
    (target / "src/familydb/web/static/themes.css").unlink()
    code, shown = maintain_on_tty(target, env, "doctor", keys="\nn\n")
    assert code == 0, shown
    flat_shown = flat(shown)
    assert flat_shown.index("[ OK ]") < flat_shown.index(
        "While I am here: Set up the nightly backup"
    )


def test_check_still_only_reads(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    css = target / "src/familydb/web/static/themes.css"
    css.unlink()
    done = maintain(target, env, "check", "--yes")
    assert done.returncode == 1
    assert not css.exists()
    assert "What I will do" not in done.stdout


@pytest.mark.parametrize(
    ("folder", "allowed"),
    [
        ("{target}/data", True),
        ("{target}/some/deeper/data", True),
        ("/var/lib/familydb", True),
        ("{target}", False),
        ("/", False),
        ("/etc", False),
        ("/var", False),
        ("/home/someone", False),
        ("/srv/anything-else", False),
    ],
)
def test_a_repair_only_hands_over_a_folder_that_could_be_familydbs(
    tmp_path, folder, allowed
) -> None:
    """FAMILYDB_PATH can be anything, and a repair that runs `chown -R` on it must not follow it
    into a system folder or the code."""
    import subprocess

    from tests.install_fixture import BASH, ROOT

    target = "/opt/familydb"
    path = folder.format(target=target)
    done = subprocess.run(
        [
            BASH,
            "-c",
            f'. "{ROOT}/scripts/lib/common.sh"; . "{ROOT}/scripts/lib/doctor.sh"; '
            f'TARGET={target}; dc_data_dir_ok "{path}"',
        ],
        capture_output=True,
        text=True,
    )
    assert (done.returncode == 0) is allowed, path


def test_windows_line_ends_in_env_do_not_make_every_value_look_wrong(tmp_path) -> None:
    from tests.test_doctor_machine import check, mark_of

    target, env = healthy_install(tmp_path)
    (target / ".env").write_bytes(b"WEB_ENABLED=true\r\nWEB_PORT=8080\r\n")
    done = check(target, env)
    assert mark_of(done, ".env syntax") == "!"
    assert mark_of(done, "web port") == "✓", "the carriage return is not part of the port"
    assert "web page" not in {
        name for name in __import__("tests.install_fixture", fromlist=["rows"]).rows(done.stdout)
    }
