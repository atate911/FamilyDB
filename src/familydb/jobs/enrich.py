"""Enrichment: look up each new idea's place on the web and store what was found. By default
lookups wait for the evening (`lookups_when`, `lookup_hour`) and each chat gets one note; an idea
asked for now (`look_up_now`) goes on the next run with its own note; "asap" looks each up as it
comes."""

from __future__ import annotations

import logging
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from typing import Any

from familydb import routing, voice
from familydb.agent import spending
from familydb.agent.loop import MessagesAPI
from familydb.app import App
from familydb.availability import enrichment_available
from familydb.base.config import Settings
from familydb.base.dates import last_hour_passed, utc_iso
from familydb.scouting import fill
from familydb.scouting.fill import OUTCOMES
from familydb.scouting.reach import Reach
from familydb.store import ideas, messages, places
from familydb.store.db import transaction
from familydb.store.ideas import Idea
from familydb.store.places import Place

log = logging.getLogger(__name__)

# The most one evening looks up; the rest wait.
EVENING_MOST = 40


def lookups_due_before(settings: Settings, now: datetime) -> str | None:
    """None when each idea is looked up as it comes; else the last evening lookup hour passed,
    as a UTC stamp: ideas waiting since before it are due."""
    if settings.lookups_when == "asap":
        return None
    return utc_iso(last_hour_passed(now, settings.lookup_hour, settings.tzinfo))


def render_place_note(idea: Idea, place: Place, settings: Any) -> str:
    """The one-line chat note after an idea is filled in."""
    return voice.say(
        settings, "lookup_done", idea=idea.id, place=place.name, details=place_details(place)
    )


def render_evening_note(found: list[tuple[Idea, Place]], settings: Any) -> str:

    if len(found) == 1:
        return render_place_note(*found[0], settings)
    listed = "\n".join(
        f"• #{idea.id} {place.name}: {place_details(place)}" for idea, place in found
    )
    return voice.say(settings, "lookups_done", count=len(found), found=listed)


def place_details(place: Place) -> str:
    """What was found, in a line."""
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


def _origin(app: App, conn: Any, idea: Idea) -> tuple[Any, Place] | None:
    """The message an idea came from and its place, when a note can be sent there."""
    if not app.settings.enrichment_notes or idea.source_message_id is None:
        return None
    origin = messages.get(conn, idea.source_message_id)
    if origin is None or app.senders.get(origin.channel) is None:
        return None
    place = places.get(conn, idea.place_id) if idea.place_id else None
    return (origin, place) if place is not None else None


def _notify(app: App, conn: Any, idea: Idea) -> None:
    """Post the 'filled in' note to the idea's chat, when possible and wanted."""
    found = _origin(app, conn, idea)
    if found is None:
        return
    origin, place = found
    _send_note(app, conn, origin, render_place_note(idea, place, app.settings), place.name)


def _to(app: App, conn: Any, origin: Any) -> tuple[str, str]:
    """Where a note goes: the teller's own chat when it came from a group (routing.py)."""
    return routing.for_person(conn, app.settings, origin.channel, origin.chat_id, origin.member_id)


def _notify_together(app: App, conn: Any, done: list[int]) -> None:

    by_chat: dict[tuple[str, str], list[tuple[Any, Idea, Place]]] = defaultdict(list)
    for idea_id in done:
        idea = ideas.get(conn, idea_id)
        found = _origin(app, conn, idea) if idea is not None else None
        if idea is not None and found is not None:
            origin, place = found
            by_chat[_to(app, conn, origin)].append((origin, idea, place))
    for rows in by_chat.values():
        text = render_evening_note([(idea, place) for _, idea, place in rows], app.settings)
        _send_note(app, conn, rows[-1][0], text, rows[0][2].name, together=len(rows) > 1)


def _send_note(
    app: App, conn: Any, origin: Any, text: str, mention: str, *, together: bool = False
) -> None:
    channel, chat_id = _to(app, conn, origin)
    here = (channel, chat_id) == (origin.channel, origin.chat_id)
    with transaction(conn):
        outbound = messages.insert_out(
            conn,
            channel=channel,
            chat_id=chat_id,
            text=text,
            reply_to=origin.id if here else None,
            now=utc_iso(app.clock.now()),
        )
    voice.hand_over(
        app,
        conn,
        outbound.id,
        event="lookups_done" if together else "lookup_done",
        channel=channel,
        chat_id=chat_id,
        mention=mention,
    )


def enrich_idea(
    app: App, conn: Any, idea: Idea, *, api: MessagesAPI | None = None, note: bool = True
) -> str:
    """Look one idea up (scouting/fill.py); returns done, skipped, failed or deferred. With
    `note` off (the evening's lookups) the run says it all at once."""
    status = fill.fill_in(Reach.of_app(app, conn, api), idea)
    current = ideas.get(conn, idea.id) if status == "done" and note else None
    if current is not None and current.enrichment == "done":
        try:
            _notify(app, conn, current)
        except Exception:
            log.exception("could not note the enrichment of idea %s", idea.id)
    return status


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
        found: list[int] = []  # the evening's, noted together after the run
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
