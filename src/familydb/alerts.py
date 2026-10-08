"""Telling an admin what only an admin can fix, on Telegram, with no model call.

Kinds (`KINDS`): credit and key (a company's account or key; about: company), limit (the day's
spending limit), calendar (Google refused the key, or none is saved), calendar_access (the key
works but the calendar is not there for it), model, price, prices, new and shift (from the daily
check, model_watch.py and usage_watch.py), api (a company refused a part of a request, now sent
without it; agent/providers/parts.py), refused (a refusal FamilyDB cannot read, told
once it happens twice without an answer between, then a judgement is asked), advice (what a
judgement answered and what came of it), backup and disk (the hourly upkeep, upkeep.py),
telegram (the bot token refused; shown on the Status page only, `NOT_ON_TELEGRAM`), happening (a
source of what is on near home unread three days running; about: the source; jobs/happening.py)
and calendars (new event calendars found near home, to tick on the settings page; told once).

Each is noted where it is seen, in a short write of its own, and forgotten when that thing is
seen to work again, so the next time is told at once. The minute job (`run_alerts`) tells every
admin with a Telegram id in her words (`voice.EVENTS` alert_*), again at most every TELL_AGAIN
while it lasts. It reads one table and returns when there is nothing to say; the status page
lists the same troubles.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from familydb import happening, voice
from familydb.agent.providers import companies
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import alerts as alert_store
from familydb.store import members, messages
from familydb.store.db import transaction

log = logging.getLogger(__name__)

KINDS = (
    "credit",
    "key",
    "limit",
    "calendar",
    "calendar_access",
    "model",
    "price",
    "prices",
    "new",
    "shift",
    "api",
    "refused",
    "advice",
    "happening",
    "calendars",
    "backup",
    "disk",
    "telegram",
)
COMPANY_KINDS = ("credit", "key", "refused")
# Shown on the Status page and never told on Telegram, which cannot carry news of itself.
NOT_ON_TELEGRAM = frozenset({"telegram"})
TOLD_AFTER = {"refused": 2}
TELL_AGAIN = timedelta(hours=12)
KEEP = timedelta(days=7)
TELEGRAM = "telegram"


def note(
    conn: sqlite3.Connection,
    kind: str,
    about: str,
    detail: str,
    now: datetime,
    *,
    once: bool = False,
) -> None:
    """Record a trouble, or with `once` news told once. Never raises: the failure being handled
    matters more.
    """
    try:
        with transaction(conn):
            alert_store.note(
                conn,
                kind,
                about,
                detail,
                now=utc_iso(now),
                keep_after=utc_iso(now - KEEP),
                once=once,
            )
    except sqlite3.Error as exc:
        log.warning("could not note a %s trouble: %s", kind, exc)
    else:
        log.warning("noted for an admin: %s %s (%s)", kind, about, detail)


def noticed(
    conn: sqlite3.Connection,
    exc: AgentError,
    *,
    provider: str,
    now: datetime,
    model: str | None = None,
) -> None:
    if exc.trouble in COMPANY_KINDS:
        note(conn, exc.trouble, provider, str(exc), now)
        if exc.trouble == "refused" and alert_store.times(conn, "refused", provider) >= 2:
            from familydb import judgement
            from familydb.agent.providers import refusable_parts

            judgement.file_refused(conn, provider, model, str(exc), refusable_parts(provider), now)
    elif exc.trouble == "model" and model:
        note(
            conn,
            "model",
            f"{provider}:{model.lower()}",
            f"{companies.named(provider)} says it has no model called {model}, so "
            "everything asked of it fails until another is chosen",
            now,
        )


def dropped(
    conn: sqlite3.Connection,
    provider: str,
    model: str | None,
    left_out: tuple[str, ...],
    now: datetime,
) -> None:
    """A company answered once a refused part was left out: tell an admin once, since it works but
    without something it had.
    """
    company = companies.named(provider)
    for part in left_out:
        note(
            conn,
            "api",
            f"{provider}:{(model or '').lower()}:{part}",
            f"{company} no longer takes {part} for {model}, so it is now left out and the rest "
            "works without it; a newer FamilyDB may know what takes its place",
            now,
            once=True,
        )


def answered(conn: sqlite3.Connection, provider: str, model: str | None = None) -> None:
    """A company answered. Call inside the transaction that records the call: one small delete, only
    when there was something to forget.
    """
    if alert_store.any_for(conn, COMPANY_KINDS, provider):
        for kind in COMPANY_KINDS:
            alert_store.clear(conn, kind, provider)
    if model and alert_store.any_for(conn, ("model",), f"{provider}:{model.lower()}"):
        alert_store.clear(conn, "model", f"{provider}:{model.lower()}")


def working(conn: sqlite3.Connection, kind: str, about: str = "") -> None:
    try:
        with transaction(conn):
            alert_store.clear(conn, kind, about)
    except sqlite3.Error as exc:
        log.warning("could not clear a %s trouble: %s", kind, exc)


def wording(settings: Any, alert: alert_store.Alert) -> str:
    company = companies.named(alert.subject)
    # Only the lines about things near home name its page, so no other line's choice of wording
    # moves (voice.say chooses by its facts).
    page = {"page": happening.NAME} if alert.kind in ("happening", "calendars") else {}
    return voice.say(
        settings,
        f"alert_{alert.kind}",
        company=company,
        limit=f"{settings.daily_spend_limit:.2f}",
        detail=alert.detail,
        **page,
    )


def admins_on_telegram(conn: sqlite3.Connection) -> list[members.Member]:
    return [
        person
        for person in members.list_all(conn)
        if person.role == "admin" and person.channel == TELEGRAM and person.channel_user_id
    ]


def run_alerts(app: Any) -> int:
    with closing(app.connect()) as conn:
        app.refresh(conn)
        if not app.settings.admin_alerts:
            return 0
        now = app.clock.now()
        told_before = utc_iso(now - TELL_AGAIN)
        due = [
            alert
            for alert in alert_store.due(conn, told_before=told_before)
            if alert.times >= TOLD_AFTER.get(alert.kind, 1) and alert.kind not in NOT_ON_TELEGRAM
        ]
        if not due:
            return 0
        admins = admins_on_telegram(conn)
        if not admins or TELEGRAM not in app.senders:
            # Nobody to tell on Telegram, or Telegram not running here: the status page says so;
            # tried again next minute.
            return 0
        told = 0
        for alert in due:
            text = wording(app.settings, alert)
            stored: list[tuple[int, str]] = []
            with transaction(conn):
                if not any(
                    again.kind == alert.kind and again.subject == alert.subject
                    for again in alert_store.due(conn, told_before=told_before)
                ):
                    continue
                for admin in admins:
                    chat = str(admin.channel_user_id)
                    out = messages.insert_out(
                        conn, channel=TELEGRAM, chat_id=chat, text=text, now=utc_iso(now)
                    )
                    stored.append((out.id, chat))
                alert_store.mark_told(conn, alert.kind, alert.subject, now=utc_iso(now))
            for message_id, chat in stored:
                voice.hand_over(
                    app,
                    conn,
                    message_id,
                    event=f"alert_{alert.kind}",
                    channel=TELEGRAM,
                    chat_id=chat,
                    mention=alert.kind,
                )
            told += 1
        return told
