"""`maintain.sh restore` checks a backup before it stops or replaces anything.

The real cmd_restore is cut out of the script and run with the things it would do to a server
replaced by stubs that record themselves.
"""

import os
import shutil
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from familydb.store import db

ROOT = Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")

pytestmark = pytest.mark.skipif(not BASH, reason="bash required for shell integration")

HARNESS = r"""
set -euo pipefail
. "$ROOT/scripts/lib/common.sh"
die() { echo "DIED: $*" >&2; exit 1; }
as_root() { "$@"; }
approve() { echo ASKED; return 1; }
take_backup() { echo TOOK_BACKUP >> "$EFFECTS"; }
stop_bot() { echo STOPPED >> "$EFFECTS"; }
step() { shift; echo "STEP $*" >> "$EFFECTS"; }
try_step() { shift; echo "STEP $*" >> "$EFFECTS"; }
"""


def _backup_at(path: Path, extra_version: int | None = None) -> Path:
    with closing(db.connect(path)) as source:
        db.migrate(source)
        if extra_version is not None:
            source.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, 'then')",
                (extra_version,),
            )
        source.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return path


def _restore(tmp_path: Path, backup: Path):
    script = (ROOT / "scripts/maintain.sh").read_text()
    start = script.index("cmd_restore() {")
    function = script[start : script.index("\n}\n", start) + 3]
    venv = tmp_path / "target" / ".venv" / "bin"
    venv.mkdir(parents=True)
    wrapper = venv / "python"
    wrapper.write_text(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n')
    wrapper.chmod(0o755)
    path = tmp_path / "restore.sh"
    path.write_text(HARNESS + function + "\ncmd_restore\n", newline="\n")
    effects = tmp_path / "effects"
    env = {
        **os.environ,
        "ROOT": ROOT.as_posix(),
        "NO_COLOR": "1",
        "TARGET": (tmp_path / "target").as_posix(),
        "RESTORE_FILE": backup.as_posix(),
        "BACKUP_DIR": (tmp_path / "backups").as_posix(),
        "DB": (tmp_path / "live.sqlite3").as_posix(),
        "DOCKER_MODE": "0",
        "SERVICE_USER": "test",
        "EFFECTS": effects.as_posix(),
    }
    result = subprocess.run(
        [BASH, path.as_posix()], env=env, cwd=tmp_path, capture_output=True, text=True
    )
    return result, effects.read_text() if effects.exists() else ""


def test_restore_refuses_a_backup_newer_than_the_code(tmp_path):
    newest = max(version for version, _, _ in db.list_migrations())
    backup = _backup_at(tmp_path / "newer.sqlite3", newest + 1)
    result, effects = _restore(tmp_path, backup)
    assert result.returncode != 0
    assert f"version {newest + 1}" in result.stderr
    assert f"up to {newest}" in result.stderr
    assert "upgrade" in result.stderr
    assert "Nothing was stopped or replaced" in result.stderr
    assert effects == ""  # no safety backup, no stop, nothing put in place


def test_restore_goes_on_with_a_backup_from_this_version(tmp_path):
    result, effects = _restore(tmp_path, _backup_at(tmp_path / "same.sqlite3"))
    assert "DIED" not in result.stderr, result.stderr
    assert "ASKED" in result.stdout  # it got as far as asking
    assert effects == ""


def test_restore_still_refuses_what_is_not_a_database(tmp_path):
    junk = tmp_path / "junk.sqlite3"
    junk.write_text("not a database")
    result, effects = _restore(tmp_path, junk)
    assert result.returncode != 0
    assert "backup validation failed; nothing was restored" in result.stderr
    assert effects == ""
