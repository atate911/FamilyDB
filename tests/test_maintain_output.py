"""What `scripts/maintain.sh` says: the rows `status` lays out, what it counts as wanting a look,
and the words it tells time and size in. These run the script's own functions, with root, cron
and the network stood in for."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from tests.test_https_port import BASH, _maintain_function, _shell

pytestmark = pytest.mark.skipif(not BASH or os.name == "nt", reason="needs bash")

HELPERS = ("section", "row", "more", "ago", "human_size", "took", "env_file_value", "app_port")


def _run(script: str, *names: str, **env: str):
    functions = "".join(_maintain_function(name) for name in (*HELPERS, *names))
    return _shell("ISSUES=()\n" + functions + script, **env)


def test_time_and_size_are_said_the_way_a_person_would() -> None:
    done = _run(
        "for s in 5 600 7200 400000; do ago $s; echo; done; "
        "for b in 812000 11000000 1400000000; do human_size $b; echo; done; "
        "took 12; echo; took 100"
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        "just now",
        "10 minutes ago",
        "2 hours ago",
        "5 days ago",
        "812 KB",
        "11 MB",
        "1.4 GB",
        "12s",
        "1m 40s",
    ]


def test_rows_line_up_and_only_what_is_wanting_is_counted() -> None:
    done = _run(
        'row Service running good; row Memory "140 MB"; row Nightly "not scheduled" poor; '
        'row Answers "nothing answered" bad; echo "${#ISSUES[@]}: ${ISSUES[*]}"'
    )
    lines = done.stdout.splitlines()
    assert lines[0] == "  ✓ Service      running"
    assert lines[1] == "    Memory       140 MB"
    assert lines[2].startswith("  ! Nightly      not scheduled")
    assert lines[3].startswith("  ✗ Answers      nothing answered")
    assert lines[4] == "2: Nightly: not scheduled Answers: nothing answered"


def _backups(tmp_path: Path, cron: str, *ages_hours: float):
    folder = tmp_path / "backups"
    folder.mkdir(exist_ok=True)
    for n, hours in enumerate(ages_hours):
        made = folder / f"familydb-2026092{n}031500.sqlite3"
        made.write_bytes(b"x" * 2_000_000)
        then = time.time() - hours * 3600
        os.utime(made, (then, then))
    stubs = f'as_root() {{ "$@"; }}\ncrontab() {{ printf %s "{cron}"; }}\n'
    return _run(
        stubs + 'status_backups; echo "issues=${#ISSUES[@]}"',
        "status_backups",
        BACKUP_DIR=str(folder),
        SERVICE_USER="familydb",
    )


def test_backups_say_how_old_the_newest_is_and_how_many_are_kept(tmp_path) -> None:
    done = _backups(tmp_path, "15 3 * * * run # familydb-maintain-backup", 9, 33)
    assert done.returncode == 0, done.stderr
    assert "✓ Newest       9 hours ago" in done.stdout
    assert "Kept         2 in" in done.stdout and "4 MB together" in done.stdout
    assert "✓ Nightly      every night at 03:15" in done.stdout
    assert done.stdout.rstrip().endswith("issues=0")


def test_a_stale_backup_and_no_schedule_want_a_look(tmp_path) -> None:
    done = _backups(tmp_path, "", 80)
    assert "! Newest       3 days ago" in done.stdout
    assert "! Nightly      not scheduled" in done.stdout
    assert "schedule-backups" in done.stdout
    assert done.stdout.rstrip().endswith("issues=2")


def test_no_backups_at_all_is_the_worst_of_it(tmp_path) -> None:
    done = _backups(tmp_path, "")
    assert "✗ Newest       none in" in done.stdout
    assert "take one now" in done.stdout


def test_the_page_says_where_it_is_and_whether_https_stands(tmp_path) -> None:
    (tmp_path / ".env").write_text("WEB_PORT=8080\nWEB_DOMAIN=family.example.com\n")
    stubs = (
        f'TARGET="{tmp_path}"; DOCKER_MODE=0\n'
        'as_root() { "$@"; }\nhave() { true; }\n'
        'systemctl() { printf %s "${CADDY:-active}"; }\n'
    )
    done = _run(stubs + "status_page", "status_page")
    assert "Address      https://family.example.com/" in done.stdout
    assert "✓ HTTPS        Caddy on port 443, passing the page on to 8080" in done.stdout
    down = _run(stubs + "status_page", "status_page", CADDY="inactive")
    assert "✗ HTTPS        Caddy is inactive" in down.stdout

    (tmp_path / ".env").write_text("WEB_PORT=8080\nWEB_HOST=0.0.0.0\n")
    bare = _run(stubs + "this_address() { printf 203.0.113.7; }\nstatus_page", "status_page")
    assert "! Address      http://203.0.113.7:8080/, without HTTPS" in bare.stdout
