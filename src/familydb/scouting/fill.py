"""Filling in details from the web (docs/FINDS.md, "filling in"): one worker turn finds an idea's
place and hands back with `save_place` or `skip_place` (tools/places.py), which keep what the
page says; a find is filled in the same way (`fill_find`, with `save_find` or `skip_find`), so
ideas and finds end up with the same facts. An idea with nothing to look up
(`ideas.needs_lookup`) is skipped with no call. When each is looked up, and what the family is
told, is the jobs' (jobs/enrich.py, jobs/happening.py)."""

from __future__ import annotations

import json
import logging

from familydb import meals
from familydb.agent.spending import LIMITS
from familydb.agent.worker import WorkerTurn
from familydb.base.config import Settings
from familydb.base.dates import utc_iso
from familydb.base.errors import AgentError
from familydb.integrations import recipe_page
from familydb.integrations.recipe_page import PageAPI, PageError, RecipePages
from familydb.scouting.reach import Reach
from familydb.scouting.reach import turn as reach_turn
from familydb.store import finds, ideas, places
from familydb.store import recipes as recipe_store
from familydb.store.db import transaction
from familydb.store.ideas import RECIPE, Idea, needs_lookup
from familydb.store.places import Place

log = logging.getLogger(__name__)

OUTCOMES = ("done", "skipped", "failed", "deferred")
# Which ideas have nothing to look up is the idea record's rule (`ideas.needs_lookup`).
NO_LOOKUP_NOTE = "nothing to look up: a {kind} idea with no place or link"


def render_enrich_request(idea: Idea, place: Place | None, settings: Settings) -> str:

    lines = [f"Idea #{idea.id}: {idea.title}", f"Kind: {idea.kind}"]
    if idea.location_name:
        lines.append(f"Location as the family said it: {idea.location_name}")
    if idea.description:
        lines.append(f"Description: {idea.description}")
    if idea.url:
        lines.append(f"Link the family gave: {idea.url}")
    if idea.participants:
        lines.append(f"For: {', '.join(idea.participants)}")
    lines.append(f"Home area: {settings.home_area or 'not set'}")
    if place is not None:
        known = {
            "name": place.name,
            "address": place.address,
            "website": place.website,
            "hours": place.hours,
            "booking_url": place.booking_url,
        }
        lines.append(
            "Previously saved details, to re-check and update: "
            + json.dumps(known, ensure_ascii=False, sort_keys=True)
        )
    lines.append(
        f"Hand back with save_place (idea_id={idea.id}) or skip_place (idea_id={idea.id})."
    )
    return "\n".join(lines)


def _mark(reach: Reach, idea_id: int, status: str, note: str | None) -> None:
    now = utc_iso(reach.clock.now())
    with transaction(reach.conn):
        ideas.update(
            reach.conn,
            idea_id,
            {"enrichment": status, "enriched_at": now, "enrichment_note": note},
            now=now,
        )


def fill_in(reach: Reach, idea: Idea, pages: PageAPI | None = None) -> str:
    """Look one idea up and keep what the page says; returns done, skipped, failed or deferred.
    What the family is told is the job's (jobs/enrich.py). A recipe is read from its link."""
    if idea.kind == RECIPE and needs_lookup(idea):
        return fill_recipe_in(reach, idea, pages)
    if not needs_lookup(idea):
        _mark(reach, idea.id, "skipped", NO_LOOKUP_NOTE.format(kind=idea.kind))
        log.info("idea %s enrichment skipped without a model call", idea.id)
        return "skipped"
    place = places.get(reach.conn, idea.place_id) if idea.place_id else None
    request = render_enrich_request(idea, place, reach.settings)
    try:
        turn: WorkerTurn = reach_turn(
            reach, "enrich", request, f"#{idea.id} {idea.title}", idea_id=idea.id, geocoder=True
        )
    except AgentError as exc:
        if exc.retryable or isinstance(exc, LIMITS):
            log.warning("enrichment of idea %s deferred: %s", idea.id, exc)
            return "deferred"
        _mark(reach, idea.id, "failed", f"worker: {exc}")
        return "failed"
    except Exception as exc:
        # Left pending it would burn a model call every run.
        log.exception("enrichment of idea %s crashed", idea.id)
        _mark(reach, idea.id, "failed", f"error: {type(exc).__name__}: {exc}")
        return "failed"

    if turn.handed_back():
        current = ideas.get(reach.conn, idea.id)
        status = current.enrichment if current else "failed"
        log.info("idea %s enrichment %s", idea.id, status)
        return status if status in OUTCOMES else "done"

    if turn.result.status != "ok":
        note = f"worker: {turn.result.error or turn.result.status}"
    else:
        note = "worker ended without saving"
    _mark(reach, idea.id, "failed", note)
    log.warning("idea %s enrichment failed: %s", idea.id, note)
    return "failed"


def render_find_request(found: finds.Find, settings: Settings) -> str:
    """What the lookup is told of a find: what the listing said, never the family."""
    lines = [f"Find {found.id}: {found.title}", f"Page: {found.url}"]
    if found.starts_at:
        lines.append(f"On: {found.starts_at}" + (f" to {found.ends_at}" if found.ends_at else ""))
    else:
        lines.append("On: any time (a place to go)")
    where = ", ".join(part for part in (found.venue, found.address) if part)
    if where:
        lines.append(f"Where: {where}")
    if found.summary:
        lines.append(f"The listing said: {found.summary}")
    lines.append(f"Home area: {settings.home_area or 'not set'}")
    lines.append(
        f"Hand back with save_find (find_id={found.id}) or skip_find (find_id={found.id})."
    )
    return "\n".join(lines)


def fill_find(reach: Reach, found: finds.Find) -> str:
    """Look one find up and keep what the pages say; returns done, skipped, failed or deferred.
    A turn that ends without a hand-back is marked tried, so the next evening moves on."""
    request = render_find_request(found, reach.settings)
    try:
        turn = reach_turn(
            reach,
            "fill_find",
            request,
            f"find {found.id} {found.title}",
            find_id=found.id,
            geocoder=True,
        )
    except AgentError as exc:
        if exc.retryable or isinstance(exc, LIMITS):
            log.warning("filling in find %s deferred: %s", found.id, exc)
            return "deferred"
        _tried(reach, found.id, f"worker: {exc}")
        return "failed"
    except Exception as exc:
        log.exception("filling in find %s crashed", found.id)
        _tried(reach, found.id, f"error: {type(exc).__name__}: {exc}")
        return "failed"
    if turn.handed_back("save_find"):
        return "done"
    if turn.handed_back("skip_find"):
        return "skipped"
    _tried(reach, found.id, f"worker: {turn.result.error or turn.result.status}")
    return "failed"


def _tried(reach: Reach, find_id: int, note: str) -> None:
    with transaction(reach.conn):
        finds.mark_filled(
            reach.conn,
            find_id,
            place_id=None,
            facts={},
            note=note,
            now=utc_iso(reach.clock.now()),
        )


# -- recipes (docs/RECIPES.md) --------------------------------------------------------------------

# What a link that will never be read says: the address check refused it, so no model is asked.
REFUSED = ("not a web address", "not a public address")


def read_recipe(reach: Reach, idea: Idea, pages: PageAPI | None = None) -> str:
    """Read a recipe's link by code, for nothing: "done" when its page carried a recipe block,
    "refused" when the address is not one this server reads (no model is asked either), else
    "unread", left for the paid lookup with why."""
    recipe = recipe_store.get(reach.conn, idea.id)
    url = (recipe.source_url if recipe else None) or idea.url
    now = utc_iso(reach.clock.now())
    if not url:
        return "refused"
    try:
        found = recipe_page.read(url, pages or RecipePages())
    except PageError as exc:
        note = str(exc)
        refused = note in REFUSED
        with transaction(reach.conn):
            meals.not_read(reach.conn, idea, note, status="failed" if refused else None, now=now)
        log.info("recipe %s not read by code: %s", idea.id, note)
        return "refused" if refused else "unread"
    if found is None:
        with transaction(reach.conn):
            meals.not_read(reach.conn, idea, "no recipe on the page", status=None, now=now)
        return "unread"
    facts = {
        "name": found.name,
        "ingredients": found.ingredients,
        "steps": found.steps,
        "active_minutes": found.active_minutes,
        "total_minutes": found.total_minutes,
        "serves": found.serves,
    }
    with transaction(reach.conn):
        meals.from_page(reach.conn, idea, facts, by="page", tags=found.tags, now=now)
    log.info("recipe %s read by code", idea.id)
    return "done"


def render_recipe_request(idea: Idea, recipe: recipe_store.Recipe | None) -> str:
    """What the recipe reader is told: the link, the title, why code could not read it."""
    url = (recipe.source_url if recipe else None) or idea.url
    lines = [f"Recipe #{idea.id}: {idea.title}", f"Link: {url}"]
    if recipe and recipe.fill_note:
        lines.append(f"Read without a browser, the page gave: {recipe.fill_note}")
    lines.append(
        f"Hand back with save_recipe (idea_id={idea.id}) or skip_recipe (idea_id={idea.id})."
    )
    return "\n".join(lines)


def fill_recipe_in(reach: Reach, idea: Idea, pages: PageAPI | None = None) -> str:
    """A recipe's link: read by code first, whenever that has not been tried; the paid reader only
    for a page code could not. Returns done, skipped, failed or deferred."""
    recipe = recipe_store.get(reach.conn, idea.id)
    if recipe is None or (recipe.filled_at is None and recipe.fill_note is None):
        read = read_recipe(reach, idea, pages)
        if read == "done":
            return "done"
        if read == "refused":
            return "failed"
        recipe = recipe_store.get(reach.conn, idea.id)
    try:
        turn = reach_turn(
            reach,
            "fill_recipe",
            render_recipe_request(idea, recipe),
            f"#{idea.id} {idea.title}",
            idea_id=idea.id,
        )
    except AgentError as exc:
        if exc.retryable or isinstance(exc, LIMITS):
            log.warning("reading recipe %s deferred: %s", idea.id, exc)
            return "deferred"
        _mark(reach, idea.id, "failed", f"worker: {exc}")
        return "failed"
    except Exception as exc:
        log.exception("reading recipe %s crashed", idea.id)
        _mark(reach, idea.id, "failed", f"error: {type(exc).__name__}: {exc}")
        return "failed"
    if turn.handed_back("save_recipe"):
        return "done"
    if turn.handed_back("skip_recipe"):
        current = ideas.get(reach.conn, idea.id)
        return current.enrichment if current and current.enrichment in OUTCOMES else "skipped"
    note = f"worker: {turn.result.error or turn.result.status}"
    if turn.result.status == "ok":
        note = "worker ended without saving"
    _mark(reach, idea.id, "failed", note)
    return "failed"
