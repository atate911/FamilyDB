"""The page on another port than 443: the Caddyfile, the port chosen, and the address shown.

These run the real functions in scripts/lib/https.sh, with nothing but root's `tee` and the
installer's ledger stood in for, so what is tested is what writes /etc/caddy/Caddyfile.
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
