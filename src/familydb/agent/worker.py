"""Worker turns: small, separate model calls with their own prompt, tool subset and web access.

The chat agent never gets the web tools; enrichment and discovery run here instead and hand their
results back through strict client tools (save_place / skip_place, report_finds).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Literal

from familydb.agent.loop import MessagesAPI, TurnResult, run_turn
from familydb.agent.prompt import load_prompt
from familydb.agent.providers import (
    Message,
    Provider,
    SystemBlock,
    ToolDef,
    WebAccess,
    fallback_for,
    for_surface,
)
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


def worker_system_blocks(kind: WorkerKind, settings: Settings) -> list[SystemBlock]:
    home = f"Home area: {settings.home_area or 'not set'}\nTimezone: {settings.tz}"
    return [SystemBlock(load_prompt(kind), cacheable=True), SystemBlock(home, cacheable=True)]


def worker_tools(kind: WorkerKind, registry: ToolRegistry) -> list[ToolDef]:
    return registry.tool_defs(WORKER_TOOLS[kind])


def worker_web(kind: WorkerKind, user_location: dict[str, Any] | None = None) -> WebAccess:
    """Hosted search for this worker, capped. Only worker turns ever get it."""
    return WebAccess(max_uses=WORKER_MAX_USES[kind], user_location=user_location)


def run_worker_turn(
    *,
    kind: WorkerKind,
    api: MessagesAPI | None = None,
    settings: Settings,
    clock: Clock,
    registry: ToolRegistry,
    conn: sqlite3.Connection,
    request: str,
    geocoder: Any = None,
    message_id: int | None = None,
    user_location: dict[str, Any] | None = None,
    provider: Provider | None = None,
    fallback: Provider | None = None,
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
    worker: Provider = provider or for_surface(settings, "worker", api=api)
    spare = fallback
    if spare is None and api is None:
        spare = fallback_for(settings, "worker", worker.name)
    result = run_turn(
        provider=worker,
        surface="worker",
        fallback=spare,
        settings=settings,
        registry=registry,
        ctx=ctx,
        system=worker_system_blocks(kind, settings),
        messages=[Message("user", [f"Today is {clock.describe()}.", request])],
        tools=worker_tools(kind, registry),
        web=worker_web(kind, user_location),
        max_iterations=settings.worker_max_iterations,
        model=worker.model_for("worker"),
        effort=settings.worker_effort,
    )
    return WorkerTurn(result, ctx)
