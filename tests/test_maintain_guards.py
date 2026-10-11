"""What keeps maintain.sh from doing harm by accident: one changing command at a time, an install
told from its service file or virtualenv rather than from the compose file that ships with the
code, a Docker start that is checked rather than assumed, a fetch failure named for what it is,
free space checked before the bot is stopped, and an upgrade finished by the script that came
with the new code.

Runs against the install that tests/install_fixture.py builds; the upgrade tests give it a bare
remote with a newer commit to fetch from.
"""

from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.install_fixture import ROOT, git, healthy_install, maintain, stub

BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(not BASH or not shutil.which("git"), reason="bash and git")


def flat(text: str) -> str:
    return " ".join(text.split())


def test_one_command_that_changes_the_install_runs_at_a_time(tmp_path) -> None:
    """The nightly backup landing while an upgrade runs, or two people upgrading at once, would
    each work on what the other is changing; the second says who holds the lock and stops."""
    target, env = healthy_install(tmp_path)
    lock = Path(env["FAMILYDB_LEDGER_DIR"]) / "maintain.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a+") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        held.seek(0)
        held.truncate()
        held.write("upgrade (pid 4242, since 2026-10-10 09:00)\n")
        held.flush()
        busy = maintain(target, env, "backup", "--yes")
        assert busy.returncode == 1
        assert "another maintain.sh is already working" in flat(busy.stderr)
        assert "upgrade (pid 4242" in busy.stderr
        assert len(list((target / "backups").glob("familydb-*.sqlite3"))) == 1  # nothing taken
        reading = maintain(target, env, "status")  # a reader takes no lock
        assert reading.returncode == 0, reading.stdout + reading.stderr
    after = maintain(target, env, "backup", "--yes")
    assert after.returncode == 0, after.stdout + after.stderr
    assert len(list((target / "backups").glob("familydb-*.sqlite3"))) == 2


def test_a_broken_virtualenv_beside_docker_is_still_a_virtualenv_install(tmp_path) -> None:
    """docker-compose.yml ships with the code, so it says nothing by itself: an install with a
    .venv, however broken, is the one the doctor should mend, not a Docker install to build."""
    target, env = healthy_install(tmp_path)
    (target / ".venv/bin/familydb").unlink()
    shutil.copy(ROOT / "docker-compose.yml", target / "docker-compose.yml")
    stub(env, "docker", "#!/bin/sh\nexit 0\n")
    done = maintain(target, env, "status")
    assert "no service installed" in done.stdout
    assert "Docker" not in done.stdout.splitlines()[1]  # the banner names how it runs
    (tmp_path / "d").mkdir()
    docker_target, docker_env = healthy_install(tmp_path / "d", docker=True)
    stub(docker_env, "docker", "#!/bin/sh\nexit 0\n")
    assert "Docker" in maintain(docker_target, docker_env, "status").stdout.splitlines()[1]


@pytest.mark.parametrize(
    ("state", "last_line"),
    [("running", "[ OK ] Restarted"), ("exited", "[FAIL] FamilyDB did not come back up")],
)
def test_on_docker_a_start_is_believed_only_when_the_container_runs(tmp_path, state, last_line):
    """With the page off there is nothing to ask, and a container that stopped straight away
    is not "came back up"."""
    target, env = healthy_install(tmp_path, docker=True)
    (target / ".env").write_text("WEB_ENABLED=false\n")
    stub(
        env,
        "docker",
        '#!/bin/sh\ncase "$*" in *" ps "*) echo "bot ' + state + '" ;; esac\nexit 0\n',
    )
    done = maintain(target, env, "restart", "--yes")
    assert last_line in done.stdout, done.stdout + done.stderr
    assert done.returncode == (0 if state == "running" else 1)


@pytest.mark.parametrize(
    ("said", "kind"),
    [
        (
            "fatal: unable to access 'https://github.com/x/y/': Could not resolve host: github.com",
            "network",
        ),
        ("ssh: connect to host github.com port 22: Connection timed out", "network"),
        (
            "fatal: could not read Username for 'https://github.com': terminal prompts disabled",
            "credential",
        ),
        (
            "ERROR: Repository not found.\nfatal: Could not read from remote repository.",
            "credential",
        ),
        ("git@github.com: Permission denied (publickey).", "credential"),
        ("fatal: detected dubious ownership in repository at '/opt/familydb'", "ownership"),
        ("fatal: '/srv/gone.git' does not appear to be a git repository", "missing"),
        ("something else entirely", "unknown"),
    ],
)
def test_what_a_failed_fetch_said_is_read_for_what_it_means(said: str, kind: str) -> None:
    done = subprocess.run(
        [BASH, "-c", f'source "{ROOT}/scripts/lib/common.sh"; fetch_trouble "$1"', "_", said],
        capture_output=True,
        text=True,
        check=True,
    )
    assert done.stdout == kind


def _with_a_newer_version(tmp_path: Path):
    """The install, a bare remote it fetches from, and a clone of that remote one commit ahead."""
    target, env = healthy_install(tmp_path)
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    git(target, "remote", "set-url", "origin", str(remote))
    git(target, "push", "-q", "origin", "HEAD:main")
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(remote), str(seed)], check=True)
    return target, env, seed


def test_free_space_is_checked_before_the_bot_is_stopped(tmp_path) -> None:
    target, env, seed = _with_a_newer_version(tmp_path)
    (seed / "NOTES").write_text("newer\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "newer")
    git(seed, "push", "-q", "origin", "main")
    before = git(target, "rev-parse", "HEAD")
    done = maintain(target, env, "upgrade", "--yes", FAKE_DF_FREE_MB="100")
    assert done.returncode == 1
    assert "only 100 MB free" in flat(done.stderr) and "needs about 600 MB" in flat(done.stderr)
    assert "Nothing to stop" not in done.stdout  # it never got as far as stopping the bot
    assert git(target, "rev-parse", "HEAD") == before


def test_the_upgrade_is_finished_by_the_script_that_came_with_the_new_code(tmp_path) -> None:
    """A release can change how an upgrade is finished only if the new maintain.sh does the
    finishing: the old one fetches, asks and moves the code, then hands over."""
    target, env, seed = _with_a_newer_version(tmp_path)
    script = seed / "scripts/maintain.sh"
    text = script.read_text()
    marker = "upgrade_finish() { # from the checkout on"
    assert marker in text
    script.write_text(
        text.replace(
            marker,
            'upgrade_finish() { say "FINISHED-BY-THE-NEW-SCRIPT"; : # from the checkout on',
            1,
        )
    )
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "a newer maintain.sh")
    git(seed, "push", "-q", "origin", "main")
    done = maintain(target, env, "upgrade", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "FINISHED-BY-THE-NEW-SCRIPT" in done.stdout
    assert git(target, "rev-parse", "HEAD") == git(seed, "rev-parse", "HEAD")
    assert "[ OK ] Upgraded" in done.stdout
    assert not (Path(env["FAMILYDB_LEDGER_DIR"]) / "upgrade-pending").exists()
    assert (Path(env["FAMILYDB_LEDGER_DIR"]) / "last-upgrade").exists()


def test_resume_is_refused_when_nothing_is_half_way_through_an_upgrade(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = maintain(target, env, "upgrade", "--resume", "--yes", UPGRADE_NAME="main")
    assert done.returncode == 1
    assert "nothing here is half-way through one" in flat(done.stderr)


def test_uv_is_never_run_without_the_install_as_its_home() -> None:
    """Every `uv sync` in the scripts goes through the helpers that keep uv's cache and Python
    inside the install; a bare one that has to build the virtualenv again builds it on a Python
    under /root."""
    allowed = {"scripts/lib/common.sh"}
    for path in sorted(Path(ROOT, "scripts").rglob("*.sh")):
        relative = path.relative_to(ROOT).as_posix()
        for line in path.read_text().splitlines():
            if "uv sync" in line and relative not in allowed:
                assert "uv_vars" in line or "uv_env" in line or "UV_PYTHON_INSTALL_DIR" in line, (
                    f"{relative}: {line}"
                )
    common = (ROOT / "scripts/lib/common.sh").read_text()
    assert "UV_PYTHON_INSTALL_DIR=%s/.local/share/uv/python" in common


def test_the_fetch_never_waits_for_a_password() -> None:
    """A question under a spinner would wait forever: git is told there is nobody to ask."""
    script = (ROOT / "scripts/maintain.sh").read_text()
    fetch = next(line for line in script.splitlines() if 'git -C "$TARGET" fetch --tags' in line)
    assert "GIT_TERMINAL_PROMPT=0" in fetch and "--force" in fetch
    assert os.environ.get("GIT_TERMINAL_PROMPT", "0") in ("0", "")
