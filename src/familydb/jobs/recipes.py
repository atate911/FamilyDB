"""Reading pasted recipe links (docs/RECIPES.md): every few minutes, each recipe whose link nobody
has tried is read by this server from its page's recipe block, with no model call, and the chat
it came from is told what was found. A page with none waits for the evening's lookup
(jobs/enrich.py), which pays a reader for it. Idle, this is one query."""

from __future__ import annotations

import logging
from contextlib import closing
from typing import Any

from familydb.app import App
from familydb.integrations.recipe_page import PageAPI
from familydb.jobs.enrich import notify
from familydb.scouting import fill
from familydb.scouting.reach import Reach
from familydb.store import ideas
from familydb.store import recipes as recipe_store

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
            except Exception:
                log.exception("reading recipe %s crashed", idea_id)
                continue
            counts[outcome] += 1
            if outcome == "done":
                _told(app, conn, idea_id)
    return counts


def _told(app: App, conn: Any, idea_id: int) -> None:
    current = ideas.get(conn, idea_id)
    if current is None:
        return
    try:
        notify(app, conn, current)
    except Exception:
        log.exception("could not note the reading of recipe %s", idea_id)
