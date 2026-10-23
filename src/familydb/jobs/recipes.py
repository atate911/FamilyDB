"""Reading pasted recipe links (docs/RECIPES.md): every few minutes, each recipe whose link nobody
has tried is read by this server from its page's recipe block, with no model call, and the chat
it came from is told what was found. A page with none waits for the evening's lookup
(jobs/enrich.py), which pays a reader for it. Idle, this is one query."""

from __future__ import annotations

import logging
from contextlib import closing
from typing import Any

from familydb import meals
from familydb.app import App
from familydb.base.dates import utc_iso
from familydb.integrations.recipe_page import PageAPI
from familydb.jobs.enrich import notify
from familydb.scouting import fill
from familydb.scouting.reach import Reach
from familydb.store import ideas
from familydb.store import recipes as recipe_store
from familydb.store.db import transaction

log = logging.getLogger(__name__)

# The most links one run reads; the rest wait a few minutes.
MOST = 10


def run_recipe_links(app: App, *, pages: PageAPI | None = None) -> dict[str, int]:
    """Read the links waiting; returns how many were read, left for the lookup, or refused."""
    counts = {"done": 0, "unread": 0, "refused": 0}
    with closing(app.connect()) as conn:
        app.refresh(conn)
        if not app.settings.recipe_links:
            return counts
        waiting = recipe_store.links_to_read(conn, MOST)
        if not waiting:
            return counts
        reach = Reach.of_app(app, conn)
        for idea_id in waiting:
            idea = ideas.get(conn, idea_id)
            if idea is None:
                continue
            try:
                outcome = fill.read_recipe(reach, idea, pages)
            except Exception as exc:
                # Noted, so the next run does not fetch it again: the evening's lookup has it.
                log.exception("reading recipe %s crashed", idea_id)
                _noted(app, conn, idea, f"could not be read: {type(exc).__name__}")
                counts["unread"] += 1
                continue
            counts[outcome] += 1
            if outcome == "done":
                _told(app, conn, idea_id)
    return counts


def _noted(app: App, conn: Any, idea: Any, note: str) -> None:
    with transaction(conn):
        meals.not_read(conn, idea, note, status=None, now=utc_iso(app.clock.now()))


def _told(app: App, conn: Any, idea_id: int) -> None:
    current = ideas.get(conn, idea_id)
    if current is None:
        return
    try:
        notify(app, conn, current)
    except Exception:
        log.exception("could not note the reading of recipe %s", idea_id)
