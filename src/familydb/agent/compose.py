"""Builds each kind's request from labelled sections and measures them. Vendors report only total
input tokens, so each section's size is recorded in characters per call and the billed total is
shared out in proportion (an estimate split of a real total)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from familydb.agent.history import HistoryTurn
from familydb.agent.prompt import build_messages, chat_blocks, chat_prefix, load_prompt
from familydb.agent.providers import (
    Exchange,
    SystemBlock,
    ToolDef,
    TurnRequest,
    WebAccess,
)
from familydb.base.config import Settings
from familydb.tools import ToolRegistry

if TYPE_CHECKING:
    from familydb.agent.gateway import CallSpec

# Every part a request can have, its label, and its docs/AI_CALLS.md layer (prefix or turn).
SECTIONS: dict[str, tuple[str, str]] = {
    "personality": ("who the assistant is", "prefix"),
    "instructions": ("instructions", "prefix"),
    "family": ("who the family is", "prefix"),
    "ideas": ("the idea list", "prefix"),
    "home": ("where home is", "prefix"),
    "tools": ("tool definitions", "prefix"),
    "history": ("recent conversation", "turn"),
    "message": ("the message and today's date", "turn"),
    "earlier steps": ("earlier steps of the same turn", "turn"),
}


@dataclass
class Composed:
    """A request ready to send, and the size in characters of each part of it."""

    request: TurnRequest
    sections: dict[str, int]


def _chars(parts: Iterable[str]) -> int:
    return sum(len(part) for part in parts)


def prefix(
    call: CallSpec, conn: sqlite3.Connection, settings: Settings
) -> tuple[list[SystemBlock], dict[str, int]]:
    """The cached part of the request; nothing in it may vary between calls."""
    if call.prompt == "system":
        character, instructions, family, idea_list = chat_prefix(conn, settings)
        sizes = {"instructions": len(instructions), "family": len(family), "ideas": len(idea_list)}
        if character:
            sizes["personality"] = len(character)
        return chat_blocks(character, instructions, family, idea_list), sizes
    instructions = load_prompt(call.prompt)
    home = f"Home area: {settings.home_area or 'not set'}\nTimezone: {settings.tz}"
    blocks = [SystemBlock(instructions, cacheable=True), SystemBlock(home, cacheable=True)]
    return blocks, {"instructions": len(instructions), "home": len(home)}


def tool_defs(call: CallSpec, registry: ToolRegistry) -> list[ToolDef]:
    return registry.tool_defs() if call.tools is None else registry.tool_defs(call.tools)


def tool_chars(tools: Sequence[ToolDef]) -> int:
    return sum(
        len(tool.name) + len(tool.description) + len(json.dumps(tool.schema, sort_keys=True))
        for tool in tools
    )


def compose(
    call: CallSpec,
    *,
    conn: sqlite3.Connection,
    settings: Settings,
    registry: ToolRegistry,
    model: str,
    effort: str | None,
    current: list[str],
    history: Sequence[HistoryTurn] = (),
    user_location: dict[str, Any] | None = None,
) -> Composed:
    """The whole request for one call of this kind."""
    system, sections = prefix(call, conn, settings)
    tools = tool_defs(call, registry)
    messages = build_messages(list(history), current)
    sent = _chars(part for message in messages for part in message.parts)
    sections |= {
        "tools": tool_chars(tools),
        "history": sent - _chars(current),
        "message": _chars(current),
    }
    web = None
    if call.web_searches is not None:
        web = WebAccess(max_uses=call.web_searches, user_location=user_location)
    request = TurnRequest(
        system=system,
        messages=messages,
        tools=tools,
        web=web,
        model=model,
        effort=effort or (getattr(settings, call.effort) if call.effort else None),
    )
    return Composed(request, {name: size for name, size in sections.items() if size})


def exchange_chars(exchanges: Iterable[Exchange]) -> int:
    """What a turn's earlier steps add to each later call."""
    total = 0
    for exchange in exchanges:
        total += len(exchange.reply.text)
        total += sum(
            len(call.name) + len(json.dumps(call.arguments, sort_keys=True))
            for call in exchange.reply.tool_calls
        )
        total += sum(len(outcome.content) for outcome in exchange.outcomes)
    return total


def breakdown(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Input tokens per section, averaged per call. Rows carry `sections` (JSON characters) and
    `sent` (reported input tokens); rows without sections are left out."""
    tokens: dict[str, float] = {}
    counted = 0
    for row in rows:
        sizes = json.loads(row["sections"]) if row.get("sections") else None
        total = sum(sizes.values()) if sizes else 0
        if not total or not row.get("sent"):
            continue
        counted += 1
        for name, size in sizes.items():
            tokens[name] = tokens.get(name, 0.0) + row["sent"] * size / total
    if not counted:
        return []
    everything = sum(tokens.values())
    return [
        {
            "section": name,
            "label": SECTIONS.get(name, (name, ""))[0],
            "layer": SECTIONS.get(name, ("", "turn"))[1],
            "tokens": round(amount / counted),
            "share": round(amount / everything * 100),
            "calls": counted,
        }
        for name, amount in sorted(tokens.items(), key=lambda item: -item[1])
    ]
