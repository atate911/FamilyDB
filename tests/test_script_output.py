"""What `maintain.sh` shows a person, and the layout helpers in lib/common.sh behind it.

The look is for the eye and may change, but what a person reads off it may not: a plan numbered
and said before anything is done, a verdict, the facts a person needs to act, every warning said
again at the end, a failure that says what to type, and no escape codes in a log or a pipe.
Runs the real scripts, and cuts functions out of lib/common.sh, with nothing here touching a server.
"""

# ruff: noqa: E501  (shell snippets, written as a person would type them)

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(not BASH or os.name == "nt", reason="needs bash")

ESCAPE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
LIB = (
    "set -euo pipefail\n"
    f'. "{ROOT}/scripts/lib/common.sh"\n'
    "LOG_FILE=''\n"  # no transcript: nothing here writes outside the test
)


def _lib(code: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, "-c", LIB + code],
        cwd=ROOT,
        env={**os.environ, "NO_COLOR": "1", "COLUMNS": "80", "LC_ALL": "C.UTF-8", **env},
        capture_output=True,
        text=True,
        timeout=60,
    )


def _fake_server(tmp_path: Path, *, backups: int = 0) -> tuple[Path, dict[str, str]]:
    """An install the script will take for one: its checkout, a database, and stand-ins for the
    things that would otherwise reach for root, systemd, cron or the network."""
    target = tmp_path / "install"
    (target / "data").mkdir(parents=True)
    (target / "backups").mkdir()
    (target / ".env").write_text("WEB_ENABLED=true\n")
    shutil.copytree(ROOT / "scripts", target / "scripts")
    (target / "pyproject.toml").write_text('[project]\nname = "familydb"\n')
    with closing(sqlite3.connect(target / "data" / "familydb.sqlite3")) as conn:
        conn.execute("create table members (id integer primary key)")
        conn.commit()
    for number in range(backups):
        (target / "backups" / f"familydb-2026010{number}.sqlite3").write_text("x")
    program = target / ".venv" / "bin" / "familydb"
    program.parent.mkdir(parents=True)
    program.write_text(
        f"#!{sys.executable}\n"
        "import sqlite3, sys\n"
        "import os\n"
        "if sys.argv[1:2] == ['doctor']:\n"
        "    print(os.environ.get('FAKE_DOCTOR', '✓ settings: loaded\\n\\nEverything is set up.'))\n"
        "if sys.argv[1:3] == ['db', 'backup']:\n"
        "    with sqlite3.connect('data/familydb.sqlite3') as source:\n"
        "        target = sqlite3.connect(sys.argv[3]); source.backup(target); target.close()\n"
    )
    program.chmod(0o755)
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "sudo").write_text(
        '#!/bin/sh\nwhile [ "${1#-}" != "$1" ]; do shift; [ "$1" = root ] && shift; done\nexec "$@"\n'
    )
    (stubs / "crontab").write_text("#!/bin/sh\nexit 1\n")
    (stubs / "curl").write_text("#!/bin/sh\nprintf 'ok\\n200'\n")
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    env = {
        "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
        "NO_COLOR": "1",
        "COLUMNS": "80",
        # Whatever this machine runs as a service is none of the test's business.
        "FAMILYDB_SERVICE_UNIT": str(tmp_path / "no-such.service"),
    }
    return target, env


def _maintain(target: Path, env: dict[str, str], *args: str, tty: bool = False):
    command = [
        BASH,
        str(target / "scripts" / "maintain.sh"),
        *args,
        "--target",
        str(target),
        "--user",
        "root",
    ]
    return subprocess.run(
        command,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


# -- the help


def test_the_help_groups_commands_by_what_they_do_to_the_install() -> None:
    done = subprocess.run(
        [BASH, "scripts/maintain.sh", "--help"],
        cwd=ROOT,
        env={**os.environ, "NO_COLOR": "1"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    text = done.stdout
    headings = [
        text.index(h) for h in ("Look at it", "Keep it safe", "Change it", "Options", "Examples")
    ]
    assert headings == sorted(headings)
    look, safe, change = (text[headings[i] : headings[i + 1]] for i in range(3))
    assert all(f"\n  {name} " in look for name in ("status", "check", "logs"))
    assert all(f"\n  {name} " in safe for name in ("backup", "restore", "schedule-backups"))
    assert all(
        f"\n  {name} " in change for name in ("upgrade", "restart", "https", "port", "password")
    )
    assert not ESCAPE.search(text)


def test_the_help_has_colour_on_a_terminal_and_none_in_a_pipe() -> None:
    forced = subprocess.run(
        [BASH, "scripts/maintain.sh", "--help"],
        cwd=ROOT,
        env={**os.environ, "FORCE_COLOR": "1", "NO_COLOR": ""},
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout
    assert "\x1b[1mChange it\x1b[0m" in forced  # a heading is bold
    assert "\x1b[36mupgrade\x1b[0m" in forced  # a command is cyan
    refused = subprocess.run(
        [BASH, "scripts/maintain.sh", "--help"],
        cwd=ROOT,
        env={**os.environ, "FORCE_COLOR": "1", "NO_COLOR": "1"},
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout
    assert not ESCAPE.search(refused)  # NO_COLOR wins


# -- status


def test_status_leads_with_a_verdict_and_ends_with_what_to_do(tmp_path) -> None:
    target, env = _fake_server(tmp_path)
    done = _maintain(target, env, "status")
    assert done.returncode == 0, done.stdout + done.stderr
    out = done.stdout
    assert not ESCAPE.search(out + done.stderr)
    assert re.search(
        r"^╔═\[■\]═ FamilyDB ═ Status ═+ .+ ═╗$", out, re.M
    )  # the title bar says what, and where
    # No backup and no schedule: not well, and it says how to put that right, command first.
    assert "Running, with 2 things to look at" in out  # the backup and its schedule
    assert re.search(r"^  ! Last backup +none yet", out, re.M)
    attention = out[out.index("Needs attention") :]
    assert re.search(r"sudo \S*maintain\.sh backup +# take one now", attention)
    assert "schedule-backups" in attention
    # The labels line up, whatever their length: every value starts in the same column.
    starts = {
        re.match(r"^ {2}(?:[✓!✗] | {2})(?:Version|Database|Last backup|Disk) +", line).end()
        for line in out.splitlines()
        if re.match(r"^ {2}(?:[✓!✗] | {2})(?:Version|Database|Last backup|Disk) ", line)
    }
    assert len(starts) == 1


def test_status_with_a_fresh_backup_and_nothing_wrong_is_all_well(tmp_path) -> None:
    target, env = _fake_server(tmp_path)
    fresh = target / "backups" / "familydb-20990101.sqlite3"
    fresh.write_text("x")
    # Root's crontab carries the nightly line, as schedule-backups writes it.
    (tmp_path / "stubs" / "crontab").write_text(
        "#!/bin/sh\necho '15 3 * * * /bin/true # familydb-maintain-backup'\n"
    )
    done = _maintain(target, env, "status")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Running, and all is well" in done.stdout or "Needs attention" not in done.stdout, (
        done.stdout
    )
    assert re.search(r"✓ Last backup +just now", done.stdout)
    assert re.search(r"✓ Schedule +nightly at 03:15", done.stdout)


def test_a_backup_older_than_the_upkeep_job_tolerates_is_called_stale(tmp_path) -> None:
    target, env = _fake_server(tmp_path, backups=1)
    old = target / "backups" / "familydb-20260100.sqlite3"
    os.utime(old, (1_700_000_000, 1_700_000_000))
    done = _maintain(target, env, "status")
    assert re.search(r"! Last backup .*older than 36 hours", done.stdout)
    assert "nightly one may have stopped" in " ".join(done.stdout.split())


# -- a command that changes something says so first, and last


def test_a_dry_run_says_it_changed_nothing_and_changes_nothing(tmp_path) -> None:
    target, env = _fake_server(tmp_path)
    done = _maintain(target, env, "backup", "--dry-run")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "[ DRY RUN ]" in done.stdout
    assert "[dry run] would back up the database" in done.stdout
    assert "Dry run finished: nothing was changed" in done.stdout
    assert list((target / "backups").iterdir()) == []


def test_a_backup_ends_with_where_it_is_and_how_to_fetch_it(tmp_path) -> None:
    if os.geteuid() != 0:
        pytest.skip("the backup is handed to the service account, which takes root to do")
    target, env = _fake_server(tmp_path)
    done = _maintain(target, env, "backup")
    assert done.returncode == 0, done.stdout + done.stderr
    out = done.stdout
    assert [p.suffix for p in (target / "backups").iterdir()] == [".sqlite3"]
    assert re.search(r"\[ OK \] Backed up the database \(\S+\) to \S*familydb-\d+\.sqlite3", out)
    assert "To fetch a copy off this machine" in out
    assert "scp " in out
    assert "SQLite's online backup" not in out  # how it works is not what this run is about
    assert not ESCAPE.search(out + done.stderr)


def test_a_refused_question_changes_nothing_and_says_so(tmp_path) -> None:
    target, env = _fake_server(tmp_path)
    done = _maintain(target, env, "schedule-backups")  # nobody at the terminal to say yes
    assert done.returncode == 0
    out = done.stdout
    asked = done.stdout + done.stderr  # the question itself goes to stderr when nobody can answer
    assert re.search(
        r"Schedule +every night at 03:15", out
    )  # what this run would set up, not how cron works
    assert out.index("Schedule") < asked.index("Add the nightly backup to the crontab?")
    assert "There is no terminal here to answer, so the answer is no." in asked
    assert "Nothing was changed." in out


def _asked(default: str, answer: bytes) -> tuple[int, str]:
    """Run approve at a terminal, type ANSWER, and say what it decided (0 yes, 1 no) and showed."""
    master, slave = os.openpty()
    process = subprocess.Popen(
        [BASH, "-c", LIB + f'approve "Go on?" {default} && exit 0 || exit 1'],
        env={**os.environ, "NO_COLOR": "1", "LC_ALL": "C.UTF-8"},
        stdin=slave,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        text=True,
    )
    os.close(slave)
    os.write(master, answer)
    _, shown = process.communicate(timeout=30)
    os.close(master)
    return process.returncode, shown


@pytest.mark.parametrize(
    ("default", "typed", "decided"),
    [
        ("yes", b"\n", 0),  # Enter takes the default: what is done every week is a yes
        ("yes", b"n\n", 1),
        ("yes", b"y\n", 0),
        ("no", b"\n", 1),  # what cannot be undone is a no until somebody says otherwise
        ("no", b"y\n", 0),
        ("no", b"maybe\n", 1),  # anything else is not yes
    ],
)
def test_enter_takes_the_default_and_a_default_of_no_is_for_what_cannot_be_undone(
    default, typed, decided
) -> None:
    assert _asked(default, typed)[0] == decided


def test_the_question_shows_which_answer_enter_gives() -> None:
    assert "[Y/n]" in _asked("yes", b"\n")[1]
    assert "[y/N]" in _asked("no", b"\n")[1]


def test_saying_yes_on_the_command_line_does_not_ask_and_does_not_chatter() -> None:
    done = _lib('ASSUME_YES=1; approve "Go on?" no && echo went')
    assert done.stdout == "went\n" and done.stderr == ""


# -- the layout helpers


def test_the_installers_plan_is_numbered_with_its_reasons_and_what_stays() -> None:
    done = _lib(
        'plan_item "Fetch the code" "it is what the bot runs"\n'
        'plan_item "Restart" "so it takes effect"\n'
        'plan_untouched ".env"\n'
        'show_plan "What this does"\n'
    )
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert "What this does" in lines
    assert any(re.fullmatch(r"  1  Fetch the code", line) for line in lines)
    assert any(re.fullmatch(r"  2  Restart", line) for line in lines)
    assert "     it is what the bot runs" in lines
    assert "    · .env" in lines


def test_every_warning_is_said_again_at_the_end_and_counted() -> None:
    done = _lib(
        'warn "disk is nearly full"; warn "one step failed, carrying on"\n'
        'finish ok "Upgraded"\nkv Version "v1"\nrecap\n'
    )
    assert done.returncode == 0, done.stderr
    assert "[WARN] Upgraded, with 2 warnings" in done.stdout
    assert done.stdout.index("Version") < done.stdout.index(
        "Warnings"
    )  # facts, then what went wrong
    recap = done.stdout[done.stdout.index("Warnings") :]
    assert "disk is nearly full" in recap and "one step failed, carrying on" in recap
    clean = _lib('finish ok "Upgraded"\nrecap\n')
    assert "[ OK ] Upgraded" in clean.stdout and "Warnings" not in clean.stdout


def test_a_failed_run_is_never_called_a_success_and_a_dry_run_never_one_that_ran() -> None:
    assert "[FAIL] Stopped" in _lib('finish bad "Stopped"\n').stdout
    dry = _lib('finish ok "Upgraded"\n', DRY_RUN="1")
    assert "Dry run finished: nothing was changed" in dry.stdout and "Upgraded" not in dry.stdout


def test_facts_are_laid_out_in_a_column_with_a_mark_that_does_not_depend_on_colour() -> None:
    done = _lib(
        'kv "Version" "v1"\nkv "Last backup" "3 hours ago" ok\nkv "Disk" "full" bad\nkv "Schedule" "none" warn\n'
    )
    lines = done.stdout.splitlines()
    assert lines == [
        "    Version      v1",
        "  ✓ Last backup  3 hours ago",
        "  ✗ Disk         full",
        "  ! Schedule     none",
    ]
    ascii_only = _lib(
        'kv "Disk" "full" bad\nkv "Last backup" "3 hours ago" ok\n', FAMILYDB_ASCII="1"
    )
    assert ascii_only.stdout.splitlines() == [
        "  x Disk         full",
        "  + Last backup  3 hours ago",
    ]


@pytest.mark.parametrize(
    ("seconds", "said"),
    [(5, "5s"), (65, "1m 05s"), (7500, "2h 05m"), (183_600, "2d 3h")],
)
def test_a_length_of_time_is_said_in_the_shortest_words_that_are_exact(seconds, said) -> None:
    assert _lib(f"fmt_secs {seconds}").stdout == said


@pytest.mark.parametrize(
    ("seconds", "said"),
    [(10, "just now"), (600, "10 min ago"), (10_800, "3 hours ago"), (259_200, "3 days ago")],
)
def test_how_long_ago_is_said_as_a_person_would(seconds, said) -> None:
    assert _lib(f"ago {seconds}").stdout == said


def test_a_long_reason_is_broken_at_words_and_a_long_path_is_not_cut() -> None:
    path = "/srv/" + "x" * 90
    done = _lib(
        f'plan_item "Step" "copies it over {path} and then sets the owner and mode"; show_plan',
        COLUMNS="60",
    )
    lines = done.stdout.splitlines()
    assert path in "".join(line.strip() for line in lines)  # whole on one line
    assert any(path in line for line in lines)
    assert all(len(line) <= 60 or path in line for line in lines)


# -- what a failure says


def test_a_failure_names_what_to_type_and_what_it_cost_in_words_a_person_can_follow() -> None:
    done = _lib(
        'on_failure_hint "The upgrade stopped part-way."$\'\\n\'"To go back:"$\'\\n\'"  sudo git checkout abc     # v1"\n'
        'again_hint "finish the upgrade: sudo bash maintain.sh upgrade"\n'
        'die "could not fetch" "What to try:" "      sudo git fetch origin" "A sentence."\n'
    )
    assert done.returncode == 1
    err = done.stderr
    assert "✗ could not fetch" in err
    assert "      sudo git fetch origin" in err
    assert "To go back:" in err and "sudo git checkout abc" in err
    assert "When that is sorted, finish the upgrade: sudo bash maintain.sh upgrade" in err
    assert not ESCAPE.search(err)


def test_a_failure_colours_commands_but_only_where_stderr_is_a_terminal() -> None:
    done = _lib(
        'die "stopped" "  sudo systemctl status familydb     # why"\n', FORCE_COLOR="1", NO_COLOR=""
    )
    assert "\x1b[36m  sudo systemctl status familydb\x1b[0m" in done.stderr
    assert "\x1b[2m     # why\x1b[0m" in done.stderr  # its comment is dim


def test_the_doctors_report_is_counted_and_a_failure_only_view_hides_the_rest() -> None:
    report = (
        "▸ Settings\n✓ settings: loaded\n! telegram: no token\n    → set one\n"
        "▸ Model\n✗ model key: none\n    → add one\n· note: skipped\n\nIt is not set up."
    )
    done = _lib(
        f"show_doctor failures '{report}'; echo \"$DOCTOR_FINE $DOCTOR_WARN $DOCTOR_BAD|$DOCTOR_VERDICT\""
    )
    assert done.returncode == 0, done.stderr
    out = done.stdout
    assert re.search(r"✗ model key +none", out) and "→ add one" in out
    assert "telegram" not in out and "settings" not in out
    assert out.strip().endswith("1 1 1|It is not set up.")
    everything = _lib(f"show_doctor all '{report}'")
    assert "▸ Settings" in everything.stdout and "▸ Model" in everything.stdout
    assert re.search(r"✓ settings +loaded", everything.stdout)
    assert re.search(r"! telegram +no token", everything.stdout)
    assert re.search(r"○ note +skipped", everything.stdout)
    folded = _lib(f"show_doctor problems '{report}'")
    assert (
        "settings" in folded.stdout and "loaded" not in folded.stdout
    )  # fine rows are folded away


def test_the_report_names_the_first_thing_to_fix_and_counts_in_one_bar() -> None:
    done = _lib(
        "doctor_begin; doctor_section A; doctor_row ok one fine; doctor_row bad two broken 'do this';"
        " doctor_row bad three also; doctor_row warn four hmm; doctor_row skip five -;"
        " doctor_summary"
    )
    assert done.returncode == 0, done.stderr
    assert "Checked 5" in done.stdout
    assert (
        "1✓" in done.stdout and "1!" in done.stdout and "2✗" in done.stdout and "1○" in done.stdout
    )
    start = done.stdout.split("Start here")[1]
    assert "two: broken" in start and "do this" in start and "three" not in start


def test_a_name_is_reported_once_and_the_first_word_wins() -> None:
    done = _lib(
        "doctor_begin; doctor_row ok service 'the machine says up';"
        " doctor_feed '✗ service: the program says down'; doctor_show all; echo \"$DOCTOR_FINE $DOCTOR_BAD\""
    )
    assert "the machine says up" in done.stdout and "the program says down" not in done.stdout
    assert done.stdout.strip().endswith("1 0")


def test_the_fine_sections_fold_to_a_line_that_still_says_what_was_looked_at() -> None:
    done = _lib(
        "doctor_begin; doctor_section Files; doctor_row ok 'service account' x; doctor_row ok '.env' y;"
        " doctor_section Git; doctor_row ok checkout z; doctor_row warn 'working tree' w 'git diff';"
        " doctor_show problems"
    )
    assert re.search(r"✓ Files +service account · \.env", done.stdout)
    assert "▸ Git" in done.stdout and re.search(r"! working tree +w", done.stdout)
    assert "1 fine: checkout" in done.stdout


# -- a step at a terminal shows it is working, and elsewhere says nothing until it is done


def test_a_step_at_a_terminal_redraws_one_line_and_leaves_the_tick() -> None:
    pty = pytest.importorskip("pty")
    master, slave = pty.openpty()
    code = LIB + '_live_ok() { return 0; }\nstep "Waiting on something slow" sleep 1\n'
    process = subprocess.Popen(
        [BASH, "-c", code],
        cwd=ROOT,
        env={**os.environ, "TERM": "xterm", "NO_COLOR": "1", "COLUMNS": "80"},
        stdout=slave,
        stderr=slave,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    os.close(slave)
    chunks = []
    while True:
        try:
            data = os.read(master, 4096)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
    process.wait(timeout=30)
    os.close(master)
    shown = b"".join(chunks).decode("utf-8", "replace")
    assert process.returncode == 0
    assert shown.count("\r") >= 3  # redrawn in place, not a line a time
    assert "Waiting on something slow" in shown
    assert (
        shown.rstrip().splitlines()[-1].endswith("✓ Waiting on something slow")
    )  # and what is left is the tick


def test_interrupting_a_step_stops_the_command_and_leaves_no_line_drawing() -> None:
    """Ctrl-C reaches what the step runs, as it always did, and nothing is left running behind."""
    import signal
    import time

    if not shutil.which("setsid"):
        pytest.skip("needs setsid, to give the script a terminal of its own to interrupt")
    code = LIB + (
        "_live_ok() { return 0; }\n"
        "enable_failure_reporting\n"
        'step "Waiting on something very slow" sleep 31.7\n'
    )
    master, slave = os.openpty()
    process = subprocess.Popen(
        ["setsid", "--ctty", "--wait", BASH, "-c", code],
        env={**os.environ, "TERM": "xterm", "NO_COLOR": "1", "COLUMNS": "80", "LC_ALL": "C.UTF-8"},
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)
    time.sleep(1.0)
    os.write(master, b"\x03")  # what the terminal turns into an interrupt for what is running
    shown = b""
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            data = os.read(master, 4096)
        except OSError:
            break
        if not data:
            break
        shown += data
    process.wait(timeout=10)
    os.close(master)
    assert process.returncode in (128 + signal.SIGINT, -signal.SIGINT)  # as it ended before
    time.sleep(0.5)
    running = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    assert "sleep 31.7" not in [line.strip() for line in running.splitlines()], (
        "the command was left running"
    )
    assert shown.endswith(b"\r\x1b[K")  # the line that was drawing itself is wiped, not left


def test_a_step_in_a_pipe_prints_only_its_result() -> None:
    done = _lib('step "Waiting on something slow" sleep 0.2', TERM="xterm")
    assert done.stdout == "✓ Waiting on something slow\n"
    assert "\r" not in done.stdout


def test_a_step_that_failed_says_what_it_ran_and_what_it_said() -> None:
    done = _lib("step \"Stopping\" bash -c 'echo no space left on device; exit 3'")
    assert done.returncode == 3
    assert "✗ Stopping — failed" in done.stderr
    assert "exit code: 3" in done.stderr and "no space left on device" in done.stderr
    assert "The disk is full" in done.stderr  # and what that means


def test_the_title_bar_fills_the_width_whatever_the_width_and_keeps_the_right_end() -> None:
    for width in (40, 60, 80, 120):
        bar = _lib(
            'banner "Upgrade" "/opt/familydb ${S_DOT} systemd service (familydb)"',
            COLUMNS=str(width),
        ).stdout.strip()
        shown = min(max(width, 40), 88)
        assert len(bar) == shown, (width, bar)
        assert bar.startswith("╔═[■]═ FamilyDB ═ Upgrade ═") and bar.endswith("═╗")
    plain = _lib('banner "Upgrade"', FAMILYDB_ASCII="1", COLUMNS="60").stdout.strip()
    assert (
        plain.startswith("+=[#]= FamilyDB = Upgrade =")
        and plain.endswith("=+")
        and len(plain) == 60
    )


def test_a_command_exits_with_what_its_last_line_said(tmp_path) -> None:
    target, env = _fake_server(tmp_path)
    well = _maintain(target, env, "status")
    assert well.returncode == 0, well.stdout + well.stderr
    # The page says it is not well: a monitor reads that from the exit status, not from the words.
    (tmp_path / "stubs" / "curl").write_text(
        "#!/bin/sh\nprintf 'the database does not answer\\n503'\n"
    )
    sick = _maintain(target, env, "status")
    assert sick.returncode == 1, sick.stdout + sick.stderr
    assert "does not answer" in sick.stdout
    assert _lib('finish bad "x" >/dev/null; exit "$FINISH_BAD"').returncode == 1
    assert _lib('finish warn "x" >/dev/null; exit "$FINISH_BAD"').returncode == 0


def _on_a_terminal(code: str, **env: str) -> str:
    """What a script prints when its output is a terminal, with nothing else changed."""
    master, slave = os.openpty()
    process = subprocess.Popen(
        [BASH, "-c", LIB + code],
        env={
            **os.environ,
            "TERM": "xterm",
            "NO_COLOR": "",
            "COLUMNS": "80",
            "LC_ALL": "C.UTF-8",
            **env,
        },
        stdin=subprocess.DEVNULL,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)
    shown = b""
    while True:
        try:
            data = os.read(master, 4096)
        except OSError:
            break
        if not data:
            break
        shown += data
    process.wait(timeout=30)
    os.close(master)
    return shown.decode("utf-8", "replace")


def test_a_pull_request_number_is_a_link_on_a_terminal_and_plain_text_anywhere_else() -> None:
    link = 'hyperlink "https://github.com/o/r/pull/64" "#64"'
    shown = _on_a_terminal(link)
    assert "\x1b]8;;https://github.com/o/r/pull/64\x07#64\x1b]8;;\x07" in shown
    assert _on_a_terminal(link, FAMILYDB_NO_LINKS="1").strip() == "#64"
    assert _lib(link).stdout == "#64"  # a pipe, a log, a mail
    assert _lib('hyperlink "" "#64"').stdout == "#64"  # no address to link to


@pytest.mark.parametrize(
    ("remote", "web"),
    [
        ("git@github.com:atate911/FamilyDB.git", "https://github.com/atate911/FamilyDB"),
        ("https://github.com/atate911/FamilyDB", "https://github.com/atate911/FamilyDB"),
        ("https://github.com/atate911/FamilyDB.git/", "https://github.com/atate911/FamilyDB"),
        ("ssh://git@github.com/atate911/FamilyDB.git", "https://github.com/atate911/FamilyDB"),
        ("/srv/git/familydb.git", ""),
        ("https://git.example.org/o/r.git", ""),
    ],
)
def test_where_a_remote_can_be_read_on_the_web_is_worked_out_and_otherwise_left_alone(
    remote, web
) -> None:
    assert _lib(f'repo_web_base "{remote}"').stdout == web


def test_the_verdict_is_a_badge_that_reads_without_colour() -> None:
    colour = _lib(
        "_verdict_badge warn; _verdict_badge bad; _verdict_badge ok", FORCE_COLOR="1", NO_COLOR=""
    )
    assert "\x1b[1;30;43m WARN \x1b[0m" in colour.stdout
    assert "\x1b[1;37;41m FAIL \x1b[0m" in colour.stdout
    assert "\x1b[1;30;42m  OK  \x1b[0m" in colour.stdout
    assert (
        _lib("_verdict_badge ok; _verdict_badge warn; _verdict_badge bad").stdout
        == "[ OK ][WARN][FAIL]"
    )


def test_a_terminal_that_cannot_draw_the_glyphs_is_given_plain_ones_unasked() -> None:
    shown = _on_a_terminal(
        'banner "Upgrade"; ok "Done"', LC_ALL="C", FAMILYDB_UNICODE="", NO_COLOR="1"
    )
    assert "+=[#]= FamilyDB = Upgrade =" in shown and "+ Done" in shown
    assert "╔" not in shown and "✓" not in shown
    # A pipe is not asked: it is read somewhere that may well draw them.
    assert "╔═[■]═" in _lib('banner "Upgrade"', LC_ALL="C").stdout
    # And anyone can have either, whatever the locale says.
    assert "╔═[■]═" in _on_a_terminal(
        'banner "Upgrade"', LC_ALL="C", FAMILYDB_UNICODE="1", NO_COLOR="1"
    )


def _page_health(
    tmp_path: Path, env_file: str, curl: str = "ok\\n200"
) -> subprocess.CompletedProcess[str]:
    """maintain.sh's own page_health, cut out and run against an .env and a stand-in for curl."""
    script = (ROOT / "scripts/maintain.sh").read_text()
    functions = "".join(
        script[
            script.index(f"{name}() {{") : script.index("\n}\n", script.index(f"{name}() {{")) + 3
        ]
        for name in ("env_file_value", "page_health")
    )
    (tmp_path / ".env").write_text(env_file)
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "curl").write_text(f"#!/bin/sh\nprintf '{curl}'\n")
    (stub / "curl").chmod(0o755)
    return _lib(
        f'TARGET="{tmp_path}"; as_root() {{ "$@"; }}\n'
        + functions
        + "set +e; page_health; printf ' [%s]' \"$?\"",
        PATH=f"{stub}{os.pathsep}{os.environ['PATH']}",
    )


def test_a_page_that_is_off_is_not_asked_and_so_cannot_fail_an_upgrade(tmp_path) -> None:
    # WEB_ENABLED defaults to false: an install that never turned it on has no page to wait for.
    for env_file in ("", "WEB_ENABLED=false\n", "WEB_ENABLED=\n"):
        done = _page_health(tmp_path, env_file, curl="refused\\n000")
        assert done.stdout == "the web page is switched off [2]", (env_file, done.stdout)


def test_a_page_that_is_on_is_asked_and_what_it_says_is_believed(tmp_path) -> None:
    assert _page_health(tmp_path, "WEB_ENABLED=true\n").stdout == "ok [0]"
    assert _page_health(tmp_path, "WEB_ENABLED=True\nWEB_PORT=9090\n").stdout == "ok [0]"
    sick = _page_health(
        tmp_path, "WEB_ENABLED=yes\n", curl="the scheduled jobs have not run for 22 minutes\\n503"
    )
    assert sick.stdout == "the scheduled jobs have not run for 22 minutes [1]"
    # An error page of the web server's is markup, which says nothing: say the status instead.
    page = _page_health(tmp_path, "WEB_ENABLED=true\n", curl="<html>oops</html>\\n500")
    assert page.stdout == "the page answered with status 500 [1]"
