"""The scripts read .env as the program does, and write it so the program reads it back whole.

`env_value` (scripts/lib/common.sh) is held to python-dotenv, which is what pydantic-settings
reads the file with: a script that saw `8080 # moved` where the program saw `8080` would ask the
page at the wrong address and call a running bot stopped. `env_file_write` must leave every other
line alone, replace the line the program reads (the last one for a name), and never glue a new
line onto a file that did not end with one.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(not BASH or os.name == "nt", reason="bash")

LIB = f'source "{ROOT / "scripts/lib/common.sh"}"\nas_root() {{ "$@"; }}\n'

TRICKY = (
    "# the family's settings\n"
    "WEB_PORT=8080 # moved last week\n"
    'WEB_HOST="0.0.0.0"\n'
    "export WEB_ENABLED=true\n"
    "WEB_DOMAIN = a.example   \n"
    "WEB_PASSWORD='it is # not a comment'\n"
    'OPENAI_API_KEY="sk-\\"quoted\\" and \\\\ back"\n'
    "ANTHROPIC_API_KEY=first\n"
    "ANTHROPIC_API_KEY=last\n"
    "WEB_PUBLIC_PORT=8443\r\n"
    "GEMINI_API_KEY=\n"
    "  TZ=Europe/London\n"
)


def value(env_file: Path, key: str) -> str:
    done = subprocess.run(
        [BASH, "-c", LIB + f'printf "%s" "$(env_value "{env_file}" {key})"'],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def write(env_file: Path, key: str, val: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, "-c", LIB + 'env_file_write "$1" "$2" "$3"', "_", str(env_file), key, val],
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )


def test_the_script_reads_every_value_as_the_program_does(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(TRICKY, newline="")
    expected = dotenv_values(env_file)
    for key, want in expected.items():
        assert value(env_file, key) == (want or ""), key
    assert expected["WEB_PORT"] == "8080"  # the case that mattered: an inline comment
    assert expected["WEB_ENABLED"] == "true"  # and an `export` line
    assert value(env_file, "NOT_THERE") == ""


def test_a_missing_file_reads_as_empty_and_does_not_fail_the_caller(tmp_path) -> None:
    done = subprocess.run(
        [
            BASH,
            "-c",
            LIB + f'set -e; v="$(env_value "{tmp_path}/.env" WEB_PORT)"; echo "[$v] alive"',
        ],
        capture_output=True,
        text=True,
    )
    assert done.stdout.strip() == "[] alive"


def test_writing_adds_a_line_of_its_own_even_when_the_file_did_not_end_with_one(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("WEB_DOMAIN=a.example")  # no trailing newline, as some editors leave it
    env_file.chmod(0o600)
    assert write(env_file, "WEB_PUBLIC_PORT", "8443").returncode == 0
    assert env_file.read_text() == "WEB_DOMAIN=a.example\nWEB_PUBLIC_PORT=8443\n"
    assert oct(env_file.stat().st_mode & 0o777) == "0o600"
    assert dotenv_values(env_file) == {"WEB_DOMAIN": "a.example", "WEB_PUBLIC_PORT": "8443"}


def test_writing_replaces_the_line_the_program_reads_and_keeps_the_rest(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(TRICKY, newline="")
    assert write(env_file, "ANTHROPIC_API_KEY", "newest").returncode == 0
    text = env_file.read_text()
    assert "ANTHROPIC_API_KEY=first\n" in text  # an earlier duplicate is left as it was
    assert text.count("ANTHROPIC_API_KEY=") == 2
    assert dotenv_values(env_file)["ANTHROPIC_API_KEY"] == "newest"
    assert "WEB_PORT=8080 # moved last week\n" in text  # nothing else touched
    assert write(env_file, "WEB_ENABLED", "false").returncode == 0
    assert "export WEB_ENABLED=true" not in env_file.read_text()
    assert dotenv_values(env_file)["WEB_ENABLED"] == "false"


@pytest.mark.parametrize(
    "val",
    ["a&b", "x|y", "back\\slash", "with space", "hash # inside", "it's", "end  ", "$HOME"],
)
def test_a_value_is_written_so_it_reads_back_whole(tmp_path, val: str) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("WEB_PORT=8080\n")
    assert write(env_file, "WEB_PASSWORD", val).returncode == 0
    assert dotenv_values(env_file)["WEB_PASSWORD"] == val
    assert value(env_file, "WEB_PASSWORD") == val
    assert dotenv_values(env_file)["WEB_PORT"] == "8080"


def test_a_file_that_is_not_there_yet_is_made_private(tmp_path) -> None:
    env_file = tmp_path / ".env"
    assert write(env_file, "WEB_PORT", "9090").returncode == 0
    assert env_file.read_text() == "WEB_PORT=9090\n"
    assert oct(env_file.stat().st_mode & 0o777) == "0o600"
