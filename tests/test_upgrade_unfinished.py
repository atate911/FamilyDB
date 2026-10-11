"""`maintain.sh upgrade` when it stops after moving the code, and when it is rerun.

The real cmd_upgrade (and the helpers beside it) is cut out of the script and run against a real
git remote and checkout in a temporary folder, with lib/common.sh's own failure reporting and the
parts that would touch a server (the service, the dependency install, the migration) replaced by
stubs that succeed or fail on request.
"""

# ruff: noqa: E501  (the harness is a shell script, written as a person would type it)

import os
import re
import shutil
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")

pytestmark = pytest.mark.skipif(
    not BASH or not shutil.which("git"), reason="bash and git required for shell integration"
)

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    # git 2.46 and later hand a commit's or a fetch's housekeeping to a background process that
    # holds .git/maintenance.lock for a moment after the command returns; a test that then removes
    # or inspects .git races it. Every git run here, by a test or by maintain.sh, keeps it in front.
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "maintenance.autoDetach",
    "GIT_CONFIG_VALUE_0": "false",
    "GIT_CONFIG_KEY_1": "gc.autoDetach",
    "GIT_CONFIG_VALUE_1": "false",
}

HARNESS = r"""
set -euo pipefail
. "$ROOT/scripts/lib/common.sh"
enable_failure_reporting
LEDGER_DIR="$WORK/ledger"
as_root() { "$@"; }
# Each stand-in says what it did on the screen and, because a step's output goes to the log and
# not the screen, in $WORK/sequence too, which is where the order of things is read from.
did() { echo "$1"; echo "$1" >> "$WORK/sequence"; }
take_backup() { did BACKUP; LAST_BACKUP="$WORK/backups/familydb-1.sqlite3"; }
stop_bot() { did STOPPING; }
start_bot() { did STARTING; }
retry() {
  did SYNC
  # FAIL_SYNC fails the first sync only: the one that puts the old packages back then works.
  if [ "${FAIL_SYNC:-0}" = 1 ] && [ ! -f "$WORK/sync-failed" ]; then
    touch "$WORK/sync-failed"
    die "Installing the dependencies failed"
  fi
}
SERVICE_UNIT="${FAMILYDB_SERVICE_UNIT:-/nonexistent/familydb.service}"
SERVICE_USER=familydb
service_installed() { [ -f "$SERVICE_UNIT" ]; }
service_active() { [ "${SERVICE_UP:-1}" = 1 ]; }
systemctl() { did "SYSTEMCTL $*"; }
docker() {
  did "DOCKER $*"
  case "$*" in
    *" ps "*) echo "bot ${CONTAINER_STATE:-running}" ;;
    *"images -q"*) echo abc123 ;;
    *" build"*) [ "${FAIL_DOCKER_BUILD:-0}" = 0 ] || return 1 ;;
  esac
}
familydb_cmd() {
  case "$1" in
    doctor)
      seen="$(cat "$WORK/doctor-count" 2>/dev/null || echo 0)"
      echo $((seen + 1)) > "$WORK/doctor-count"
      if [ "$seen" = 0 ]; then printf '%b' "${DOCTOR_BEFORE-✓ settings: loaded\n\nEverything is set up.\n}"
      else printf '%b' "${DOCTOR_AFTER-✓ settings: loaded\n\nEverything is set up.\n}"; fi ;;
    db)
      did MIGRATE
      [ "${FAIL_MIGRATE:-0}" = 0 ] || return 1
      python3 -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('insert into schema_version values (?, ?)', (int(sys.argv[2]), 'now')); c.commit()" "$DB" "$NEWEST" ;;
  esac
}
"""


LOCK = """version = 1

[[package]]
name = "familydb"
version = "0.3.0"

[[package]]
name = "anthropic"
version = "{anthropic}"

{extra}"""


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=GIT_ENV, check=True, capture_output=True, text=True
    ).stdout.strip()


class Server:
    """A remote with two commits, a checkout one behind it, and a database one migration behind."""

    def __init__(self, tmp: Path, *, rich: bool = False, released: bool = False):
        self.tmp = tmp
        remote = tmp / "remote.git"
        seed = tmp / "seed"
        _git(tmp, "init", "-q", "--bare", "-b", "main", str(remote))
        _git(tmp, "init", "-q", "-b", "main", str(seed))
        heading = "v9.9.9 — beta (2026-10-09)" if released else "v9.9.9 — in progress"
        (seed / "CHANGELOG.md").write_text(f"# Changelog\n\n## {heading}\n\n### New\n\n")
        migrations = seed / "src/familydb/store/migrations"
        migrations.mkdir(parents=True)
        (migrations / "0001_first.sql").write_text("select 1;\n")
        if rich:
            (seed / "uv.lock").write_text(LOCK.format(anthropic="1.0.0", extra=""))
            (seed / ".env.example").write_text("# Notes\nPROVIDER=openai\n# WEB_HOST=\n")
            (seed / "deploy").mkdir()
            (seed / "deploy/familydb.service").write_text("[Service]\nUser=familydb\n")
        _git(seed, "add", "-A")
        _git(seed, "commit", "-q", "-m", "one")
        if released:
            _git(seed, "tag", "v9.9.9")
        _git(seed, "remote", "add", "origin", str(remote))
        _git(seed, "push", "-q", "--tags", "origin", "main")
        self.target = tmp / "target"
        _git(tmp, "clone", "-q", str(remote), str(self.target))
        self.before = _git(self.target, "rev-parse", "HEAD")
        (migrations / "0002_second.sql").write_text("select 2;\n")
        if rich:
            (seed / "uv.lock").write_text(
                LOCK.format(
                    anthropic="1.1.0", extra='[[package]]\nname = "newthing"\nversion = "2.0.0"\n'
                )
            )
            (seed / ".env.example").write_text(
                "# Notes\nPROVIDER=openai\n# WEB_HOST=\nDIGEST_SWITCH=true\n"
            )
            (seed / "deploy/familydb.service").write_text("[Service]\nUser=familydb\nNice=5\n")
            changelog = (seed / "CHANGELOG.md").read_text()
            (seed / "CHANGELOG.md").write_text(
                changelog + "- **The digest can be switched off.** A setting.\n"
            )
        _git(seed, "add", "-A")
        _git(seed, "commit", "-q", "-m", "A switch for the digest (#64)" if rich else "two")
        _git(seed, "push", "-q", "origin", "main")
        self.db = tmp / "live.sqlite3"
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("create table schema_version (version integer primary key, applied_at)")
            conn.execute("insert into schema_version values (1, 'then')")
            conn.commit()
        self.marker = tmp / "ledger/upgrade-pending"
        self.remote = remote
        self.seed = seed

    def sequence(self) -> list[str]:
        """What the stand-ins did, in order, whether it reached the screen or only the log."""
        path = self.tmp / "sequence"
        return path.read_text().splitlines() if path.exists() else []

    def version(self) -> int:
        with closing(sqlite3.connect(self.db)) as conn:
            return conn.execute("select max(version) from schema_version").fetchone()[0]

    def upgrade(self, **env: str):
        script = (ROOT / "scripts/maintain.sh").read_text()
        start = script.index("# An upgrade that has moved the code")
        begin = script.index("cmd_upgrade() {")
        region = script[start : script.index("\n}\n", begin) + 3]
        path = self.tmp / "upgrade.sh"
        path.write_text(HARNESS + region + "\ncmd_upgrade\n", newline="\n")
        return subprocess.run(
            [BASH, path.as_posix()],
            env={
                **GIT_ENV,
                "ROOT": ROOT.as_posix(),
                "WORK": self.tmp.as_posix(),
                "TARGET": self.target.as_posix(),
                "DB": self.db.as_posix(),
                "DOCKER_MODE": "0",
                "DRY_RUN": "0",
                "ASSUME_YES": "1",
                "BACKUP_DIR": (self.tmp / "backups").as_posix(),
                "NEWEST": "2",
                "NO_COLOR": "1",
                "GITHUB_TOKEN": "",  # one in the environment is a warning of its own
                **env,
            },
            cwd=self.tmp,
            capture_output=True,
            text=True,
        )


def test_the_bot_is_stopped_before_the_code_moves_and_the_way_back_is_printed_before_it(tmp_path):
    """A running bot would pick up new files as they land; a backup taken once it is stopped
    misses nothing said to it meanwhile; and the way back is on the screen before the code moves."""
    server = Server(tmp_path)
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    command = f"checkout --quiet --detach {server.before}"
    assert "familydb-1.sqlite3" in out
    assert out.index("STOPPING") < out.index("BACKUP") < out.index(command) < out.index("SYNC")
    assert server.sequence() == ["STOPPING", "BACKUP", "SYNC", "MIGRATE", "STARTING"]
    assert server.version() == 2
    assert not server.marker.exists()


def test_a_failure_before_the_migrations_puts_the_old_code_back_and_starts_the_bot_again(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade(FAIL_SYNC="1")
    assert result.returncode != 0
    assert _git(server.target, "rev-parse", "HEAD") == server.before
    assert "Putting things back" in result.stderr
    assert "the code is back on" in result.stderr
    assert "its packages as they were" in result.stderr
    assert "FamilyDB is running again" in result.stderr
    assert server.sequence()[-1] == "STARTING"
    assert not server.marker.exists(), "nothing is left half-done to finish"
    assert server.version() == 1
    assert "try the upgrade again" in result.stderr
    assert "Nothing in the database has changed" in result.stderr


def test_on_docker_the_image_is_built_while_the_old_one_still_runs(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade(DOCKER_MODE="1")
    assert result.returncode == 0, result.stdout + result.stderr
    done = server.sequence()
    build = next(i for i, line in enumerate(done) if "build --pull" in line)
    assert build < done.index("STOPPING") < done.index("BACKUP") < done.index("MIGRATE")
    assert "SYNC" not in done
    assert result.stdout.index("BACKUP") < result.stdout.index("To go back:")
    assert server.version() == 2
    assert not server.marker.exists()


def test_on_docker_a_build_that_fails_leaves_the_old_containers_running_on_the_old_code(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade(DOCKER_MODE="1", FAIL_DOCKER_BUILD="1")
    assert result.returncode != 0
    assert _git(server.target, "rev-parse", "HEAD") == server.before
    assert "STOPPING" not in server.sequence()
    assert not server.marker.exists()
    assert "the code is back on" in result.stderr and "the image as it was" in result.stderr


def test_a_default_branch_renamed_on_the_remote_is_followed(tmp_path):
    """A clone writes origin/HEAD once and a fetch never moves it: the remote is asked each time."""
    server = Server(tmp_path)
    _git(server.seed, "checkout", "-q", "-b", "trunk")
    (server.seed / "NEW").write_text("x\n")
    _git(server.seed, "add", "-A")
    _git(server.seed, "commit", "-qm", "three")
    _git(server.seed, "push", "-q", "origin", "trunk")
    _git(server.remote, "symbolic-ref", "HEAD", "refs/heads/trunk")
    _git(server.remote, "branch", "-D", "main")
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(server.target, "rev-parse", "HEAD") == _git(server.seed, "rev-parse", "trunk")
    assert "on trunk" in result.stdout


def test_a_release_tag_moved_on_the_remote_does_not_stop_the_fetch(tmp_path):
    server = Server(tmp_path, released=True)  # v9.9.9 on the first commit, in the clone too
    _git(server.seed, "tag", "-f", "v9.9.9")  # the remote moved it to the second
    _git(server.seed, "push", "-q", "-f", "origin", "refs/tags/v9.9.9")
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(server.target, "rev-parse", "v9.9.9") == _git(server.seed, "rev-parse", "HEAD")


def test_a_fetch_that_fails_says_what_git_said_and_what_it_means(tmp_path):
    server = Server(tmp_path)
    _git(server.target, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    result = server.upgrade()
    assert result.returncode != 0
    assert "there is no repository at" in result.stderr
    assert "does not appear to be a git repository" in result.stderr  # git's words, not a guess
    assert "private repository" not in result.stderr
    assert "STOPPING" not in result.stdout


def test_a_shipped_file_changed_here_stops_the_upgrade_before_anything_is_touched(tmp_path):
    server = Server(tmp_path)
    (server.target / "CHANGELOG.md").write_text("my notes\n")
    result = server.upgrade()
    assert result.returncode != 0
    assert "CHANGELOG.md" in result.stderr
    assert "docker-compose.override.yml" in result.stderr
    assert server.sequence() == []
    assert not server.marker.exists()
    assert _git(server.target, "rev-parse", "HEAD") == server.before


def test_up_to_date_still_notices_the_bot_is_not_running(tmp_path):
    """After an upgrade whose restart failed, this is the state; "nothing to do" would be wrong."""
    server = Server(tmp_path)
    assert server.upgrade().returncode == 0
    unit = tmp_path / "familydb.service"
    unit.write_text("[Service]\n")
    again = server.upgrade(FAMILYDB_SERVICE_UNIT=str(unit), SERVICE_UP="0")
    assert "[WARN] Already up to date" in again.stdout and "not running" in again.stdout
    assert "restart" in again.stdout
    fine = server.upgrade(FAMILYDB_SERVICE_UNIT=str(unit), SERVICE_UP="1")
    assert "[ OK ] Already up to date" in fine.stdout


def test_a_service_file_as_the_installer_wrote_it_follows_the_new_version(tmp_path):
    server = Server(tmp_path, rich=True)  # deploy/familydb.service gains Nice=5
    unit = tmp_path / "familydb.service"
    unit.write_text("[Service]\nUser=familydb\n")  # exactly what the old version's installer wrote
    result = server.upgrade(FAMILYDB_SERVICE_UNIT=str(unit))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "the installed one is updated to match" in " ".join(result.stdout.split())
    assert unit.read_text() == "[Service]\nUser=familydb\nNice=5\n"
    assert (
        tmp_path / "familydb.service.before-upgrade"
    ).read_text() == "[Service]\nUser=familydb\n"
    assert "SYSTEMCTL daemon-reload" in server.sequence()


def test_a_service_file_edited_by_hand_is_left_alone(tmp_path):
    server = Server(tmp_path, rich=True)
    unit = tmp_path / "familydb.service"
    unit.write_text("[Service]\nUser=familydb\nNice=10\n")
    result = server.upgrade(FAMILYDB_SERVICE_UNIT=str(unit))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "edited by hand" in " ".join(result.stdout.split())
    assert unit.read_text() == "[Service]\nUser=familydb\nNice=10\n"
    assert not (tmp_path / "familydb.service.before-upgrade").exists()


def test_a_run_that_stopped_before_the_code_moved_goes_back_to_the_fresh_backup(tmp_path):
    """The backup of an earlier run is the right one only when that run had moved the code and its
    migrations may have run; before that, the database was untouched and the new backup is newer."""
    server = Server(tmp_path)
    server.marker.parent.mkdir(parents=True, exist_ok=True)
    server.marker.write_text(
        f"target=main\nbefore={server.before}\nbackup=/old/familydb-0.sqlite3\n"
    )
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "familydb-1.sqlite3" in result.stdout
    assert "familydb-0.sqlite3" not in result.stdout


def test_an_upgrade_brings_in_work_merged_after_the_release_with_no_new_version(tmp_path):
    """The newest version is tagged and dated, and the branch has a commit past it: the upgrade
    goes to that commit rather than finding the release it is already on."""
    server = Server(tmp_path, released=True)
    assert _git(server.target, "describe", "--tags", "--exact-match", "HEAD") == "v9.9.9"
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Already up to date" not in result.stdout
    assert _git(server.target, "rev-parse", "HEAD") == _git(
        server.target, "rev-parse", "origin/main"
    )
    assert _git(server.target, "rev-parse", "HEAD") != server.before
    assert server.version() == 2


def test_a_stop_in_the_migrations_says_how_to_go_back_and_how_to_finish(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade(FAIL_MIGRATE="1")
    assert result.returncode != 0
    assert "Nothing was half-done" not in result.stderr
    assert "The upgrade stopped part-way" in result.stderr
    assert f"checkout --quiet --detach {server.before}" in result.stderr
    assert "restore " in result.stderr and "familydb-1.sqlite3" in result.stderr
    assert "finish the upgrade: sudo bash" in result.stderr
    assert server.marker.exists()
    assert server.version() == 1


def test_a_rerun_finishes_a_stopped_upgrade_instead_of_calling_it_up_to_date(tmp_path):
    server = Server(tmp_path)
    assert server.upgrade(FAIL_MIGRATE="1").returncode != 0
    again = server.upgrade()
    assert again.returncode == 0, again.stdout + again.stderr
    assert "Already up to date" not in again.stdout
    assert "not upgraded" in again.stderr
    assert "Finishing it now" in again.stdout
    # What to go back to is still what the first run saw, not the half-way state.
    assert f"checkout --quiet --detach {server.before}" in again.stdout
    assert server.version() == 2
    assert not server.marker.exists()

    last = server.upgrade()
    assert last.returncode == 0, last.stdout + last.stderr
    assert "Already up to date" in last.stdout
    assert "STOPPING" not in last.stdout


def test_code_on_the_target_with_an_unmigrated_database_is_not_up_to_date(tmp_path):
    server = Server(tmp_path)
    _git(server.target, "fetch", "-q", "origin")
    _git(server.target, "checkout", "-q", "--detach", "origin/main")
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Already up to date" not in result.stdout
    assert "the database is at migration 1" in result.stderr
    assert server.version() == 2


def test_the_screen_says_what_this_upgrade_changes_before_it_asks_and_takes_no_backup_before(
    tmp_path,
):
    server = Server(tmp_path, rich=True)
    unit = tmp_path / "familydb.service"
    unit.write_text("[Service]\nUser=familydb\n")
    result = server.upgrade(FAMILYDB_SERVICE_UNIT=str(unit))
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    order = [
        out.index("1 commit (#64)"),
        out.index("Database"),
        out.index("STOPPING"),  # only once it was agreed
        out.index("BACKUP"),
        out.index("To go back:"),
        out.index("SYNC"),
    ]
    assert order == sorted(order)
    flat = " ".join(out.split())
    assert "A switch for the digest (#64)" in out  # the commits, as a pull request lists them
    assert "The digest can be switched off" in out  # what the changelog says is new
    assert "1 new migration: 0002_second" in flat
    assert "1 updated (anthropic 1.0.0 → 1.1.0); 1 added (newthing 2.0.0)" in flat
    assert "new in .env.example: DIGEST_SWITCH" in flat
    assert "changed in deploy/familydb.service" in flat
    assert "some rewrite what is in it" in flat  # said because there is a migration to say it about


def test_what_goes_as_expected_is_one_line_and_the_last_line_carries_what_moved(tmp_path):
    server = Server(tmp_path, rich=True)
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    assert "Fetched" not in out and "Checking out" not in out  # nothing a person acts on
    assert "Stopping" not in out and "Starting" not in out
    assert "Applying 1 new migration (0002_second)" in out
    last = [line for line in out.splitlines() if line.startswith("[ OK ] Upgraded ")]
    assert len(last) == 1
    assert f"Upgraded {server.before[:7]} → " in last[0]  # where it was, and where it is
    assert "· 1 commit · 1 migration · 2 packages · down " in last[0]
    assert "go back" not in out.split(last[0])[1].lower()  # said again only if it may be needed


def test_an_upgrade_with_nothing_to_change_says_so_in_a_line_and_takes_no_backup(tmp_path):
    server = Server(tmp_path)
    assert server.upgrade().returncode == 0
    again = server.upgrade()
    assert again.returncode == 0, again.stdout + again.stderr
    assert "Already up to date" in again.stdout
    assert "BACKUP" not in again.stdout and "commit" not in again.stdout


def test_a_change_with_no_migration_or_package_move_says_nothing_about_them(tmp_path):
    server = Server(tmp_path)
    (server.tmp / "seed/src/familydb/store/migrations/0002_second.sql").unlink()
    _git(server.tmp / "seed", "commit", "-q", "-am", "drop it again")
    _git(server.tmp / "seed", "push", "-q", "origin", "main")
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    flat = " ".join(result.stdout.split())
    # Nothing to say about the database or the packages, so nothing is said: no news is the report.
    assert "Database" not in flat and "Packages" not in flat and "Settings" not in flat
    assert "some rewrite what is in it" not in flat
    assert "commit" in flat and "migration" not in flat.split("Upgraded ")[1]


def test_a_failed_step_after_the_summary_still_says_how_to_go_back(tmp_path):
    server = Server(tmp_path, rich=True)
    result = server.upgrade(FAIL_MIGRATE="1")
    assert result.returncode != 0
    assert f"checkout --quiet --detach {server.before}" in result.stderr
    assert "finish the upgrade: sudo bash" in result.stderr


def test_the_screen_says_where_it_stands_and_where_it_is_going_and_how_big_the_move_is(tmp_path):
    server = Server(tmp_path, rich=True)
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    lines = out.splitlines()
    installed = next(line for line in lines if line.lstrip().startswith("Installed"))
    going = next(line for line in lines if line.lstrip().startswith("Upgrading"))
    assert server.before[:7] in installed
    assert server.before[:7] not in going and installed != going
    assert lines.index(installed) + 1 == lines.index(going)  # one above the other
    assert "on main, where v9.9.9 is in progress" in going  # what it follows, and what is coming
    # git's own picture: a row for each part that changes, + and - to scale, with the counts.
    assert any(re.fullmatch(r"  \S+ +\d+  \++-* *\s?\+\d+ -\d+", line) for line in lines), out


def test_the_run_counts_its_steps_and_the_foot_of_the_window_is_the_full_bar(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    foot = next(line for line in result.stdout.splitlines() if line.startswith("╚═["))
    assert "] 100%  8/8 " in foot and foot.endswith("╝")
    bar = foot[foot.index("[") + 1 : foot.index("]")]
    assert set(bar) == {"█"}  # every step ran: nothing left empty


def test_a_run_that_stopped_shows_a_bar_that_stops_where_it_did():
    done = subprocess.run(
        [
            BASH,
            "-c",
            'set -euo pipefail; . "$ROOT/scripts/lib/common.sh"; progress_total 7; progress_to 3; finish bad "Stopped"',
        ],
        env={**os.environ, "ROOT": ROOT.as_posix(), "NO_COLOR": "1", "COLUMNS": "60"},
        capture_output=True,
        text=True,
    )
    foot = next(line for line in done.stdout.splitlines() if line.startswith("╚═["))
    assert " 42%  3/7 " in foot
    bar = foot[foot.index("[") + 1 : foot.index("]")]
    assert "█" in bar and "░" in bar and bar.index("░") > bar.index("█")
    assert "[FAIL] Stopped" in done.stdout


def test_a_step_that_fails_midway_shows_where_the_run_got_to_above_what_went_wrong(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade(FAIL_MIGRATE="1")
    assert result.returncode != 0
    assert "62%  5/8" in result.stderr  # the migration is the sixth step: five were done
    assert result.stderr.index("5/8") < result.stderr.index("failed")


FAILING = "✗ model key: no key\n    → add one\n\n1 thing(s) must be fixed\n"


def test_a_problem_that_was_there_before_is_shown_and_not_blamed_on_the_upgrade(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade(DOCTOR_BEFORE=FAILING, DOCTOR_AFTER=FAILING)
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.search(r"✗ model key +no key", result.stdout)  # it is in front of the person
    assert "→ add one" in result.stdout
    assert "(the same before the upgrade)" in result.stdout
    last = [line for line in result.stdout.splitlines() if "Upgraded " in line]
    assert last and last[0].startswith("[ OK ]")  # and the upgrade is not called a failure for it


def test_a_problem_the_upgrade_brought_is_called_the_upgrades(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade(DOCTOR_AFTER=FAILING)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[WARN] Upgraded " in result.stdout and "1 new problem" in result.stdout
    # the way back is said again, because it may be needed now
    assert result.stdout.count(f"checkout --quiet --detach {server.before}") == 2


def test_the_installed_version_is_shown_even_when_there_is_nothing_to_upgrade(tmp_path):
    server = Server(tmp_path)
    assert server.upgrade().returncode == 0
    again = server.upgrade()
    assert "Installed" in again.stdout and "Upgrading" not in again.stdout
