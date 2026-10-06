"""What is new in the running code, for the Status page: the top section of the CHANGELOG.md that
shipped with it (the image copies it), which is the release's own section for an install from a
tag, and the one still being written for an install that follows the default branch. Read from
the file, never a model; nothing when the file is not there."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# src/familydb/whatsnew.py: the repository (or the image's /app) is two folders up.
CHANGELOG = Path(__file__).resolve().parents[2] / "CHANGELOG.md"
SECTION = re.compile(r"^## (.+)$")
NEW = re.compile(r"^### New since ")
ITEM = re.compile(r"^- \*\*(.+?)\*\*\s*(.*)$")


@dataclass(frozen=True)
class WhatsNew:
    heading: str  # "v0.3.0 — in progress"
    items: tuple[tuple[str, str], ...]  # (what, said of it), in the changelog's order


def latest(path: Path = CHANGELOG) -> WhatsNew | None:
    """The top section's "New since" list, as (title, words) pairs; None without the file."""
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    return _read(path, stamp)


@lru_cache(maxsize=4)
def _read(path: Path, _stamp: float) -> WhatsNew | None:
    heading: str | None = None
    listing = False
    items: list[list[str]] = []
    for line in path.read_text("utf-8").splitlines():
        if found := SECTION.match(line):
            if heading is not None:
                break  # the next release's: only the top one is what is new
            heading = found.group(1).strip()
            continue
        if heading is None:
            continue
        if line.startswith("### "):
            listing = NEW.match(line) is not None  # the "New since" list, not what it does
            continue
        if not listing:
            continue
        if found := ITEM.match(line):
            # "- **A new Home**, the first page...": the words go on from the title.
            items.append([found.group(1).rstrip("."), found.group(2).lstrip(",;: ")])
        elif items and line.startswith("  ") and line.strip():
            items[-1][1] = f"{items[-1][1]} {line.strip()}".strip()
    if heading is None:
        return None
    return WhatsNew(heading, tuple((what, said.replace("**", "")) for what, said in items))
