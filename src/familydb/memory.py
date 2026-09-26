"""Which of the family's memories a message needs, chosen by code (docs/MEMORY.md).

What the family has told the bot about itself is kept by the `remember` tool (store/memories.py).
Before each chat turn, code chooses what goes with the message, in the part of the request that
is not cached, so the cached prefix never moves when a memory does:

- every firm one in force, whatever the message says: an allergy or a "never" is not dropped
  for being off the subject, and not for the budget either;
- then the rest, as many as fit in `BUDGET` characters, those that bear on the message first:
  sharing a word with it, of a kind it touches on (food for a question about dinner), about
  whoever is asking or the whole family, then the newest.

No model is asked which memories matter: at family scale every one usually fits, and when they
do not, a word in common is a fair guess at what bears on a message, and a firm one never waits
on a guess. A guess the model made (`inferred`) is marked as one, so it only leans on it.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date

from familydb.store import memories
from familydb.store.memories import Memory

# About 400 tokens of the family's tastes on top of their firm needs, which always go.
BUDGET = 1600


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


# Words too common to say what a message is about.
COMMON = _words(
    "about after again also and any are been but can could did does doing for from get got had "
    "has have her him his how its just like lets love maybe more much need not now our out over "
    "really she should some that the them then there they this too want was well were what "
    "when where which who why will with would you your"
)
# Words that say a message touches on a kind of memory, though it names nothing remembered.
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
    left_out: int  # in force, but not chosen for this message


def words(text: str) -> set[str]:
    """The words of a text that could say what it is about."""
    found = {word for word in re.findall(r"[a-z]{3,}", text.casefold()) if word not in COMMON}
    # "girls" and "girl", "hikes" and "hike": the same word here.
    return found | {word[:-1] for word in found if word.endswith("s") and len(word) > 3}


def choose(
    conn: sqlite3.Connection,
    text: str,
    *,
    sender_id: int | None,
    today: date,
    budget: int = BUDGET,
) -> Chosen:
    """The memories this message goes with: every firm one, then the best of the rest."""
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
    """One memory as the chat model is told it; the budget is counted in these."""
    notes = []
    if memory.firm:
        notes.append("must")
    if memory.inferred:
        notes.append("a guess")
    if memory.until:
        notes.append(f"until {memory.until}")
    said = f" ({', '.join(notes)})" if notes else ""
    return f"- m{memory.id} {memory.about_name or 'family'}: {memory.fact}{said}"
