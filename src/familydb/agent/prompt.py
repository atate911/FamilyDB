"""Assemble the request: cached system blocks first, everything volatile last."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from importlib import resources
from typing import Any

from familydb.agent.history import HistoryTurn
from familydb.agent.render import render_family_context, render_idea_list
from familydb.config import Settings
from familydb.store import ideas, members

IDEAS_HEADER = (
    "Ideas list, one per line: number | kind | title | where | who it is for | tags | "
    "setting/weather | seasons | duration | cost | booking | status | suggested by, date | "
    "details looked up?"
)


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    """A prompt file from the package: system, enrich, discover."""
    return (resources.files("familydb.agent") / "prompts" / f"{name}.md").read_text("utf-8")


def load_system_prompt() -> str:
    return load_prompt("system")


def cache_control(settings: Settings) -> dict[str, str]:
    if settings.anthropic_cache_ttl == "1h":
        return {"type": "ephemeral", "ttl": "1h"}
    return {"type": "ephemeral"}


def build_system_blocks(conn: sqlite3.Connection, settings: Settings) -> list[dict[str, Any]]:
    """Two blocks, both cache breakpoints: the system prompt, then family context + idea list."""
    marker = cache_control(settings)
    family = render_family_context(members.list_all(conn), settings)
    idea_lines = render_idea_list(ideas.list_for_prompt(conn))
    context = f"{family}\n\n{IDEAS_HEADER}\n{idea_lines}"
    return [
        {"type": "text", "text": load_system_prompt(), "cache_control": marker},
        {"type": "text", "text": context, "cache_control": marker},
    ]


def build_messages(
    history: list[HistoryTurn], current: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """History as alternating turns (same-role turns merged), then the current user turn."""
    merged: list[dict[str, Any]] = []
    for turn in history:
        if merged and merged[-1]["role"] == turn.role:
            merged[-1]["content"] += "\n\n" + turn.text
        else:
            merged.append({"role": turn.role, "content": turn.text})
    while merged and merged[0]["role"] != "user":
        merged.pop(0)
    if merged and merged[-1]["role"] == "user":
        previous = merged[-1]["content"]
        blocks = [{"type": "text", "text": previous}] if isinstance(previous, str) else previous
        merged[-1]["content"] = blocks + current
    else:
        merged.append({"role": "user", "content": current})
    return merged
