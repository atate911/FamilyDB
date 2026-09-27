"""Enrichment: look up each new idea's place on the web and store what was found.

Filling an idea in rarely changes what the family does next, so by default the lookups wait for
the evening (`lookups_when`, `lookup_hour`): the first run after that hour takes every idea that
was waiting before it, and each chat gets one note for all it found there. An idea somebody asked
for now (`look_up_now`, the page's button, /lookup) is looked up on the next run whatever the
hour, with a note of its own. With `lookups_when` "asap" every idea is looked up as it comes.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from contextlib import closing
from datetime import datetime, time, timedelta
from typing import Any

from familydb import voice
from familydb.agent import spending
from familydb.agent.loop import MessagesAPI
from familydb.agent.spending import SpendingLimitReached
from familydb.agent.worker import WorkerTurn, home_location, run_worker_turn
from familydb.app import App
from familydb.availability import enrichment_available
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import ideas, messages, places
from familydb.store.db import transaction
from familydb.store.ideas import GIFT, Idea
from familydb.store.places import Place

log = logging.getLogger(__name__)

OUTCOMES = ("done", "skipped", "failed", "deferred")
# The most one evening looks up; any more wait for the next. The day's limit still holds.
EVENING_MOST = 40
# Kinds that are never a place to look up. Kept narrow on purpose: a title alone can name a place
# ("Pizza Luna"), so only a kind that means "not out anywhere" decides it, and only while the
# family has given nothing to look up (no location, no link, no place already attached). A gift's
# link is to the thing itself, so only a place named for it (a class somewhere) is looked up.
NO_LOOKUP_KINDS = frozenset({"home", GIFT})
NO_LOOKUP_NOTE = "nothing to look up: a {kind} idea with no place or link"


def needs_lookup(idea: Idea) -> bool:
    """Whether a worker turn could find anything for this idea. Decided in code, for free."""
    if idea.kind not in NO_LOOKUP_KINDS:
        return True
    link = idea.url if idea.kind != GIFT else None
    return bool(idea.location_name or link or idea.place_id)


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


def lookups_due_before(settings: Settings, now: datetime) -> str | None:
    """None when each idea is looked up as it comes; otherwise the last evening lookup hour that
    has passed, as the UTC stamp ideas are stored under: those waiting since before it are due."""
    if settings.lookups_when == "asap":
        return None
    zone = settings.tzinfo
    local = now.astimezone(zone)
    evening = datetime.combine(local.date(), time(settings.lookup_hour), tzinfo=zone)
    if local < evening:
        evening = datetime.combine(
            local.date() - timedelta(days=1), time(settings.lookup_hour), tzinfo=zone
        )
    return utc_iso(evening)


def render_place_note(idea: Idea, place: Place, settings: Any) -> str:
    """The one-line chat note after an idea is filled in, in the assistant's voice."""
    return voice.say(
        settings, "lookup_done", idea=idea.id, place=place.name, details=place_details(place)
    )


def render_evening_note(found: list[tuple[Idea, Place]], settings: Any) -> str:
    """One note for everything the evening's lookups found for a chat."""
    if len(found) == 1:
        return render_place_note(*found[0], settings)
    listed = "\n".join(
        f"• #{idea.id} {place.name}: {place_details(place)}" for idea, place in found
    )
    return voice.say(settings, "lookups_done", count=len(found), found=listed)


def place_details(place: Place) -> str:
    """What was found, in a line: what it is, its hours, how far, tickets, prices."""
    parts: list[str] = []
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
    return " · ".join(parts).rstrip(".")


def _mark(conn: Any, app: App, idea_id: int, status: str, note: str | None) -> None:
    now = utc_iso(app.clock.now())
    with transaction(conn):
        ideas.update(
            conn,
            idea_id,
            {"enrichment": status, "enriched_at": now, "enrichment_note": note},
            now=now,
        )


def _origin(app: App, conn: Any, idea: Idea) -> tuple[Any, Place] | None:
    """The message an idea came from and its place, when a note about it can be sent there."""
    if not app.settings.enrichment_notes or idea.source_message_id is None:
        return None
    origin = messages.get(conn, idea.source_message_id)
    if origin is None or app.senders.get(origin.channel) is None:
        return None
    place = places.get(conn, idea.place_id) if idea.place_id else None
    return (origin, place) if place is not None else None


def _notify(app: App, conn: Any, idea: Idea) -> None:
    """Post the 'filled in' note to the chat the idea came from, when possible and wanted."""
    found = _origin(app, conn, idea)
    if found is None:
        return
    origin, place = found
    _send_note(app, conn, origin, render_place_note(idea, place, app.settings), place.name)


def _notify_together(app: App, conn: Any, done: list[int]) -> None:
    """One note in each chat for everything the evening's lookups found there."""
    by_chat: dict[tuple[str, str], list[tuple[Any, Idea, Place]]] = defaultdict(list)
    for idea_id in done:
        idea = ideas.get(conn, idea_id)
        found = _origin(app, conn, idea) if idea is not None else None
        if idea is not None and found is not None:
            origin, place = found
            by_chat[(origin.channel, origin.chat_id)].append((origin, idea, place))
    for rows in by_chat.values():
        text = render_evening_note([(idea, place) for _, idea, place in rows], app.settings)
        _send_note(app, conn, rows[-1][0], text, rows[0][2].name, together=len(rows) > 1)


def _send_note(
    app: App, conn: Any, origin: Any, text: str, mention: str, *, together: bool = False
) -> None:
    with transaction(conn):
        outbound = messages.insert_out(
            conn,
            channel=origin.channel,
            chat_id=origin.chat_id,
            text=text,
            reply_to=origin.id,
            now=utc_iso(app.clock.now()),
        )
    voice.hand_over(
        app,
        conn,
        outbound.id,
        event="lookups_done" if together else "lookup_done",
        channel=origin.channel,
        chat_id=origin.chat_id,
        mention=mention,
    )


def enrich_idea(
    app: App, conn: Any, idea: Idea, *, api: MessagesAPI | None = None, note: bool = True
) -> str:
    """Look one idea up. Returns done, skipped, failed or deferred (try again later).

    With `note` off (the evening's lookups) nothing is said here: the run says it all at once."""
    if not needs_lookup(idea):
        _mark(conn, app, idea.id, "skipped", NO_LOOKUP_NOTE.format(kind=idea.kind))
        log.info("idea %s enrichment skipped without a model call", idea.id)
        return "skipped"
    place = places.get(conn, idea.place_id) if idea.place_id else None
    request = render_enrich_request(idea, place, app.settings)
    try:
        turn: WorkerTurn = run_worker_turn(
            kind="enrich",
            idea_id=idea.id,
            about=f"#{idea.id} {idea.title}",
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
        if exc.retryable or isinstance(exc, SpendingLimitReached):
            log.warning("enrichment of idea %s deferred: %s", idea.id, exc)
            return "deferred"
        _mark(conn, app, idea.id, "failed", f"worker: {exc}")
        return "failed"
    except Exception as exc:
        # Anything else would leave the idea pending and burn a model call every run.
        log.exception("enrichment of idea %s crashed", idea.id)
        _mark(conn, app, idea.id, "failed", f"error: {type(exc).__name__}: {exc}")
        return "failed"

    if turn.handed_back():
        current = ideas.get(conn, idea.id)
        status = current.enrichment if current else "failed"
        if status == "done" and current is not None and note:
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
    with closing(app.connect()) as conn:
        app.refresh(conn)
        if not enrichment_available(app.settings):
            log.debug("enrichment skipped: web tools are off")
            return counts
        if not app.can_ask("worker", api=api):
            # Not a failure: the ideas wait, pending, and are looked up once a key is added.
            log.debug("enrichment waits: there is no model key yet")
            return counts
        before = lookups_due_before(app.settings, app.clock.now())
        evening = before is not None and idea_id is None
        if idea_id is not None:
            idea = ideas.get(conn, idea_id)
            batch = [idea] if idea is not None else []
        else:
            most = EVENING_MOST if evening else app.settings.enrich_batch
            batch = ideas.due_enrichment(conn, before=before, limit=limit or most)
        if not batch:
            return counts
        if spending.used_up(conn, app.settings, app.clock.now()):
            log.debug("enrichment waits for tomorrow: the daily spending limit is used up")
            return counts
        found: list[int] = []  # the evening's, said together once the run is over
        try:
            for idea in batch:
                together = evening and idea.lookup_wanted_at is None
                outcome = enrich_idea(app, conn, idea, api=api, note=not together)
                counts[outcome] += 1
                if outcome == "deferred":
                    break
                if idea.lookup_wanted_at is not None:
                    with transaction(conn):
                        ideas.lookup_asked_for(conn, idea.id)
                if together and outcome == "done":
                    found.append(idea.id)
        finally:
            if found:
                try:
                    _notify_together(app, conn, found)
                except Exception:
                    log.exception("could not note the evening's lookups")
    return counts
