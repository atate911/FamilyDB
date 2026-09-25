"""Exercise real backup shell code with fake privilege/container boundaries."""

import os
import shutil
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from familydb.store import db, members

ROOT = Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")


@pytest.mark.parametrize("docker_mode", [0, 1])
@pytest.mark.parametrize("fail", [False, True])
def test_backup_reads_wal_and_fails_closed(conn, settings, tmp_path, docker_mode, fail):
    if not BASH or not Path(BASH).exists():
        pytest.skip("bash required for shell integration")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    with db.transaction(conn):
        members.add(conn, "Only in the WAL", "parent")
    script = (ROOT / "scripts/maintain.sh").read_text()
    start = script.index("take_backup() {")
    function = script[start : script.index("\n# ----", start)]
    helper = tmp_path / "backup.py"
    helper.write_text(
        "import sqlite3,sys\n"
        "from contextlib import closing\n"
        "with closing(sqlite3.connect(sys.argv[1])) as source:\n"
        "    with closing(sqlite3.connect(sys.argv[2])) as target:\n"
        "        source.backup(target)\n"
    )
    # Feedback/privilege functions are replaced, not the backup implementation.
    harness = r"""
set -euo pipefail
system_change() { :; }
ok() { :; }
note() { :; }
warn() { :; }
die() { echo "$*" >&2; exit 1; }
require_free_mb() { :; }
try_step() { shift; "$@"; }
step() { shift; "$@"; }
as_root() { if [ "$1" = chown ]; then return; fi; "$@"; }
backup() {
  if [ "$FAIL_BACKUP" = 1 ]; then printf 'partial' > "$1"; return 1; fi
  "$TEST_PYTHON" "$TEST_HELPER" "$DB" "$1"
}
familydb_cmd() { backup "$3"; }
docker() {
  local mount="" previous="" last=""
  for arg in "$@"; do
    if [ "$previous" = -v ]; then mount="$arg"; fi
    previous="$arg"
    last="$arg"
  done
  [ -n "$mount" ] || return 2
  [[ "$last" = /backup/* ]] || return 3
  backup "${mount%:/backup}/${last#/backup/}"
}
"""
    path = tmp_path / "harness.sh"
    path.write_text(harness + function + '\ntake_backup "$BACKUP_DIR" test\n', newline="\n")
    directory = tmp_path / "backup with spaces"
    directory.mkdir()
    env = {
        **os.environ,
        "DB": settings.familydb_path.name,
        "TARGET": ".",
        "BACKUP_DIR": directory.name,
        "DOCKER_MODE": str(docker_mode),
        "DRY_RUN": "0",
        "SERVICE_USER": "test",
        "TEST_PYTHON": Path(sys.executable).as_posix(),
        "TEST_HELPER": helper.as_posix(),
        "FAIL_BACKUP": "1" if fail else "0",
    }
    result = subprocess.run(
        [BASH, path.as_posix()], env=env, cwd=tmp_path, capture_output=True, text=True
    )
    backups = list(directory.glob("*.sqlite3"))
    if fail:
        assert result.returncode != 0, result.stdout + result.stderr
        assert backups == []
        assert "no backup was created" in result.stderr
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(backups) == 1
        with closing(db.connect(backups[0])) as restored:
            assert members.find_by_name(restored, "Only in the WAL") is not None
    assert members.find_by_name(conn, "Only in the WAL") is not None
