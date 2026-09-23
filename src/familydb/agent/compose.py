"""What goes into a request, part by part, and what each part costs.

The gateway decides which kind of call this is; this module builds what that kind is sent, from
labelled sections, and measures them. The providers then put it in each vendor's own format.

A provider reports one real number for what a call sent: its input tokens, cached or not. No
vendor says how those split between the instructions, the tools, the idea list and the history,
and counting each part exactly would cost a request of its own. So each section's size is
recorded in characters with every call, and the real total is shared out in proportion: the
split is an estimate, the total is what was billed. That is enough to see which part is large
and whether a change made it smaller, which is what the numbers are for.
"""

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
    Provider,
    SystemBlock,
    ToolDef,
    TurnRequest,
    WebAccess,
)
from familydb.config import Settings
from familydb.tools import ToolRegistry

if TYPE_CHECKING:
    from familydb.agent.gateway import CallSpec

# Every part a request can have, what a person would call it, and which layer of
# docs/AI_CALLS.md it belongs to: the cached prefix, or the turn itself.
SECTIONS: dict[str, tuple[str, str]] = {
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
    """The cached part of the request. Nothing in it may change from one call to the next."""
    if call.prompt == "system":
        instructions, family, idea_list = chat_prefix(conn, settings)
        sizes = {"instructions": len(instructions), "family": len(family), "ideas": len(idea_list)}
        return chat_blocks(instructions, family, idea_list), sizes
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
    provider: Provider,
    current: list[str],
    history: Sequence[HistoryTurn] = (),
    user_location: dict[str, Any] | None = None,
) -> Composed:
    """The whole request for one call of this kind: the prefix, the tools, the conversation."""
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
        model=provider.model_for(call.surface),
        effort=getattr(settings, call.effort) if call.effort else None,
    )
    return Composed(request, {name: size for name, size in sections.items() if size})


def exchange_chars(exchanges: Iterable[Exchange]) -> int:
    """What the earlier steps of a turn add to each later call: answers, tool calls, results."""
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
    """Where the input tokens of these calls went, per section, averaged per call.

    Each row is one recorded call: `sections` (JSON of characters per section) and `sent`, the
    input tokens the provider reported for it. Calls recorded without sections are left out.
    """
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
