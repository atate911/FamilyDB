"""Enrichment: look up each new idea's place on the web and store what was found."""

from __future__ import annotations

import json
import logging
from contextlib import closing
from typing import Any

from familydb.agent.loop import MessagesAPI
from familydb.agent.worker import WorkerTurn, home_location, run_worker_turn
from familydb.app import App
from familydb.availability import enrichment_available
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import ideas, messages, places
from familydb.store.db import transaction
from familydb.store.ideas import Idea
from familydb.store.places import Place

log = logging.getLogger(__name__)

OUTCOMES = ("done", "skipped", "failed", "deferred")


def render_enrich_request(idea: Idea, place: Place | None, settings: Settings) -> str:
    """What the worker is told about the idea it should look up."""
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


def render_place_note(idea: Idea, place: Place) -> str:
    """The one-line chat note after an idea is filled in."""
    parts = [f"Filled in #{idea.id} {place.name}:"]
    if place.summary:
        parts.append(place.summary.rstrip("."))
    if place.hours:
        known = [day for day, ranges in place.hours.items() if ranges]
        closed = [day for day, ranges in place.hours.items() if not ranges]
        if known:
            parts.append(f"hours saved for {', '.join(known)}")
        if closed:
            parts.append(f"closed {', '.join(closed)}")
    else:
        parts.append("hours unknown")
    if place.travel_minutes is not None:
        parts.append(f"about {place.travel_minutes} min away (estimate)")
    if place.booking_url:
        parts.append(f"tickets: {place.booking_url}")
    if place.price_note:
        parts.append(place.price_note)
    return " · ".join(parts)


def _mark(conn: Any, app: App, idea_id: int, status: str, note: str | None) -> None:
    now = utc_iso(app.clock.now())
    with transaction(conn):
        ideas.update(
            conn,
            idea_id,
            {"enrichment": status, "enriched_at": now, "enrichment_note": note},
            now=now,
        )


def _notify(app: App, conn: Any, idea: Idea) -> None:
    """Post the 'filled in' note to the chat the idea came from, when possible and wanted."""
    if not app.settings.enrichment_notes or idea.source_message_id is None:
        return
    origin = messages.get(conn, idea.source_message_id)
    if origin is None:
        return
    sender = app.senders.get(origin.channel)
    place = places.get(conn, idea.place_id) if idea.place_id else None
    if sender is None or place is None:
        return
    text = render_place_note(idea, place)
    with transaction(conn):
        messages.insert_out(
            conn,
            channel=origin.channel,
            chat_id=origin.chat_id,
            text=text,
            reply_to=origin.id,
            now=utc_iso(app.clock.now()),
        )
    try:
        sender(origin.chat_id, text)
    except Exception:
        log.exception("could not deliver the enrichment note for idea %s", idea.id)


def enrich_idea(app: App, conn: Any, idea: Idea, *, api: MessagesAPI | None = None) -> str:
    """Look one idea up. Returns done, skipped, failed or deferred (try again later)."""
    place = places.get(conn, idea.place_id) if idea.place_id else None
    request = render_enrich_request(idea, place, app.settings)
    try:
        turn: WorkerTurn = run_worker_turn(
            kind="enrich",
            api=api,
            settings=app.settings,
            clock=app.clock,
            registry=app.registry,
            conn=conn,
            request=request,
            geocoder=app.geocoder,
            user_location=home_location(app.settings),
        )
    except AgentError as exc:
        if exc.retryable:
            log.warning("enrichment of idea %s deferred: %s", idea.id, exc)
            return "deferred"
        _mark(conn, app, idea.id, "failed", f"worker: {exc}")
        return "failed"
    except Exception as exc:
        # Anything else would leave the idea pending and burn a model call every run.
        log.exception("enrichment of idea %s crashed", idea.id)
        _mark(conn, app, idea.id, "failed", f"error: {type(exc).__name__}: {exc}")
        return "failed"

    if turn.handed_back("save_place") or turn.handed_back("skip_place"):
        current = ideas.get(conn, idea.id)
        status = current.enrichment if current else "failed"
        if status == "done" and current is not None:
            try:
                _notify(app, conn, current)
            except Exception:
                log.exception("could not note the enrichment of idea %s", idea.id)
        log.info("idea %s enrichment %s", idea.id, status)
        return status if status in OUTCOMES else "done"

    if turn.result.status != "ok":
        note = f"worker: {turn.result.error or turn.result.status}"
    else:
        note = "worker ended without saving"
    _mark(conn, app, idea.id, "failed", note)
    log.warning("idea %s enrichment failed: %s", idea.id, note)
    return "failed"


def run_enrichment(
    app: App,
    *,
    api: MessagesAPI | None = None,
    idea_id: int | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    """Look up pending ideas (or one given idea). Returns counts per outcome."""
    counts = dict.fromkeys(OUTCOMES, 0)
    if not enrichment_available(app.settings):
        log.debug("enrichment skipped: web tools are off")
        return counts
    with closing(app.connect()) as conn:
        if idea_id is not None:
            idea = ideas.get(conn, idea_id)
            batch = [idea] if idea is not None else []
        else:
            batch = ideas.pending_enrichment(conn, limit=limit or app.settings.enrich_batch)
        if not batch:
            return counts
        for idea in batch:
            outcome = enrich_idea(app, conn, idea, api=api)
            counts[outcome] += 1
            if outcome == "deferred":
                break
    return counts
