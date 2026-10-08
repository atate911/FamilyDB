"""`maintain.sh upgrade` when it stops after moving the code, and when it is rerun.

The real cmd_upgrade (and the helpers beside it) is cut out of the script and run against a real
git remote and checkout in a temporary folder, with lib/common.sh's own failure reporting and the
parts that would touch a server (the service, the dependency install, the migration) replaced by
stubs that succeed or fail on request.
"""

# ruff: noqa: E501  (the harness is a shell script, written as a person would type it)

import os
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
}

HARNESS = r"""
set -euo pipefail
. "$ROOT/scripts/lib/common.sh"
enable_failure_reporting
LEDGER_DIR="$WORK/ledger"
as_root() { "$@"; }
take_backup() { echo BACKUP; LAST_BACKUP="$WORK/backups/familydb-1.sqlite3"; }
stop_bot() { echo STOPPING; }
start_bot() { echo STARTING; }
retry() {
  echo SYNC
  if [ "${FAIL_SYNC:-0}" = 1 ]; then die "Installing the dependencies failed"; fi
}
familydb_cmd() {
  case "$1" in
    doctor) echo "✓ settings: loaded"; echo; echo "Everything is set up." ;;
    db)
      echo MIGRATE
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

    def __init__(self, tmp: Path, *, rich: bool = False):
        self.tmp = tmp
        remote = tmp / "remote.git"
        seed = tmp / "seed"
        _git(tmp, "init", "-q", "--bare", "-b", "main", str(remote))
        _git(tmp, "init", "-q", "-b", "main", str(seed))
        (seed / "CHANGELOG.md").write_text("# Changelog\n\n## v9.9.9 — in progress\n\n### New\n\n")
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
        _git(seed, "remote", "add", "origin", str(remote))
        _git(seed, "push", "-q", "origin", "main")
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
                **os.environ,
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


def test_rollback_is_printed_before_the_bot_is_stopped(tmp_path):
    server = Server(tmp_path)
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    command = f"checkout --quiet --detach {server.before}"
    assert command in result.stdout
    assert "familydb-1.sqlite3" in result.stdout
    assert result.stdout.index(command) < result.stdout.index("STOPPING")
    assert server.version() == 2
    assert not server.marker.exists()


@pytest.mark.parametrize("failing", ["FAIL_MIGRATE", "FAIL_SYNC"])
def test_a_stop_after_the_checkout_says_how_to_go_back_and_how_to_finish(tmp_path, failing):
    server = Server(tmp_path)
    result = server.upgrade(**{failing: "1"})
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
    result = server.upgrade()
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    order = [
        out.index("1 commit (#64)"),
        out.index("Database"),
        out.index("BACKUP"),  # only once it was agreed
        out.index("To go back:"),
        out.index("STOPPING"),
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
    last = [line for line in out.splitlines() if line.startswith("✓ Upgraded to")]
    assert len(last) == 1
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
    assert "commit" in flat and "migration" not in flat.split("Upgraded to")[1]


def test_a_failed_step_after_the_summary_still_says_how_to_go_back(tmp_path):
    server = Server(tmp_path, rich=True)
    result = server.upgrade(FAIL_MIGRATE="1")
    assert result.returncode != 0
    assert f"checkout --quiet --detach {server.before}" in result.stderr
    assert "finish the upgrade: sudo bash" in result.stderr
