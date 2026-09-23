"""Worker turns: small, separate model calls with their own prompt, tool subset and web access.

The chat agent never gets the web tools; enrichment and discovery run here instead and hand their
results back through strict client tools (save_place / skip_place, report_finds). What each
kind may use is declared in `agent.gateway.KINDS`; this module only frames the request.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Literal

from familydb.agent import gateway
from familydb.agent.loop import MessagesAPI, TurnResult
from familydb.agent.providers import Provider
from familydb.clock import Clock
from familydb.config import Settings
from familydb.tools import ToolContext, ToolRegistry

WorkerKind = Literal["enrich", "discover"]


@dataclass
class WorkerTurn:
    result: TurnResult
    ctx: ToolContext
    kind: WorkerKind = "enrich"

    def handed_back(self, tool_name: str | None = None) -> bool:
        """Whether the worker made a successful call to its hand-back tool (or to this one)."""
        return gateway.handed_back(gateway.spec(self.kind), self.result, tool_name)


def home_location(settings: Settings) -> dict[str, Any] | None:
    """An approximate location for web searches, from HOME_AREA ('City, Region')."""
    if not settings.home_area:
        return None
    parts = [p.strip() for p in settings.home_area.split(",") if p.strip()]
    location: dict[str, Any] = {"type": "approximate", "city": parts[0], "timezone": settings.tz}
    if len(parts) > 1:
        location["region"] = parts[1]
    return location


def worker_turn(clock: Clock, request: str) -> list[str]:
    """A worker's whole conversation: today's date, then what it is asked to do."""
    return [f"Today is {clock.describe()}.", request]


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
    idea_id: int | None = None,
) -> WorkerTurn:
    """One worker turn. `message_id` ties the audit rows to a chat message when there is one."""
    ctx = ToolContext(
        conn=conn,
        settings=settings,
        clock=clock,
        member=None,
        message_id=message_id,
        geocoder=geocoder,
        worker_idea_id=idea_id,
    )
    result = gateway.ask(
        kind,
        settings=settings,
        registry=registry,
        ctx=ctx,
        current=worker_turn(clock, request),
        api=api,
        provider=provider,
        fallback=fallback,
        user_location=user_location,
    )
    return WorkerTurn(result, ctx, kind)
