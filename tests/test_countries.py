"""The country filter (`maintain.sh countries`, scripts/lib/countries.sh): what it lets in, the
rules it writes, and the lists it will and will not use. The rules are checked by nftables itself
where it is installed, and loaded into a network namespace of their own where that is allowed."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.test_https_port import BASH, ROOT

pytestmark = pytest.mark.skipif(not BASH or os.name == "nt", reason="needs bash")

HARNESS = r"""
set -euo pipefail
. scripts/lib/common.sh
. scripts/lib/countries.sh
as_root() { "$@"; }
"""


def _shell(script: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, "-c", HARNESS + script],
        cwd=ROOT,
        env={**os.environ, "NO_COLOR": "1", **env},
        capture_output=True,
        text=True,
        timeout=60,
    )


def _filter(tmp_path: Path, v4: str, v6: str = "", allow: str = "") -> Path:
    (tmp_path / "lists").mkdir(exist_ok=True)
    (tmp_path / "countries").write_text("US\n")
    (tmp_path / "lists" / "US.v4").write_text(v4)
    (tmp_path / "lists" / "US.v6").write_text(v6)
    (tmp_path / "allow").write_text("# let in from anywhere\n" + allow)
    done = _shell("countries_rules", COUNTRIES_DIR=str(tmp_path))
    assert done.returncode == 0, done.stderr
    rules = tmp_path / "rules.nft"
    rules.write_text(done.stdout)
    return rules


def test_addresses_and_codes_are_told_apart() -> None:
    done = _shell(
        "for a in 203.0.113.7 23.0.0.0/8 2600:1f18::1 2600::/12 US us 999 host.example.com; do "
        'if is_address "$a"; then echo "$a address"; elif is_country_code "$a"; then '
        'echo "$a country"; else echo "$a neither"; fi; done'
    )
    assert done.stdout.split("\n")[:-1] == [
        "203.0.113.7 address",
        "23.0.0.0/8 address",
        "2600:1f18::1 address",
        "2600::/12 address",
        "US country",
        "us country",
        "999 neither",
        "host.example.com neither",
    ]


def test_only_a_sound_list_is_used(tmp_path) -> None:
    good = tmp_path / "good"
    good.write_text("".join(f"{n}.0.0.0/8\n" for n in range(1, 101)))
    shrunk = tmp_path / "shrunk"
    shrunk.write_text("1.0.0.0/8\n2.0.0.0/8\n")
    page = tmp_path / "page"
    page.write_text("<html>rate limited</html>\n")
    empty = tmp_path / "empty"
    empty.write_text("")
    v6 = tmp_path / "v6"
    v6.write_text("2600::/12\n2001:db8::/32\n")
    done = _shell(
        f'for f in {good} {page} {empty}; do list_is_sound v4 "$f" && echo yes || echo no; done; '
        f"list_is_sound v4 {shrunk} {good} && echo yes || echo no; "
        f"list_is_sound v4 {good} {shrunk} && echo yes || echo no; "
        f"list_is_sound v6 {v6} && echo yes || echo no; "
        f"list_is_sound v4 {v6} && echo yes || echo no"
    )
    # a good list; an error page; nothing; one that shrank by half since last week; one that grew;
    # an IPv6 list, which is not an IPv4 one.
    assert done.stdout.split() == ["yes", "no", "no", "no", "yes", "yes", "no"]


def test_the_rules_let_in_the_country_the_allowed_and_what_this_machine_asked_for(tmp_path) -> None:
    allow = "23.234.83.83 on SSH\n2001:db8::7 mine\n"
    rules = _filter(tmp_path, "3.0.0.0/8\n23.0.0.0/8\n", "2600::/12\n", allow).read_text()
    assert "table inet familydb_countries\ndelete table inet familydb_countries\n" in rules
    for allowed in ("3.0.0.0/8", "23.0.0.0/8", "23.234.83.83", "10.0.0.0/8", "100.64.0.0/10"):
        assert f"      {allowed}" in rules
    for allowed in ("2600::/12", "2001:db8::7", "fe80::/10"):
        assert f"      {allowed}" in rules
    assert "let in from anywhere" not in rules.split("{", 1)[1]  # the allow file's comment
    gate = rules.split("chain gate {")[1].split("\n  }")[0]
    assert gate.index('iif "lo" accept') < gate.index("ct state established,related accept")
    assert gate.rstrip().endswith("counter drop")
    assert "hook input priority -10" in rules and "hook forward priority -10" in rules


@pytest.mark.skipif(not shutil.which("nft"), reason="needs nftables")
def test_nftables_takes_the_rules_as_written(tmp_path) -> None:
    lots = "".join(f"{a}.{b}.0.0/16\n" for a in range(1, 224, 3) for b in range(0, 256, 4))
    rules = _filter(tmp_path, lots + "23.234.0.0/16\n", "", "23.234.83.83 overlaps the list\n")
    checked = subprocess.run(["nft", "-c", "-f", str(rules)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr


@pytest.mark.skipif(not shutil.which("nft") or not shutil.which("unshare"), reason="needs nft")
def test_the_rules_load_and_load_again_in_place(tmp_path) -> None:
    rules = _filter(tmp_path, "3.0.0.0/8\n", "", "23.234.83.83\n")
    loaded = subprocess.run(
        ["unshare", "-rn", "sh", "-c", f"nft -f {rules} && nft -f {rules} && nft list tables"],
        capture_output=True,
        text=True,
    )
    if loaded.returncode != 0 and "Operation not permitted" in loaded.stderr:
        pytest.skip("no network namespace here")
    assert loaded.returncode == 0, loaded.stderr
    assert loaded.stdout.split() == ["table", "inet", "familydb_countries"]


def test_whoever_is_on_ssh_is_found(tmp_path) -> None:
    stubs = (
        "who() { echo 'atate pts/0 2026-09-28 06:40 (23.234.83.83)'; }\n"
        "ss() { printf '%s\\n' '0 0 162.222.205.48:22 23.234.83.83:51234' "
        "'0 0 [::ffff:162.222.205.48]:22 [::ffff:198.51.100.9]:40000' "
        "'0 0 10.0.0.5:22 10.0.0.9:5000'; }\n"
    )
    done = _shell(stubs + "ssh_peers", SSH_CLIENT="23.234.83.83 51234 22")
    assert done.stdout.split() == ["198.51.100.9", "23.234.83.83"]  # private ones need no entry
