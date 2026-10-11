"""What a search reaches the world through, so the scouting layer never holds the App: the
connection, the settings in force, the clock, the tools a worker may call, the model client (a
fake in tests), the geocoder, the shared cache of searches, and the message and turn it is made
for."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from familydb.agent.worker import WorkerKind, WorkerTurn, home_location, run_worker_turn
from familydb.base.clock import Clock
from familydb.base.config import Settings
from familydb.tools import ToolContext, ToolRegistry, build_registry


@dataclass
class Reach:
    conn: sqlite3.Connection
    settings: Settings
    clock: Clock
    registry: ToolRegistry
    api: Any = None
    geocoder: Any = None
    cache: dict[str, Any] | None = None  # the App's cache of searches (App.discover_cache)
    message_id: int | None = None
    # The answering turn's own scratch (ToolContext.scratch), which lasts the turn: where a
    # search made for it is noted, so a message searches once.
    turn_notes: dict[str, Any] | None = None

    @classmethod
    def of(cls, ctx: ToolContext) -> Reach:
        """For a search made while answering a message: its tool context's own."""
        return cls(
            conn=ctx.conn,
            settings=ctx.settings,
            clock=ctx.clock,
            registry=build_registry(),
            api=ctx.api,
            cache=ctx.discover_cache,
            message_id=ctx.message_id,
            turn_notes=ctx.scratch,
        )

    @classmethod
    def of_app(cls, app: Any, conn: sqlite3.Connection, api: Any = None) -> Reach:
        """For a job: the App's settings, clock, tools and geocoder, on the job's connection."""
        return cls(
            conn=conn,
            settings=app.settings,
            clock=app.clock,
            registry=app.registry,
            api=api,
            geocoder=app.geocoder,
            cache=app.discover_cache,
        )


def turn(
    reach: Reach,
    kind: WorkerKind,
    request: str,
    about: str,
    *,
    idea_id: int | None = None,
    find_id: int | None = None,
    geocoder: bool = False,
) -> WorkerTurn:
    """One worker turn of `kind`, searching from home; raises what the turn raises. `geocoder`
    lends the turn the reach's geocoder (a lookup that saves a place needs it)."""
    return run_worker_turn(
        kind=kind,
        api=reach.api,
        settings=reach.settings,
        clock=reach.clock,
        registry=reach.registry,
        conn=reach.conn,
        request=request,
        message_id=reach.message_id,
        user_location=home_location(reach.settings),
        idea_id=idea_id,
        find_id=find_id,
        about=about,
        geocoder=reach.geocoder if geocoder else None,
    )
