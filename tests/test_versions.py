"""Which version an install follows, and that an upgrade never goes backwards.

Runs the shell functions from scripts/lib/common.sh against real git repositories: a "remote"
with a release tag and later work, and a clone of it standing in for an install.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
GIT = shutil.which("git")
pytestmark = pytest.mark.skipif(not (BASH and GIT and os.name != "nt"), reason="bash and git")

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": "/dev/null",
}


def git(where: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(where), *args], check=True, capture_output=True, text=True, env=ENV
    ).stdout.strip()


def commit(repo: Path, heading: str) -> str:
    (repo / "CHANGELOG.md").write_text(f"# Changelog\n\n{heading}\n\nNotes.\n")
    git(repo, "add", "CHANGELOG.md")
    git(repo, "commit", "-q", "-m", heading)
    return git(repo, "rev-parse", "HEAD")


def shell(install: Path, call: str) -> subprocess.CompletedProcess[str]:
    script = (
        f"source {ROOT / 'scripts/lib/common.sh'}\n"
        'as_root() { "$@"; }\n'  # the test owns the repositories; no sudo
        f"{call}\n"
    )
    return subprocess.run(
        [BASH, "-c", script], capture_output=True, text=True, env={**ENV, "INSTALL": str(install)}
    )


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    repo = tmp_path / "remote"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    commit(repo, "## v0.1.0 — first alpha (2026-09-21)")
    git(repo, "tag", "v0.1.0")
    return repo


def clone(remote: Path, tmp_path: Path) -> Path:
    install = tmp_path / "install"
    subprocess.run(["git", "clone", "-q", str(remote), str(install)], check=True, env=ENV)
    return install


def test_while_a_version_is_being_built_an_install_follows_the_branch(remote, tmp_path) -> None:
    commit(remote, "## v0.1.0 — in progress")
    install = clone(remote, tmp_path)
    assert shell(install, 'wanted_version "$INSTALL"').stdout.strip() == "branch main"


def test_once_it_is_released_an_install_follows_the_tag(remote, tmp_path) -> None:
    install = clone(remote, tmp_path)
    assert shell(install, 'wanted_version "$INSTALL"').stdout.strip() == "tag v0.1.0"


def test_an_early_tag_is_never_a_step_forward_from_newer_work(remote, tmp_path) -> None:
    """A version tagged before the work on its branch was done is behind that work, so an
    upgrade to it would go backwards."""
    commit(remote, "## v0.1.0 — in progress")
    install = clone(remote, tmp_path)  # on main, past the tag
    assert shell(install, 'moves_forward "$INSTALL" v0.1.0').returncode != 0
    assert shell(install, 'moves_forward "$INSTALL" origin/main').returncode != 0  # already there


def test_new_work_on_the_branch_is_a_step_forward(remote, tmp_path) -> None:
    install = clone(remote, tmp_path)
    git(install, "checkout", "-q", "v0.1.0")
    commit(remote, "## v0.1.0 — in progress")
    git(install, "fetch", "-q", "origin")
    assert shell(install, 'moves_forward "$INSTALL" origin/main').returncode == 0
