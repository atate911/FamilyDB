"""Parts of a request a company may stop taking, and which it has stopped taking, per model.

Some of what a request carries is dated or new: a beta named for the day it began, a tool version,
thinking and effort settings, a parameter a newer model does not know. When a company retires one,
or a model it has just released does not take it yet, the answer is a 400 on every request, and
the family's bot stops until a new release. So each provider module names the parts it may leave
out (`Part`), and when a 400 names one the request carried, the request is sent again without it,
once for each part, and the part is left out for that model for as long as the process runs. A
400 is not billed, so trying again costs a moment and nothing more. The reply says what was left
out (`ModelReply.dropped`), and the loop tells an admin (alerts.py, "api"), so a person looks at
what the bot is doing without; a 400 that names nothing here is the company's to explain and is
raised as it came (`trouble="refused"`).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class Part:
    name: str  # what it is, as an admin is told: "the refusal fallback"
    words: tuple[str, ...]  # what a refusal of it says, lower case: a parameter's name, say


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
    """Start again, as a new process would: for the tests."""
    with _lock:
        _left_out.clear()


def refused(said: str, parts: tuple[Part, ...], carried: set[str]) -> Part | None:
    """The part a 400 names, among those the request carried; None when it names none."""
    lowered = said.lower()
    for part in parts:
        if part.name in carried and any(word in lowered for word in part.words):
            return part
    return None
