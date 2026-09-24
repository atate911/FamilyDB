"""`uninstall.sh --from-zero` really runs, on a fake server, and leaves only what was there before.

It deletes things all over a machine, so it runs inside a private mount namespace where /root,
/home, /opt, /var/log and the rest are empty throwaway folders. That needs root and a kernel that
allows it, which a laptop or CI usually does not give, so the test is skipped there. The two
answers (yes, then the words typed out) go in through a pseudo-terminal, as a person's would.
"""

# ruff: noqa: E501  (the fake server is a shell script, written as a person would type it)
from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

SETUP = r"""
set -e
mount -t tmpfs none /mnt && cp -r "$1/." /mnt/ && SRC=/mnt
for d in /root /home /usr/local/bin /var/log /var/backups /opt /tmp /etc/systemd/system /var/lib; do
  mount -t tmpfs none "$d"
done
# FamilyDB, and what a person or an older version left around it.
mkdir -p /opt/familydb/data /opt/familydb/scripts
cp "$SRC/pyproject.toml" /opt/familydb/; cp -r "$SRC/scripts/." /opt/familydb/scripts/
printf 'WEB_PASSWORD=x\nWEB_DOMAIN=203.0.113.7\n' > /opt/familydb/.env
: > /opt/familydb/data/familydb.sqlite3
git -C /opt/familydb init -q
git -C /opt/familydb remote add origin git@github.com:atate911/FamilyDB.git
git -C /opt/familydb config core.sshCommand "ssh -i /root/familydb_deploy -o IdentitiesOnly=yes"
printf -- '-----BEGIN OPENSSH PRIVATE KEY-----\n' > /root/familydb_deploy; echo pub > /root/familydb_deploy.pub
mkdir -p /root/familydb-code /root/FamilyDB /home/sam/FamilyDB/.git /home/sam/notes
for d in /root/familydb-code /root/FamilyDB /home/sam/FamilyDB; do cp "$SRC/pyproject.toml" "$d/"; done
echo tar > /root/familydb.tar.gz; echo db > /home/sam/familydb-20260920.sqlite3
mkdir -p /root/.local/bin /root/.config/uv /root/.ssh
for f in uv uvx env; do echo "$f" > "/root/.local/bin/$f"; done; echo other > /root/.local/bin/black
printf '# the usual\nexport EDITOR=vi\n. "$HOME/.local/bin/env"\n' > /root/.profile
echo '{}' > /root/.config/uv/uv-receipt.json
printf 'github.com ssh-ed25519 AAAA\nother.example ssh-ed25519 BBBB\n' > /root/.ssh/known_hosts
echo keys > /root/.ssh/authorized_keys
echo uv > /usr/local/bin/uv; echo uvx > /usr/local/bin/uvx; echo keep > /usr/local/bin/something-else
echo log > /var/log/familydb-bootstrap.log; echo step > /var/log/familydb-bootstrap.progress
echo sys > /var/log/syslog
mkdir -p /var/backups/familydb; echo db > /var/backups/familydb/old.sqlite3; echo x > /var/backups/other.bak
echo unit > /etc/systemd/system/familydb.service; echo other > /etc/systemd/system/other.service
echo x > /tmp/unrelated
mkdir -p /opt/other; echo changed > /opt/other/app.conf
if [ "$LEDGER_KIND" = whole ]; then
  mkdir -p /var/lib/familydb-install/saved/opt/other
  echo original > /var/lib/familydb-install/saved/opt/other/app.conf
  printf 'began\t2026-09-24T00:00:00Z\nfile\t/etc/systemd/system/familydb.service\ndir\t/opt/familydb\nreplaced\t/opt/other/app.conf\n' \
    > /var/lib/familydb-install/ledger
fi
python3 "$SRC/drive.py"
echo "=== after"
for d in /root /home /usr/local/bin /var/log /var/backups /opt /etc/systemd/system /tmp /var/lib; do
  find "$d" -mindepth 1 2>/dev/null
done | sort
echo "=== profile"; cat /root/.profile
echo "=== known_hosts"; cat /root/.ssh/known_hosts
echo "=== app.conf"; cat /opt/other/app.conf
"""

DRIVE = r"""
import os, pty, select, time
pid, fd = pty.fork()
if pid == 0:
    os.chdir("/")
    os.execvp("bash", ["bash", "/opt/familydb/scripts/uninstall.sh", "--from-zero"])
out = b""
def drain(seconds):
    global out
    end = time.time() + seconds
    while time.time() < end:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if ready:
            try:
                data = os.read(fd, 65536)
            except OSError:
                return
            if not data:
                return
            out += data
for answer in ("y", "remove everything"):
    drain(3)
    os.write(fd, answer.encode() + b"\r")
drain(8)
print(out.decode(errors="replace"))
"""


def _namespaces_work() -> bool:
    if os.geteuid() != 0 or shutil.which("unshare") is None or shutil.which("git") is None:
        return False
    tried = subprocess.run(
        ["unshare", "-m", "--propagation", "private", "true"], capture_output=True
    )
    return tried.returncode == 0


pytestmark = pytest.mark.skipif(
    not _namespaces_work(), reason="needs root and mount namespaces, to delete nothing real"
)


def _run(tmp_path: Path, ledger: str) -> tuple[str, list[str]]:
    source = tmp_path / "source"
    shutil.copytree(ROOT / "scripts", source / "scripts")
    shutil.copy(ROOT / "pyproject.toml", source / "pyproject.toml")
    (source / "drive.py").write_text(textwrap.dedent(DRIVE))
    setup = tmp_path / "setup.sh"
    setup.write_text(SETUP)
    done = subprocess.run(
        ["unshare", "-m", "--propagation", "private", "bash", str(setup), str(source)],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "LEDGER_KIND": ledger},
        cwd="/",
    )
    output = done.stdout + done.stderr
    after = output.split("=== after", 1)[1].split("=== profile", 1)[0].split()
    return output, after


# What was there before FamilyDB, and must still be there after, whichever way it was installed.
NOT_OURS = {
    "/etc/systemd/system/other.service",
    "/home/sam/FamilyDB",  # somebody's working clone: it has a .git of its own
    "/home/sam/notes",
    "/opt/other/app.conf",
    "/root/.local/bin/black",
    "/root/.ssh/authorized_keys",
    "/tmp/unrelated",
    "/usr/local/bin/something-else",
    "/var/backups/other.bak",
    "/var/log/syslog",
}


def test_an_install_from_before_the_ledger_leaves_nothing_of_familydb(tmp_path) -> None:
    output, after = _run(tmp_path, "none")
    assert "stopped unexpectedly" not in output and "✗" not in output, output
    assert set(after) >= NOT_OURS, sorted(NOT_OURS - set(after))
    left = [
        path
        for path in after
        if path not in NOT_OURS
        and not path.startswith(
            ("/home/sam", "/root/.local", "/root/.ssh", "/root/.profile", "/opt/other")
        )
    ]
    assert left == [], left
    assert not [
        p
        for p in after
        if "uv" in p.rsplit("/", 1)[-1]
        or ("familydb" in p.lower() and not p.startswith("/home/sam/FamilyDB"))
    ]
    profile = output.split("=== profile", 1)[1].split("=== known_hosts", 1)[0]
    assert "export EDITOR=vi" in profile and ".local/bin/env" not in profile
    known = output.split("=== known_hosts", 1)[1].split("=== app.conf", 1)[0]
    assert "other.example" in known and "github.com" not in known


def test_a_whole_ledger_undoes_what_it_recorded_and_nothing_else(tmp_path) -> None:
    output, after = _run(tmp_path, "whole")
    assert "stopped unexpectedly" not in output and "✗" not in output, output
    assert set(after) >= NOT_OURS
    # Not in the ledger, so here before FamilyDB: a uv of somebody's own, and GitHub's host key.
    assert {"/root/.local/bin/uv", "/usr/local/bin/uv"} <= set(after)
    assert "github.com" in output.split("=== known_hosts", 1)[1]
    # In the ledger, or named for FamilyDB: gone. The replaced file is as it was.
    for gone in (
        "/opt/familydb",
        "/root/familydb_deploy",
        "/var/lib/familydb-install",
        "/var/backups/familydb",
        "/var/log/familydb-bootstrap.log",
        "/etc/systemd/system/familydb.service",
        "/root/familydb-code",
        "/root/FamilyDB",
    ):
        assert gone not in after, gone
    assert output.split("=== app.conf", 1)[1].strip().startswith("original")
