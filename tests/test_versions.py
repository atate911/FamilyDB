"""Which version an install follows, and that an upgrade never goes backwards.

Runs scripts/lib/common.sh's functions against real git repositories: a "remote" with a release
tag and later work, and a clone standing in for an install.

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
    # git 2.46 and later hand a commit's or a fetch's housekeeping to a background process that
    # holds .git/maintenance.lock for a moment after the command returns; a test that then removes
    # or inspects .git races it. Every git run here, by a test or by maintain.sh, keeps it in front.
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "maintenance.autoDetach",
    "GIT_CONFIG_VALUE_0": "false",
    "GIT_CONFIG_KEY_1": "gc.autoDetach",
    "GIT_CONFIG_VALUE_1": "false",
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


def test_once_it_is_released_an_install_still_follows_the_branch(remote, tmp_path) -> None:
    install = clone(remote, tmp_path)
    assert shell(install, 'wanted_version "$INSTALL"').stdout.strip() == "branch main"


def test_work_merged_after_a_release_reaches_an_install_without_a_new_version(
    remote, tmp_path
) -> None:
    """The release is dated, the tag exists, and the branch has moved on: the install is still
    offered the branch's new commits, not the tag it is already past."""
    install = clone(remote, tmp_path)
    git(install, "checkout", "-q", "--detach", "v0.1.0")
    (remote / "fix.txt").write_text("a fix merged after v0.1.0 was tagged\n")
    git(remote, "add", "fix.txt")
    git(remote, "commit", "-q", "-m", "A fix, with no new version")
    git(install, "fetch", "-q", "--tags", "origin")
    kind, name = shell(install, 'wanted_version "$INSTALL"').stdout.split()
    assert (kind, name) == ("branch", "main")
    assert shell(install, f'moves_forward "$INSTALL" origin/{name}').returncode == 0


def test_with_no_default_branch_the_newest_release_is_the_fallback(remote, tmp_path) -> None:
    install = clone(remote, tmp_path)
    git(remote, "symbolic-ref", "HEAD", "refs/heads/not-a-branch")  # the remote names none
    git(install, "remote", "set-head", "origin", "--delete")
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
