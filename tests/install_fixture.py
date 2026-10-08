"""A FamilyDB install that is well, on a temporary folder, for the tests of `maintain.sh check` and
`rescue`: the real code and migrations, a real git checkout and database, and stand-ins for what
would otherwise reach for root, systemd, the network or the machine's own disk and memory. A test
breaks one thing and reads the row it makes.

Each stand-in answers from an environment variable when a test wants it to be different:
  FAKE_PAGES      JSON of {"/path": [status, {"Header": "value"}, "body"] or null (refused)}
  FAKE_DF_FREE_MB, FAKE_DF_TOTAL_MB, FAKE_DF_INODE_PERCENT      what `df` says
  FAKE_SYSTEMD    JSON of what `systemctl show familydb` and `is-active`/`is-enabled` say
  FAKE_HELP_FAIL  a message `familydb --help` fails with
"""

from __future__ import annotations

# ruff: noqa: E501
# (the stand-in programs below are scripts in strings, kept as they would be written)
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")

CURL = r"""#!{python}
import json, os, sys

DEFAULT = {{
    "/healthz": [200, {{}}, "ok"],
    "/": [200, {{"Content-Type": "text/html", "Content-Security-Policy": "default-src 'self'"}}, "<html>FamilyDB</html>"],
    "/static/style.css": [200, {{"Content-Type": "text/css"}}, "a{{}}"],
}}
args, out, head, fmt, url, i = sys.argv[1:], None, None, "", "", 0
while i < len(args):
    a = args[i]
    if a in ("-o", "-D", "-w", "--max-time", "--resolve"):
        value = args[i + 1]
        if a == "-o":
            out = value
        elif a == "-D":
            head = value
        elif a == "-w":
            fmt = value
        i += 2
        continue
    if not a.startswith("-"):
        url = a
    i += 1
path = "/" + url.split("/", 3)[3] if url.count("/") >= 3 else "/"
pages = {{**DEFAULT, **json.loads(os.environ.get("FAKE_PAGES", "{{}}"))}}
page = pages.get(path)
if page is None:
    sys.exit(7)
status, headers, body = page
if head:
    with open(head, "w") as handle:
        handle.write("HTTP/1.1 %s X\r\n" % status + "".join("%s: %s\r\n" % pair for pair in headers.items()) + "\r\n")
if out and out != "/dev/null":
    with open(out, "w") as handle:
        handle.write(body)
elif not out:
    sys.stdout.write(body)
sys.stdout.write(fmt.replace("\\n", "\n").replace("%{{http_code}}", str(status)))
"""

PROGRAM = r"""#!{python}
import os, shutil, sys

args = sys.argv[1:]
if args[:1] == ["--help"]:
    if os.environ.get("FAKE_HELP_FAIL"):
        sys.stderr.write("Traceback (most recent call last):\n" + os.environ["FAKE_HELP_FAIL"] + "\n")
        sys.exit(1)
    print("Usage: familydb")
elif args[:1] == ["doctor"]:
    print(os.environ.get("FAKE_DOCTOR", "▸ Settings\n✓ settings: loaded\n\nEverything is set up."))
elif args[:2] == ["members", "list"]:
    print("#1 Sam [admin] telegram:1001 (signs in)\n#2 Alex [parent] no channel")
elif args[:2] == ["db", "backup"]:
    shutil.copy("data/familydb.sqlite3", args[2])
elif args[:2] == ["db", "migrate"]:
    sys.path.insert(0, {src!r})
    from familydb.store import db
    conn = db.connect("data/familydb.sqlite3")
    print("applied", db.migrate(conn))
    conn.close()
elif args[:1] == ["password"]:
    print("%s's password is now: correct-horse-battery" % (args[1] if len(args) > 1 else "Sam"))
elif args[:1] == ["run"]:
    pass
"""

SYSTEMCTL = r"""#!{python}
import json, os, sys

state = {{
    "active": "active", "enabled": "enabled", "SubState": "running", "NRestarts": "0", "Result": "success",
    "ExecMainStatus": "0", "NeedDaemonReload": "no", "ActiveEnterTimestamp": "Mon 2026-09-14 10:00:00 UTC",
    "caddy": "active",
}}
state.update(json.loads(os.environ.get("FAKE_SYSTEMD", "{{}}")))
args = [a for a in sys.argv[1:] if not a.startswith("--") or a == "--value"]
quiet = "--quiet" in sys.argv
if args[:1] == ["is-active"]:
    unit = args[1] if len(args) > 1 else "familydb"
    value = state["caddy"] if unit == "caddy" else state["active"]
    if not quiet:
        print(value)
    sys.exit(0 if value == "active" else 3)
if args[:1] == ["is-enabled"]:
    print(state["enabled"])
    sys.exit(0 if state["enabled"] == "enabled" else 1)
if args[:1] == ["show"]:
    key = args[args.index("-p") + 1]
    print(state.get(key, ""))
    sys.exit(0)
with open(os.environ.get("FAKE_SYSTEMCTL_LOG", os.devnull), "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\n")
"""

DF = r"""#!{python}
import os, sys

total = int(os.environ.get("FAKE_DF_TOTAL_MB", "50000"))
free = int(os.environ.get("FAKE_DF_FREE_MB", "30000"))
inode = os.environ.get("FAKE_DF_INODE_PERCENT", "10")
args = sys.argv[1:]
if "-Pi" in args:
    print("Filesystem Inodes IUsed IFree IUse% Mounted on")
    print("/dev/x 1000000 100000 900000 %s%% /" % inode)
elif "-Ph" in args:
    print("Filesystem Size Used Avail Use% Mounted on")
    print("/dev/x %dG %dG %dG %d%% /" % (total // 1000, (total - free) // 1000, free // 1000, 100 * (total - free) // total))
else:
    print("Filesystem 1M-blocks Used Available Capacity Mounted on")
    print("/dev/x %d %d %d %d%% /" % (total, total - free, free, 100 * (total - free) // total))
"""

SS = """#!/bin/sh
case "${FAKE_LISTEN:-python}" in
  none) ;;
  *) printf 'LISTEN 0 128 127.0.0.1:%s 0.0.0.0:* users:(("%s",pid=1,fd=3))\\n' "${FAKE_LISTEN_PORT:-8080}" "${FAKE_LISTEN:-python}"
     printf 'LISTEN 0 128 0.0.0.0:443 0.0.0.0:* users:(("caddy",pid=2,fd=3))\\n' ;;
esac
"""

SUDO = """#!/bin/sh
# sudo [-n] [-u USER] [--preserve-env...] CMD...: no passwords, no other users; just run the command.
while [ $# -gt 0 ]; do
  case "$1" in
    -n|-E|-H|-i|-S|-b) shift ;;
    -u|-g|-C|-D|-p|-r|-t|-U|-h) shift 2 ;;
    --preserve-env=*|--user=*|--group=*) shift ;;
    --) shift; break ;;
    *) break ;;
  esac
done
exec "$@"
"""

OPENSSL = """#!/bin/sh
case "$*" in
  *s_client*) [ "${FAKE_CERT:-yes}" = yes ] && echo CERT ;;
  *x509*) [ -n "$(cat)" ] || exit 1
          printf 'notAfter=%s\\nissuer=C = US, O = Let'"'"'s Encrypt, CN = R11\\n' "${FAKE_CERT_END:-Dec 31 23:59:59 2099 GMT}" ;;
esac
"""


def _write(path: Path, text: str, mode: int = 0o755) -> Path:
    path.write_text(text)
    path.chmod(mode)
    return path


def healthy_install(tmp_path: Path, *, docker: bool = False) -> tuple[Path, dict[str, str]]:
    """An install that `maintain.sh check` finds nothing wrong with, and the environment to run it in."""
    target = tmp_path / "install"
    target.mkdir()
    for name in ("pyproject.toml", ".env.example"):
        shutil.copy(ROOT / name, target / name)
    shutil.copytree(ROOT / "scripts", target / "scripts")
    shutil.copytree(ROOT / "deploy", target / "deploy")
    shutil.copytree(
        ROOT / "src", target / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    (target / "uv.lock").write_text(
        "version = 1\n"
    )  # no pins: what is installed here is the test's own
    (target / ".env").write_text("WEB_ENABLED=true\nWEB_PORT=8080\n")
    (target / ".env").chmod(0o600)
    data = target / "data"
    data.mkdir(mode=0o700)
    data.chmod(0o700)
    sys.path.insert(0, str(ROOT / "src"))
    from familydb.store import db

    with closing(db.connect(data / "familydb.sqlite3")) as conn:
        db.migrate(conn)
    (data / "familydb.sqlite3").chmod(0o600)
    backups = target / "backups"
    backups.mkdir()
    shutil.copy(data / "familydb.sqlite3", backups / "familydb-20260914030000.sqlite3")
    (backups / "familydb-20260914030000.sqlite3").chmod(0o600)

    git = ["git", "-C", str(target), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "remote", "add", "origin", "git@github.com:owner/repo.git"], check=True)
    # What an install tracks is the code, not what the install makes.
    (target / ".gitignore").write_text(".env\ndata/\nbackups/\n.venv/\n")
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "the install"], check=True)

    venv = target / ".venv" / "bin"
    venv.mkdir(parents=True)
    _write(venv / "python", f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    _write(venv / "familydb", PROGRAM.format(python=sys.executable, src=str(ROOT / "src")))
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    _write(stubs / "curl", CURL.format(python=sys.executable))
    _write(stubs / "systemctl", SYSTEMCTL.format(python=sys.executable))
    _write(stubs / "df", DF.format(python=sys.executable))
    _write(stubs / "ss", SS)
    _write(stubs / "sudo", SUDO)
    _write(stubs / "uv", "#!/bin/sh\nexit 0\n")
    _write(stubs / "timedatectl", "#!/bin/sh\necho yes\n")
    _write(stubs / "findmnt", "#!/bin/sh\necho rw,relatime\n")
    _write(stubs / "hostname", "#!/bin/sh\necho 203.0.113.9\n")
    _write(stubs / "journalctl", "#!/bin/sh\nexit 0\n")
    _write(
        stubs / "crontab",
        '#!/bin/sh\n[ "$1" = "-u" ] && [ "$2" = root ] && echo "15 3 * * * /bin/true # familydb-maintain-backup"\nexit 0\n',
    )
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 4096000 kB\nMemAvailable: 2048000 kB\nSwapTotal: 1024000 kB\n")
    if docker:
        (venv / "familydb").unlink()
        shutil.copy(ROOT / "docker-compose.yml", target / "docker-compose.yml")
    env_path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    env = {
        "PATH": env_path,
        "NO_COLOR": "1",
        "COLUMNS": "100",
        "LC_ALL": "C.UTF-8",
        "FAMILYDB_SERVICE_UNIT": str(tmp_path / "no-such.service"),
        "FAMILYDB_LEDGER_DIR": str(tmp_path / "ledger"),
        "FAMILYDB_MEMINFO": str(meminfo),
        "FAMILYDB_SYSTEM_PATH": env_path,
        "TMPDIR": str(tmp_path),
        "HOME": str(tmp_path),
        "GITHUB_TOKEN": "",
    }
    return target, env


def stub(env: dict[str, str], name: str, text: str) -> Path:
    """Add or replace a command on the install's PATH."""
    folder = Path(env["PATH"].split(os.pathsep)[0])
    return _write(folder / name, text)


def unit_file(tmp_path: Path, env: dict[str, str], target: Path, **changes: str) -> Path:
    """A systemd unit for the install, as the installer writes it, with changes."""
    text = (ROOT / "deploy" / "familydb.service").read_text().replace("/opt/familydb", str(target))
    user = (
        os.environ.get("USER")
        or subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
    )
    text = re.sub(r"^User=.*$", f"User={user}", text, flags=re.M)
    text = re.sub(r"^Group=.*$", "", text, flags=re.M)
    for key, value in changes.items():
        text = re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
    path = tmp_path / "familydb.service"
    path.write_text(text)
    env["FAMILYDB_SERVICE_UNIT"] = str(path)
    return path


def me() -> str:
    return subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()


def maintain(
    target: Path,
    env: dict[str, str],
    *args: str,
    stdin: str | None = None,
    **more_env: str,
) -> subprocess.CompletedProcess[str]:
    """`scripts/maintain.sh ARGS --target T --user ME`, as the account that owns the install."""
    return subprocess.run(
        [
            BASH,
            str(target / "scripts" / "maintain.sh"),
            *args,
            "--target",
            str(target),
            "--user",
            me(),
        ],
        env={**os.environ, **env, **more_env},
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL if stdin is None else None,
        input=stdin,
    )


ROW = re.compile(r"^ +([✓!✗○]) (.+?)(?: {2,}(.*))?$")


def rows(output: str) -> dict[str, tuple[str, str]]:
    """The check's rows by name: the mark, and the detail with its wrapped lines joined."""
    found: dict[str, tuple[str, str]] = {}
    last = None
    for line in output.splitlines():
        match = ROW.match(line)
        if match and not line.lstrip().startswith(("→", "Start here")):
            name = match.group(2).strip()
            found[name] = (match.group(1), match.group(3) or "")
            last = name
        elif last and line.startswith("          ") and not line.strip().startswith("→"):
            mark, detail = found[last]
            found[last] = (mark, f"{detail} {line.strip()}")
        elif line.strip() == "":
            last = None
    return found


def age_file(path: Path, hours: int) -> None:
    then = time.time() - hours * 3600
    os.utime(path, (then, then))


def corrupt(path: Path) -> None:
    """A database file SQLite cannot read as one."""
    path.write_bytes(b"this is not a database" * 500)


def drop_last_migration(path: Path) -> None:
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            "delete from schema_version where version = (select max(version) from schema_version)"
        )
        conn.commit()


def maintain_on_tty(
    target: Path, env: dict[str, str], *args: str, keys: str = "", **more_env: str
) -> tuple[int, str]:
    """The same, with a terminal for its input and output and `keys` already typed: what a person
    at the keyboard sees, and answers, when it asks."""
    import pty

    master, slave = pty.openpty()
    process = subprocess.Popen(
        [
            BASH,
            str(target / "scripts" / "maintain.sh"),
            *args,
            "--target",
            str(target),
            "--user",
            me(),
        ],
        env={**os.environ, **env, "TERM": "xterm", "FAMILYDB_NO_LIVE": "1", **more_env},
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)
    os.write(master, keys.encode())
    shown = b""
    while True:
        try:
            data = os.read(master, 4096)
        except OSError:
            break
        if not data:
            break
        shown += data
    code = process.wait(timeout=120)
    os.close(master)
    return code, shown.decode("utf-8", "replace").replace("\r\n", "\n")


def git(target: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(target), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def logging_stub(env: dict[str, str], name: str, log: Path, body: str = "") -> None:
    """A command that writes down how it was called (in `log`) and does what `body` says."""
    stub(env, name, f'#!/bin/sh\necho "{name} $*" >> "{log}"\n{body}\n')


def database_behind(path: Path) -> None:
    """The database as an older version left it: every migration but the newest applied, so that
    `db migrate` has something real to do (a deleted row of schema_version would make it fail
    on tables that already exist)."""
    sys.path.insert(0, str(ROOT / "src"))
    from familydb.store import db

    path.unlink()
    with closing(db.connect(path)) as conn:
        db.schema_version(conn)
        for version, _name, sql in db.list_migrations()[:-1]:
            keys_off = sql.startswith(db.FOREIGN_KEYS_OFF)
            if keys_off:
                conn.execute("PRAGMA foreign_keys=OFF")
            conn.executescript(
                f"BEGIN;\n{sql}\nINSERT INTO schema_version (version, applied_at) "
                f"VALUES ({version}, 'x');\nCOMMIT;"
            )
            if keys_off:
                conn.execute("PRAGMA foreign_keys=ON")
    path.chmod(0o600)
