"""The install guide's first step is a block people paste into a server, so it has to stay right.

Nobody reading the guide can tell a broken quote from a working one, and the first sign would be
a new family's server doing something odd. These check the block itself: that it is one command,
that it is valid shell, and that it names the repository the scripts install from.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "INSTALL.md"


def _first_block() -> str:
    text = GUIDE.read_text("utf-8")
    step = text.index("## 1. Install it")
    block = re.search(r"```bash\n(.*?)```", text[step:], re.S)
    assert block is not None, "step 1 has no bash block"
    return block.group(1)


def _inner(block: str) -> str:
    """The script inside `sudo bash -c '...'`: everything between the first quote and the last."""
    assert block.startswith("sudo bash -c '"), "the block must be one command, so pasting it works"
    assert block.rstrip().endswith("'"), "the block must end where its one command does"
    return block[block.index("'") + 1 : block.rstrip().rindex("'")]


def test_the_block_is_one_command_with_no_quote_inside_to_break_it() -> None:
    inner = _inner(_first_block())
    # A single quote inside would end the command early, and the rest would run as its own
    # commands, or be read as the answer to a question.
    assert "'" not in inner


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_the_block_is_valid_shell() -> None:
    inner = _inner(_first_block())
    checked = subprocess.run(["bash", "-n"], input=inner, text=True, capture_output=True)
    assert checked.returncode == 0, checked.stderr


def test_the_block_fetches_what_bootstrap_installs_and_asks_before_waiting() -> None:
    inner = _inner(_first_block())
    bootstrap = (ROOT / "scripts" / "bootstrap.sh").read_text("utf-8")
    repo = re.search(r'^REPO="https://github.com/([^"]+)\.git"', bootstrap, re.M).group(1)
    assert f"git@github.com:{repo}.git" in inner
    assert f"https://github.com/{repo}/settings/keys/new" in inner
    # Every read is from the terminal, so what was pasted is never taken as an answer.
    reads = [line for line in inner.splitlines() if re.search(r"\bread -r\b", line)]
    assert reads and all("</dev/tty" in line for line in reads)
    assert "bootstrap.sh --deploy-key" in inner and "</dev/tty" in inner.split("bootstrap.sh")[1]
    assert 'FAMILYDB_AGAIN="paste the same block again"' in inner


def test_every_link_inside_the_guide_goes_somewhere() -> None:
    """The guide links its own headings; a renamed one should not leave a dead link."""
    text = GUIDE.read_text("utf-8")
    anchors = set()
    for heading in re.findall(r"^#{1,4} (.+)$", text, re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
        anchors.add(slug)
    wanted = set(re.findall(r"\]\(#([^)]+)\)", text))
    assert wanted <= anchors, sorted(wanted - anchors)
