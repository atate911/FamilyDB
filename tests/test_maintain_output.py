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


# -- the upgrade ---------------------------------------------------------------------------------

UPGRADE = ("stage", "stage_done", "rule", "upgrade_summary")


def test_each_stage_fills_the_bar_and_is_timed() -> None:
    done = _run(
        'UP_STAGES=3; UP_STAGE=0; UP_STAGE_NAME=""; UP_TIMES=(); UP_HINT=""\n'
        'stage "Backing up" backup; ok "Backup written"; stage "Moving" code; stage_done\n'
        'echo "${UP_TIMES[*]}"',
        *UPGRADE,
    )
    assert done.returncode == 0, done.stderr
    lines = [line for line in done.stdout.splitlines() if line]
    assert lines[0] == "━━──── 1/3  Backing up"
    assert lines[1] == "      ✓ Backup written"  # a stage's steps sit under it
    assert lines[2] == "━━━━── 2/3  Moving"
    assert lines[3] == "backup 0 code 0"


def test_past_the_backup_a_failure_says_where_it_stopped_and_how_to_go_on() -> None:
    done = _run(
        'UP_STAGES=6; UP_STAGE=2; UP_STAGE_NAME=""; UP_TIMES=(); UP_HINT="Finish it."\n'
        'stage "Installing the libraries" libraries >/dev/null; echo "$HINT"',
        *UPGRADE,
    )
    assert done.stdout.strip() == "It stopped at 3/6, installing the libraries. Finish it."


def _summary(tmp_path: Path, **env: str):
    backup = tmp_path / "familydb-1.sqlite3"
    backup.write_bytes(b"x" * 3_000_000)
    stubs = (
        f'TARGET="{tmp_path}"; DOCKER_MODE=0; UP_COUNT=12; UP_NEWEST="A mic on the page"\n'
        "UP_MIGRATIONS=$'0035_wishes\\n0036_wording'; UP_DEPS=moved\n"
        'UP_TIMES=("backup 2" "libraries 40")\n'
        'as_root() { if [ "$1" = git ]; then echo v0.2.0; else "$@"; fi; }\n'
        "SECONDS=48; WARNINGS=${WARN_COUNT:-0}; PAGE_STATE=${PAGE_STATE:-answering}\n"
    )
    summary = f'upgrade_summary v0.1.0 main "{backup}" "${{CHECK:-0}}"'
    return _run(stubs + summary, *UPGRADE, **env)


def test_the_summary_says_what_happened_in_one_panel(tmp_path) -> None:
    done = _summary(tmp_path)
    assert done.returncode == 0, done.stderr
    said = done.stdout
    assert "╭─ Upgraded ─" in said
    assert "│  Now on     v0.2.0" in said
    assert "│  From       v0.1.0" in said
    assert "│  Changes    12, the newest: A mic on the page" in said
    assert "│  Database   2 migrations applied, 0035_wishes to 0036_wording" in said
    assert "│  Libraries  moved to the new locked versions" in said
    assert "(3 MB)" in said
    assert "│  Page       ✓ answering on port 8080" in said
    assert "│  Check      ✓ familydb doctor found nothing" in said
    assert "│  Took       48s  (backup 2s · libraries 40s)" in said
    assert "Warnings" not in said


def test_the_summary_turns_to_something_to_look_at(tmp_path) -> None:
    done = _summary(tmp_path, PAGE_STATE="silent", CHECK="1", WARN_COUNT="2")
    said = done.stdout
    assert "╭─ Upgraded, with something to look at ─" in said
    assert "│  Page       ✗ not answering on port 8080 yet" in said
    assert "│  Check      ✗ familydb doctor found something to fix" in said
    assert "│  Warnings   2, above" in said
