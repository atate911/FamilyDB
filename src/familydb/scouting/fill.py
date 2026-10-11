"""Filling in an idea's details from the web (docs/FINDS.md, "filling in"): one worker turn
finds its place and hands back with `save_place` or `skip_place` (tools/places.py), which keep
what the page says. An idea with nothing to look up (`ideas.needs_lookup`) is skipped with no
call. When ideas are looked up, and what the family is told, is the job's (jobs/enrich.py)."""

from __future__ import annotations

import json
import logging

from familydb.agent.spending import LIMITS
from familydb.agent.worker import WorkerTurn
from familydb.base.config import Settings
from familydb.base.dates import utc_iso
from familydb.base.errors import AgentError
from familydb.scouting.reach import Reach
from familydb.scouting.reach import turn as reach_turn
from familydb.store import ideas, places
from familydb.store.db import transaction
from familydb.store.ideas import Idea, needs_lookup
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


def fill_in(reach: Reach, idea: Idea) -> str:
    """Look one idea up and keep what the page says; returns done, skipped, failed or deferred.
    What the family is told is the job's (jobs/enrich.py)."""
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
