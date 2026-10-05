"""Day-after follow-ups, no model call: the question is stored as an outbound message in the
plan's chat, so the chat model sees it in history and records the answer as an outcome."""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import date, timedelta
from typing import Any

from familydb import buttons, routing, voice
from familydb.app import App
from familydb.calendar_sync import sync_plans
from familydb.dates import utc_iso
from familydb.delivery import run_deliveries
from familydb.store import messages, outcomes, plans
from familydb.store.db import transaction
from familydb.store.plans import Plan

log = logging.getLogger(__name__)

FOLLOW_UP_DAYS = 7  # older plans are left alone


def render_follow_up(plan: Plan, settings: Any) -> str:
    when = date.fromisoformat(plan.start[:10])
    label = f"#{plan.idea_id} {plan.title}" if plan.idea_id else plan.title
    return voice.say(settings, "follow_up", plan=label, day=f"{when:%A}")


def run_follow_ups(app: App) -> int:
    """Ask about each plan that ended before today and was not asked about; returns how many."""
    asked = 0
    run_deliveries(app)  # what an earlier run could not send goes first
    with closing(app.connect()) as conn:
        app.refresh(conn)
        if not app.settings.follow_ups:
            return 0
        # Don't ask about a plan cancelled in Google; if Google cannot be asked, wait.
        if app.calendar is not None:
            try:
                sync_plans(
                    conn, app.calendar, app.settings.google_calendar_id, utc_iso(app.clock.now())
                )
            except Exception:
                log.exception("follow-ups deferred: the calendar could not be checked")
                return 0
        today = app.clock.today()
        since = today - timedelta(days=FOLLOW_UP_DAYS)
        due = plans.due_for_follow_up(conn, today=today.isoformat(), since=since.isoformat())
        for plan in due:
            now = utc_iso(app.clock.now())
            if outcomes.exists_since(
                conn, idea_id=plan.idea_id, plan_id=plan.id, since=plan.start[:10]
            ):
                with transaction(conn):
                    plans.mark_followed_up(conn, plan.id, now=now)
                continue
            sender = app.senders.get(plan.channel or "")
            if sender is None or plan.chat_id is None:
                log.info(
                    "follow-up for plan %s waits: nothing here can send to %s",
                    plan.id,
                    plan.channel,
                )
                continue
            text = render_follow_up(plan, app.settings)
            # Asked of the plan's maker, in their own chat when it began in a group (routing.py).
            channel, chat_id = routing.for_person(
                conn, app.settings, plan.channel or "", plan.chat_id, plan.created_by
            )
            with transaction(conn):
                # Re-read under the write lock: a manual run can race the scheduler.
                if plans.get(conn, plan.id).followed_up_at is not None:  # type: ignore[union-attr]
                    continue
                outbound = messages.insert_out(
                    conn,
                    channel=channel,
                    chat_id=chat_id,
                    text=text,
                    now=now,
                    buttons=buttons.for_follow_up(plan.id) if plan.idea_id else None,
                )
                plans.mark_followed_up(conn, plan.id, now=now)
            voice.hand_over(
                app,
                conn,
                outbound.id,
                event="follow_up",
                channel=channel,
                chat_id=chat_id,
                mention=plan.title,
            )
            asked += 1
    return asked
