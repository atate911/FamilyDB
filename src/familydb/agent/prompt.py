"""Assemble the request: cached system blocks first, everything volatile last."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from importlib import resources
from typing import Any

from familydb import personas
from familydb.agent.history import HistoryTurn
from familydb.agent.providers.base import Message, SystemBlock
from familydb.agent.render import render_family_context, render_idea_list
from familydb.config import Settings
from familydb.store import ideas, members

IDEAS_HEADER = (
    "Ideas list, one per line: number | kind | title | where | who it is for | tags | "
    "setting/weather | seasons | duration | cost | booking | status | suggested by, date"
)


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    """A prompt file from the package: system, enrich, discover."""
    return (resources.files("familydb.agent") / "prompts" / f"{name}.md").read_text("utf-8")


def load_system_prompt() -> str:
    return load_prompt("system")


def trim_ideas(everything: list[Any], limit: int) -> tuple[list[Any], int]:
    """The newest `limit` ideas in their usual order, and how many were left out."""
    if limit <= 0 or len(everything) <= limit:
        return everything, 0
    return everything[-limit:], len(everything) - limit


# Between the persona's character and the product spec: who she is, then what the job is. Who
# she is includes the family's own notes on how she talks, after her character, so the job comes
# after those too. The spec says what to do and wins where the two meet, and the header says so
# for every persona: her own character says it too, but a family's rewrite of her need not.
# Under none neither header is sent, as there is no character for the job to win against.
PERSONA_HEADER = "# Who you are\n\n"
JOB_HEADER = "\n\n# The job\n\nWhere who you are and the job disagree, the job wins.\n\n"


def chat_prefix(conn: sqlite3.Connection, settings: Settings) -> tuple[str, str, str, str]:
    """The chat prefix in its parts: her character (with the family's notes on how she talks),
    the system prompt, the family, the ideas."""
    family = render_family_context(members.list_all(conn), settings)
    everything = ideas.list_for_prompt(conn)
    shown, hidden = trim_ideas(everything, settings.prompt_idea_limit)
    idea_list = f"{IDEAS_HEADER}\n{render_idea_list(shown)}"
    if hidden:
        idea_list += (
            f"\n({hidden} older idea{'s' if hidden != 1 else ''} not listed here; "
            "use search_ideas to find them.)"
        )
    return personas.active(settings).prompt, load_system_prompt(), family, idea_list


def chat_blocks(
    character: str, instructions: str, family: str, idea_list: str
) -> list[SystemBlock]:
    """Two blocks, both cache breakpoints: who she is and the system prompt, which never change,
    then the family context and the idea list, which change when an idea does."""
    first = f"{PERSONA_HEADER}{character}{JOB_HEADER}{instructions}" if character else instructions
    return [
        SystemBlock(first, cacheable=True),
        SystemBlock(f"{family}\n\n{idea_list}", cacheable=True),
    ]


def build_system_blocks(conn: sqlite3.Connection, settings: Settings) -> list[SystemBlock]:
    return chat_blocks(*chat_prefix(conn, settings))


def build_messages(history: list[HistoryTurn], current: list[str]) -> list[Message]:
    """History as alternating turns (same-role turns merged), then the current user turn."""
    merged: list[Message] = []
    for turn in history:
        if merged and merged[-1].role == turn.role:
            merged[-1] = Message(turn.role, [*merged[-1].parts, turn.text])
        else:
            merged.append(Message(turn.role, [turn.text]))
    while merged and merged[0].role != "user":
        merged.pop(0)  # a conversation has to open with the family, not with a reply
    if merged and merged[-1].role == "user":
        merged[-1] = Message("user", [*merged[-1].parts, *current])
    else:
        merged.append(Message("user", list(current)))
    return merged
