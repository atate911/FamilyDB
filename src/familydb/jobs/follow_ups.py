"""Day-after follow-ups: ask how a plan went so the answer becomes feedback for its idea.

No model call is needed to ask. The question is stored as an outbound message in the plan's chat,
so when the family answers, the chat model sees its own question in the history and records the
outcome through the normal feedback path.
"""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import date, timedelta

from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import messages, outcomes, plans
from familydb.store.db import transaction
from familydb.store.plans import Plan

log = logging.getLogger(__name__)

FOLLOW_UP_DAYS = 7  # plans older than this are left alone; asking weeks later is odd


def render_follow_up(plan: Plan) -> str:
    when = date.fromisoformat(plan.start[:10])
    label = f"#{plan.idea_id} {plan.title}" if plan.idea_id else plan.title
    return f"How was {label} on {when:%A}? Worth doing again?"


def run_follow_ups(app: App) -> int:
    """Ask about each plan that ended before today and was not asked about; returns how many."""
    asked = 0
    with closing(app.connect()) as conn:
        app.refresh(conn)
        today = app.clock.today()
        since = today - timedelta(days=FOLLOW_UP_DAYS)
        due = plans.due_for_follow_up(conn, today=today.isoformat(), since=since.isoformat())
        for plan in due:
            now = utc_iso(app.clock.now())
            if outcomes.exists_since(
                conn, idea_id=plan.idea_id, plan_id=plan.id, since=plan.start[:10]
            ):
                # Someone already said how it went; nothing to ask.
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
            text = render_follow_up(plan)
            with transaction(conn):
                messages.insert_out(
                    conn, channel=plan.channel or "", chat_id=plan.chat_id, text=text, now=now
                )
                plans.mark_followed_up(conn, plan.id, now=now)
            try:
                sender(plan.chat_id, text)
            except Exception:
                log.exception("could not deliver the follow-up for plan %s", plan.id)
            asked += 1
    return asked
