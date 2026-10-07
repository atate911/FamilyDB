"""Which of the family's memories a message needs, chosen by code (docs/MEMORY.md).

Memories are kept by the `remember` tool (store/memories.py). Before each chat turn code chooses
what goes with the message, in the uncached part of the request, so the cached prefix never moves
when a memory does: every firm one in force (an allergy or a "never" is never dropped, not even
for the budget), then as many of the rest as fit in `BUDGET` characters, those bearing on the
message first (a shared word, a kind it touches on, about the asker or the whole family, then
newest). No model is asked: at family scale everything usually fits. A guess the model made
(`inferred`) is marked so it only leans on it.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date

from familydb.store import memories
from familydb.store.memories import Memory

BUDGET = 1600


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


COMMON = _words(
    "about after again also and any are been but can could did does doing for from get got had "
    "has have her him his how its just like lets love maybe more much need not now our out over "
    "really she should some that the them then there they this too want was well were what "
    "when where which who why will with would you your"
)
CUES: dict[str, frozenset[str]] = {
    "food": _words(
        "eat eating food dinner lunch breakfast brunch restaurant restaurants hungry snack "
        "cook cooking menu takeout dessert cafe coffee drinks bar"
    ),
    "activities": _words(
        "bored fun weekend tonight today tomorrow outing activity hike park museum show "
        "movie concert game games play trip suggest"
    ),
    "places": _words("near nearby drive driving far downtown trip travel place"),
    "health": _words("allergy allergic sick doctor dentist walk walking diet"),
    "routine": _words(
        "monday tuesday wednesday thursday friday saturday sunday morning afternoon evening "
        "night week schedule calendar school work bedtime remind"
    ),
}


@dataclass(frozen=True)
class Chosen:
    memories: list[Memory]
    left_out: int


def words(text: str) -> set[str]:
    found = {word for word in re.findall(r"[a-z]{3,}", text.casefold()) if word not in COMMON}
    return found | {word[:-1] for word in found if word.endswith("s") and len(word) > 3}


def choose(
    conn: sqlite3.Connection,
    text: str,
    *,
    sender_id: int | None,
    today: date,
    budget: int = BUDGET,
) -> Chosen:
    live = memories.active(conn, today=today)
    firm = [memory for memory in live if memory.firm]
    rest = [memory for memory in live if not memory.firm]
    said = words(text)
    touched = {kind for kind, cues in CUES.items() if said & cues}

    def bearing(memory: Memory) -> tuple[int, int, int, int]:
        about = f"{memory.fact} {memory.about_name or ''}"
        return (
            len(said & words(about)),
            int(memory.category in touched),
            int(memory.member_id is None or memory.member_id == sender_id),
            memory.id,
        )

    chosen = list(firm)
    used = sum(len(line_of(memory)) for memory in firm)
    for memory in sorted(rest, key=bearing, reverse=True):
        size = len(line_of(memory))
        if used + size > budget:
            continue
        chosen.append(memory)
        used += size
    chosen.sort(key=lambda memory: memory.id)
    return Chosen(chosen, len(live) - len(chosen))


def line_of(memory: Memory) -> str:
    notes = []
    if memory.firm:
        notes.append("must")
    if memory.inferred:
        notes.append("a guess")
    if memory.until:
        notes.append(f"until {memory.until}")
    said = f" ({', '.join(notes)})" if notes else ""
    return f"- m{memory.id} {memory.about_name or 'family'}: {memory.fact}{said}"
