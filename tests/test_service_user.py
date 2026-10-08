"""`bootstrap.sh --user NAME` reaches the account, the unit and the scripts that look after it later.

Pieces of the real scripts are cut out and run (nothing here creates an account or writes to the
system): the argument that bootstrap forwards, the unit install.sh writes, and the recorded name
that maintain.sh and uninstall.sh read back.
"""

# ruff: noqa: E501  (shell snippets, written as a person would type them)
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")

pytestmark = pytest.mark.skipif(not BASH, reason="bash required for shell integration")


def _bash(code: str, **env: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, "-c", code],
        env={**os.environ, "ROOT": ROOT.as_posix(), "NO_COLOR": "1", **env},
        capture_output=True,
        text=True,
    )


def _between(path: str, start: str, end: str) -> str:
    text = (ROOT / path).read_text()
    first = text.index(start)
    return text[first : text.index(end, first) + len(end)]


def test_bootstrap_forwards_a_chosen_user_and_only_a_chosen_one():
    snippet = _between("scripts/bootstrap.sh", 'INSTALL_ARGS=("--mode"', '"$SERVICE_USER")')
    prelude = "set -euo pipefail; DEFAULT_SERVICE_USER=familydb; MODE=venv; "
    custom = _bash(
        prelude + "SERVICE_USER=alice; " + snippet + '; printf "%s\\n" "${INSTALL_ARGS[@]}"'
    )
    assert custom.stdout.split() == ["--mode", "venv", "--user", "alice"], custom.stderr
    default = _bash(
        prelude + "SERVICE_USER=familydb; " + snippet + '; printf "%s\\n" "${INSTALL_ARGS[@]}"'
    )
    assert default.stdout.split() == ["--mode", "venv"], default.stderr


def test_the_installed_unit_runs_as_the_chosen_user():
    snippet = _between("scripts/install.sh", 'sed -e "s#/opt/familydb#', '"$unit" > "$tmp_unit"')
    unit = ROOT / "deploy/familydb.service"
    result = _bash(
        f"set -euo pipefail; REPO_ROOT=/srv/fam; SERVICE_USER=alice; unit={unit.as_posix()}; "
        f'tmp_unit="$(mktemp)"; {snippet}; cat "$tmp_unit"; rm -f "$tmp_unit"'
    )
    assert result.returncode == 0, result.stderr
    assert "\nUser=alice\n" in result.stdout and "\nGroup=alice\n" in result.stdout
    assert "familydb\n" not in result.stdout.split("User=alice")[1].split("WorkingDirectory")[0]
    assert "WorkingDirectory=/srv/fam" in result.stdout


def test_the_scripts_read_back_the_recorded_user(tmp_path):
    ledger = tmp_path / "ledger"
    code = f"""
set -euo pipefail
. "$ROOT/scripts/lib/common.sh"
LEDGER_DIR={ledger.as_posix()}
SERVICE_USER_FILE="$LEDGER_DIR/service-user"
_ledger_on() {{ return 0; }}
echo "before: $(recorded_service_user)"
record_service_user alice
echo "recorded: $(recorded_service_user)"
echo "file: $(cat "$SERVICE_USER_FILE")"
printf 'Not A Name\\n' > "$SERVICE_USER_FILE"
echo "garbled: $(recorded_service_user)"
"""
    result = _bash(code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split("\n")[:4] == [
        "before: familydb",
        "recorded: alice",
        "file: alice",
        "garbled: familydb",
    ]


@pytest.mark.parametrize("script", ["install.sh", "bootstrap.sh"])
def test_a_bad_user_name_is_refused_before_anything_happens(script):
    result = subprocess.run(
        [BASH, (ROOT / "scripts" / script).as_posix(), "--user", "Bad Name", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "--user must be a system account name" in result.stderr


def test_name_rules():
    code = '. "$ROOT/scripts/lib/common.sh"; for n in familydb fam-db _x a1 Bad "a b" "" 1a a$(printf x%.0s {1..40}); do valid_user_name "$n" && echo "ok:$n" || echo "no:$n"; done'
    out = _bash(code).stdout.split("\n")
    assert out[:4] == ["ok:familydb", "ok:fam-db", "ok:_x", "ok:a1"]
    # Bad, "a b", empty, 1a, and 41 characters.
    assert [line.split(":")[0] for line in out[4:9]] == ["no"] * 5
