"""The page's ports: the one it is served on over HTTPS (443 unless moved), and FamilyDB's own.

These run the real functions in scripts/lib/https.sh and scripts/maintain.sh, with nothing but
root, the ledger, systemd, Docker and Caddy's reload stood in for, so what is tested is what
writes /etc/caddy/Caddyfile and .env.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(not BASH or os.name == "nt", reason="needs bash")

HARNESS = r"""
set -euo pipefail
. scripts/lib/common.sh
. scripts/lib/https.sh
as_root() { "$@"; }
noting_replaced() { :; }
"""
HEADER = "# FamilyDB, written by its installer. `sudo /opt/familydb/scripts/maintain.sh https` writes it again.\n"  # noqa: E501


def _shell(script: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, "-c", HARNESS + script],
        cwd=ROOT,
        env={**os.environ, "NO_COLOR": "1", **env},
        capture_output=True,
        text=True,
        timeout=60,
    )


def _caddyfile(tmp_path: Path, site: str, how: str, port: str = "443") -> str:
    target = tmp_path / f"Caddyfile-{how}-{port}"
    done = _shell(
        f'CADDYFILE="{target}"; PUBLIC_PORT={port}; write_caddyfile {site} 8080 {how}',
        TARGET="/opt/familydb",
    )
    assert done.returncode == 0, done.stderr
    return target.read_text()


def test_on_443_the_caddyfile_is_what_it_always_was(tmp_path) -> None:
    assert _caddyfile(tmp_path, "family.example.com", "domain") == (
        HEADER + "family.example.com {\n\treverse_proxy 127.0.0.1:8080\n}\n"
    )
    assert _caddyfile(tmp_path, "203.0.113.7", "internal") == (
        HEADER + "203.0.113.7 {\n\ttls internal\n\treverse_proxy 127.0.0.1:8080\n}\n"
    )
    assert "profile shortlived" in _caddyfile(tmp_path, "203.0.113.7", "public-ip")
    assert "https_port" not in _caddyfile(tmp_path, "203.0.113.7", "public-ip")


def test_on_its_own_port_nothing_on_80_gives_it_away(tmp_path) -> None:
    domain = _caddyfile(tmp_path, "family.example.com", "domain", "24613")
    assert domain == HEADER + (
        "{\n\thttps_port 24613\n\tauto_https disable_redirects\n}\n"
        "family.example.com {\n"
        "\ttls {\n\t\tissuer acme {\n\t\t\tdisable_tlsalpn_challenge\n\t\t}\n\t}\n"
        "\treverse_proxy 127.0.0.1:8080\n}\n"
    )
    address = _caddyfile(tmp_path, "203.0.113.7", "public-ip", "24613")
    assert "\t\t\tprofile shortlived\n\t\t\tdisable_tlsalpn_challenge\n" in address
    internal = _caddyfile(tmp_path, "203.0.113.7", "internal", "24613")
    assert "auto_https disable_redirects" in internal and "tls internal" in internal
    assert "issuer acme" not in internal  # no certificate authority to be checked by


@pytest.mark.skipif(not shutil.which("caddy"), reason="caddy is not installed here")
@pytest.mark.parametrize("how", ["domain", "public-ip", "internal"])
@pytest.mark.parametrize("port", ["443", "24613"])
def test_caddy_itself_accepts_every_caddyfile(tmp_path, how, port) -> None:
    site = "family.example.com" if how == "domain" else "203.0.113.7"
    path = tmp_path / "Caddyfile"
    path.write_text(_caddyfile(tmp_path, site, how, port))
    checked = subprocess.run(
        ["caddy", "validate", "--adapter", "caddyfile", "--config", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "XDG_DATA_HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path)},
    )
    assert checked.returncode == 0, checked.stderr


def test_a_random_port_is_one_scans_rarely_try() -> None:
    done = _shell(
        'for n in $(seq 200); do choose_public_port random 8080; printf "\\n"; done; '
        'printf "%s" "$NMAP_FAVOURITES"'
    )
    assert done.returncode == 0, done.stderr
    *picked, favourites = done.stdout.split("\n")
    ports = [int(port) for port in picked if port]
    shunned = {int(port) for port in favourites.split()}
    assert len(ports) == 200 and len(set(ports)) > 150  # spread across the range
    assert all(20000 <= port <= 29999 for port in ports)
    assert not shunned & set(ports)
    assert len(shunned) == 24 and all(20000 <= port <= 29999 for port in shunned)


@pytest.mark.parametrize(
    ("wanted", "chosen"),
    [("443", "443"), ("24613", "24613"), ("01234", "1234"), ("65535", "65535")],
)
def test_a_port_that_will_do_is_kept(wanted, chosen) -> None:
    done = _shell(f"choose_public_port {wanted} 8080")
    assert done.returncode == 0 and done.stdout == chosen, done.stderr


@pytest.mark.parametrize(
    ("wanted", "why"),
    [
        ("80", "443, or one from 1024"),
        ("22", "443, or one from 1024"),
        ("65536", "443, or one from 1024"),
        ("99999999999999999999", "443, or one from 1024"),  # never wraps round into range
        ("8080", "where FamilyDB itself listens"),
        ("eighty", "not a port number"),
        ("''", "not a port number"),
    ],
)
def test_a_port_that_will_not_do_says_why(wanted, why) -> None:
    done = _shell(f"choose_public_port {wanted} 8080")
    assert done.returncode != 0 and why in done.stderr and done.stdout == ""


def test_the_address_carries_the_port_unless_it_is_443() -> None:
    done = _shell("public_url family.example.com; echo; PUBLIC_PORT=24613; public_url 203.0.113.7")
    assert done.stdout.split() == ["https://family.example.com/", "https://203.0.113.7:24613/"]


def test_the_firewall_rule_follows_the_port() -> None:
    done = _shell("web_ports_rule; echo; PUBLIC_PORT=24613; web_ports_rule")
    assert done.stdout.split() == ["80,443/tcp", "80,24613/tcp"]


def test_maintain_explains_how_to_move_it() -> None:
    usage = subprocess.run(
        [BASH, "scripts/maintain.sh", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
        timeout=60,
    ).stdout
    assert "https [DOMAIN] [--port N|random|443]" in usage
    assert "maintain.sh https --port random" in usage


# -- FamilyDB's own port ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("wanted", "chosen"), [("9090", "9090"), ("01025", "1025"), ("65535", "65535")]
)
def test_a_port_for_familydb_itself_that_will_do_is_kept(wanted, chosen) -> None:
    done = _shell(f"port_listening() {{ return 1; }}; choose_app_port {wanted} 443 8080")
    assert done.returncode == 0 and done.stdout == chosen, done.stderr


@pytest.mark.parametrize(
    ("wanted", "public", "why"),
    [
        ("1024", "443", "one from 1025 to 65535"),  # FamilyDB runs unprivileged
        ("443", "443", "one from 1025 to 65535"),
        ("65536", "443", "one from 1025 to 65535"),
        ("99999999999999999999", "443", "one from 1025 to 65535"),
        ("24613", "24613", "where Caddy serves the page"),
        ("9091", "443", "already listens on port 9091"),
        ("eighty", "443", "not a port number"),
        ("''", "443", "not a port number"),
    ],
)
def test_a_port_for_familydb_itself_that_will_not_do_says_why(wanted, public, why) -> None:
    busy = 'port_listening() { [ "$1" = 9091 ] || [ "$1" = 8080 ]; }; '
    done = _shell(f"{busy}choose_app_port {wanted} {public} 8080")
    assert done.returncode != 0 and why in done.stderr and done.stdout == ""


def test_the_port_it_is_on_already_is_not_taken_for_somebody_else() -> None:
    done = _shell('port_listening() { [ "$1" = 8080 ]; }; choose_app_port 8080 443 8080')
    assert done.returncode == 0 and done.stdout == "8080"


def test_a_random_port_for_familydb_is_never_the_one_caddy_serves() -> None:
    busy = 'port_listening() { [ "$1" = 24613 ]; }; '
    done = _shell(busy + "for n in $(seq 100); do choose_app_port random 24613 8080; echo; done")
    ports = [int(port) for port in done.stdout.split()]
    assert len(ports) == 100 and 24613 not in ports
    assert all(20000 <= port <= 29999 for port in ports)


def _caddy(tmp_path: Path, script: str, **env: str) -> subprocess.CompletedProcess[str]:
    return _shell(
        f'CADDYFILE="{tmp_path / "Caddyfile"}"; '
        'caddy_reload() { [ "${CADDY_REFUSES:-0}" = 0 ]; }; ' + script,
        **env,
    )


def test_caddy_follows_familydb_to_its_new_port(tmp_path) -> None:
    written = _caddyfile(tmp_path, "family.example.com", "domain", "24613")
    (tmp_path / "Caddyfile").write_text(written)
    done = _caddy(tmp_path, "caddy_follows 8080 9090")
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "Caddyfile").read_text() == written.replace(
        "reverse_proxy 127.0.0.1:8080", "reverse_proxy 127.0.0.1:9090"
    )


def test_a_change_caddy_refuses_puts_the_old_caddyfile_back(tmp_path) -> None:
    written = _caddyfile(tmp_path, "203.0.113.7", "public-ip", "24613")
    (tmp_path / "Caddyfile").write_text(written)
    done = _caddy(tmp_path, "caddy_follows 8080 9090", CADDY_REFUSES="1")
    assert done.returncode == 1
    assert (tmp_path / "Caddyfile").read_text() == written


def test_a_caddyfile_that_passes_nothing_on_to_familydb_is_left_alone(tmp_path) -> None:
    theirs = "example.org {\n\treverse_proxy 127.0.0.1:3000\n}\n"
    (tmp_path / "Caddyfile").write_text(theirs)
    done = _caddy(tmp_path, "caddy_follows 8080 9090")
    assert done.returncode == 2 and (tmp_path / "Caddyfile").read_text() == theirs
    missing = _caddy(tmp_path / "nowhere", "caddy_follows 8080 9090")
    assert missing.returncode == 2


def _maintain_function(name: str) -> str:
    script = (ROOT / "scripts/maintain.sh").read_text()
    start = script.index(f"{name}() {{")
    line_end = script.index("\n", start)
    if script[start:line_end].rstrip().endswith("}"):
        return script[start:line_end] + "\n"
    return script[start : script.index("\n}\n", start) + 3]


def _port(tmp_path: Path, command: str, env_file: str, **env: str):
    """Run one of maintain.sh's commands against an install in tmp_path: what it said, and every
    command it asked root, systemd or Docker to run."""
    (tmp_path / ".env").write_text(env_file)
    calls = tmp_path / "calls"
    calls.unlink(missing_ok=True)
    stubs = (
        f'TARGET="{tmp_path}"; CADDYFILE="{tmp_path / "Caddyfile"}"; CALLS="{calls}"\n'
        'caddy_reload() { echo "caddy reload" >> "$CALLS"; [ "${CADDY_REFUSES:-0}" = 0 ]; }\n'
        'systemctl() { echo "systemctl $*" >> "$CALLS"; }\n'
        'docker() { echo "docker $*" >> "$CALLS"; }\n'
        'service_installed() { [ "${SERVICE:-1}" = 1 ]; }\n'
        'port_listening() { case " ${BUSY:-} " in *" $1 "*) return 0 ;; esac; return 1; }\n'
        "this_address() { printf 203.0.113.7; }\n"
    )
    functions = "".join(
        _maintain_function(name)
        for name in ("env_file_value", "env_file_set", "https_port_in_docker", "cmd_port")
    )
    defaults = {"DOCKER_MODE": "0", "APP_PORT": "", "HTTPS_PORT": "", "SUDO_USER": "sam"}
    done = _shell(stubs + functions + command, **{**defaults, **env})
    said = calls.read_text().splitlines() if calls.exists() else []
    return done, said


def test_moving_familydb_moves_caddy_and_restarts_it(tmp_path) -> None:
    written = _caddyfile(tmp_path, "family.example.com", "domain")
    (tmp_path / "Caddyfile").write_text(written)
    env = "WEB_HOST=127.0.0.1\nWEB_PORT=8080\nWEB_DOMAIN=family.example.com\n"
    done, calls = _port(tmp_path, "cmd_port", env, APP_PORT="9090")
    assert done.returncode == 0, done.stderr
    assert "WEB_PORT=9090" in (tmp_path / ".env").read_text()
    assert "reverse_proxy 127.0.0.1:9090" in (tmp_path / "Caddyfile").read_text()
    assert calls == ["caddy reload", "systemctl restart familydb"]
    assert "still at https://family.example.com/: only the port behind Caddy moved" in done.stdout


def test_when_caddy_refuses_nothing_is_moved(tmp_path) -> None:
    written = _caddyfile(tmp_path, "family.example.com", "domain")
    (tmp_path / "Caddyfile").write_text(written)
    env = "WEB_PORT=8080\nWEB_DOMAIN=family.example.com\n"
    done, calls = _port(tmp_path, "cmd_port", env, APP_PORT="9090", CADDY_REFUSES="1")
    assert done.returncode != 0 and "Caddy would not load the change" in done.stderr
    assert "WEB_PORT=8080" in (tmp_path / ".env").read_text()
    assert (tmp_path / "Caddyfile").read_text() == written
    assert "systemctl restart familydb" not in calls


def test_with_nothing_in_front_the_port_moved_is_the_one_people_open(tmp_path) -> None:
    done, calls = _port(tmp_path, "cmd_port", "WEB_HOST=0.0.0.0\nWEB_PORT=8080\n", APP_PORT="9090")
    assert done.returncode == 0, done.stderr
    assert calls == ["systemctl restart familydb"]
    assert "The page: http://203.0.113.7:9090/" in done.stdout
    assert "sudo ufw allow 9090/tcp && sudo ufw delete allow 8080/tcp" in done.stdout
    loopback, _ = _port(tmp_path, "cmd_port", "WEB_PORT=9090\n", APP_PORT="9191")
    assert "ssh -L 9191:127.0.0.1:9191 sam@203.0.113.7" in loopback.stdout


def test_with_docker_the_containers_start_again_on_the_new_port(tmp_path) -> None:
    env = "WEB_PORT=8080\nWEB_DOMAIN=family.example.com\nCOMPOSE_PROFILES=tls\n"
    done, calls = _port(tmp_path, "cmd_port", env, APP_PORT="9090", DOCKER_MODE="1")
    assert done.returncode == 0, done.stderr
    assert "WEB_PORT=9090" in (tmp_path / ".env").read_text()
    assert calls == [f"docker compose --project-directory {tmp_path} up -d"]


def test_the_port_it_is_on_or_one_taken_changes_nothing(tmp_path) -> None:
    same, calls = _port(tmp_path, "cmd_port", "WEB_PORT=8080\n", APP_PORT="8080")
    assert same.returncode == 0 and "Nothing to do" in same.stdout and calls == []
    taken, calls = _port(tmp_path, "cmd_port", "WEB_PORT=8080\n", APP_PORT="9090", BUSY="9090")
    assert taken.returncode != 0 and "already listens on port 9090" in taken.stderr
    assert "WEB_PORT=8080" in (tmp_path / ".env").read_text() and calls == []


def test_with_docker_https_moves_the_caddy_containers_port(tmp_path) -> None:
    env = "WEB_PORT=8080\nWEB_DOMAIN=family.example.com\nCOMPOSE_PROFILES=tls\n"
    done, calls = _port(tmp_path, "https_port_in_docker", env, HTTPS_PORT="24613")
    assert done.returncode == 0, done.stderr
    assert "WEB_PUBLIC_PORT=24613" in (tmp_path / ".env").read_text()
    assert calls == [f"docker compose --project-directory {tmp_path} up -d"]
    assert "The page: https://family.example.com:24613/" in done.stdout
    # With no domain there is no Caddy container to move: it says how to have one.
    bare, calls = _port(tmp_path, "https_port_in_docker", "WEB_PORT=8080\n", HTTPS_PORT="24613")
    assert bare.returncode != 0 and "COMPOSE_PROFILES=tls" in bare.stderr and calls == []


def test_maintain_explains_how_to_move_familydbs_own_port() -> None:
    usage = subprocess.run(
        [BASH, "scripts/maintain.sh", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
        timeout=60,
    ).stdout
    assert "port N|random" in usage and "maintain.sh port 9090" in usage


def test_with_docker_a_port_something_else_listens_on_changes_nothing(tmp_path) -> None:
    env = "WEB_PORT=8080\nWEB_DOMAIN=family.example.com\nCOMPOSE_PROFILES=tls\n"
    done, calls = _port(tmp_path, "https_port_in_docker", env, HTTPS_PORT="8443", BUSY="8443")
    assert done.returncode != 0 and "already listens on port 8443" in done.stderr
    assert "WEB_PUBLIC_PORT" not in (tmp_path / ".env").read_text() and calls == []
