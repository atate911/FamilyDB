"""Parts of a request a company may refuse (a dated beta, a tool version, thinking settings).

A 400 on every request would stop the bot until a release, so when a 400 names a part the request
carried, it is sent again without it, once per part, and the part stays left out for that model
for the life of the process. A 400 is not billed. `ModelReply.dropped` tells an admin (alerts.py,
"api"); a 400 naming nothing here is raised as `trouble="refused"`."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class Part:
    name: str  # as an admin is told: "the refusal fallback"
    words: tuple[str, ...]  # what a refusal of it says, lower case


_left_out: dict[tuple[str, str], set[str]] = {}
_lock = threading.Lock()


def left_out(company: str, model: str) -> frozenset[str]:
    """The parts this model has refused since the process started."""
    with _lock:
        return frozenset(_left_out.get((company, model.lower()), ()))


def leave_out(company: str, model: str, part: str) -> None:
    with _lock:
        _left_out.setdefault((company, model.lower()), set()).add(part)


def forget() -> None:
    """Start again, as a new process would (tests)."""
    with _lock:
        _left_out.clear()


def refused(said: str, parts: tuple[Part, ...], carried: set[str]) -> Part | None:
    """The part a 400 names, among those the request carried; None when it names none."""
    lowered = said.lower()
    for part in parts:
        if part.name in carried and any(word in lowered for word in part.words):
            return part
    return None
