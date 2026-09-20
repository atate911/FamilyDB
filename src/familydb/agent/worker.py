"""Worker turns: small, separate model calls with their own prompt, tool subset and web access.

The chat agent never gets the web tools; enrichment and discovery run here instead and hand their
results back through strict client tools (save_place / skip_place, report_finds).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Literal

from familydb.agent.loop import MessagesAPI, TurnResult, run_turn
from familydb.agent.prompt import cache_control, load_prompt
from familydb.clock import Clock
from familydb.config import Settings
from familydb.tools import ToolContext, ToolRegistry

WorkerKind = Literal["enrich", "discover"]
WORKER_TOOLS: dict[str, tuple[str, ...]] = {
    "enrich": ("save_place", "skip_place"),
    "discover": ("report_finds",),
}
WORKER_MAX_USES: dict[str, int] = {"enrich": 3, "discover": 4}


@dataclass
class WorkerTurn:
    result: TurnResult
    ctx: ToolContext

    def handed_back(self, tool_name: str) -> bool:
        """Whether the worker made a successful call to its hand-back tool."""
        return any(a.get("tool") == tool_name and a.get("ok") for a in self.result.actions)


def home_location(settings: Settings) -> dict[str, Any] | None:
    """An approximate location for web searches, from HOME_AREA ('City, Region')."""
    if not settings.home_area:
        return None
    parts = [p.strip() for p in settings.home_area.split(",") if p.strip()]
    location: dict[str, Any] = {"type": "approximate", "city": parts[0], "timezone": settings.tz}
    if len(parts) > 1:
        location["region"] = parts[1]
    return location


def worker_system_blocks(kind: WorkerKind, settings: Settings) -> list[dict[str, Any]]:
    marker = cache_control(settings)
    home = f"Home area: {settings.home_area or 'not set'}\nTimezone: {settings.tz}"
    return [
        {"type": "text", "text": load_prompt(kind), "cache_control": marker},
        {"type": "text", "text": home, "cache_control": marker},
    ]


def worker_tools(
    kind: WorkerKind,
    registry: ToolRegistry,
    settings: Settings,
    *,
    user_location: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return registry.api_tools(
        settings,
        names=WORKER_TOOLS[kind],
        force_web=True,
        max_uses=WORKER_MAX_USES[kind],
        user_location=user_location,
    )


def run_worker_turn(
    *,
    kind: WorkerKind,
    api: MessagesAPI,
    settings: Settings,
    clock: Clock,
    registry: ToolRegistry,
    conn: sqlite3.Connection,
    request: str,
    geocoder: Any = None,
    message_id: int | None = None,
    user_location: dict[str, Any] | None = None,
) -> WorkerTurn:
    """One worker turn. `message_id` ties the audit rows to a chat message when there is one."""
    ctx = ToolContext(
        conn=conn,
        settings=settings,
        clock=clock,
        member=None,
        message_id=message_id,
        geocoder=geocoder,
    )
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Today is {clock.describe()}."},
                {"type": "text", "text": request},
            ],
        }
    ]
    result = run_turn(
        api=api,
        settings=settings,
        registry=registry,
        ctx=ctx,
        system=worker_system_blocks(kind, settings),
        messages=messages,
        tools=worker_tools(kind, registry, settings, user_location=user_location),
        max_iterations=settings.worker_max_iterations,
    )
    return WorkerTurn(result, ctx)
