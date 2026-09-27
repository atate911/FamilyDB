"""Telling an admin what only an admin can fix, on Telegram, with no model call.

Four kinds of trouble:

- credit: a company says its account is out of credit or over its quota (about: the company);
- key: a company refused its key (about: the company);
- limit: the day's spending limit is used up (about: the family's date);
- calendar: Google no longer lets the bot in, so plans are not reaching the calendar;
- model: a model the family uses is gone, or going on a date (about: company and model);
- price: the price of a model they use moved (told once for each new price);
- prices: a price list could not be read, or the lists disagree about a model in use;
- new: new models to choose from (once a day at most, for each company);
- shift: what a kind of call costs or does moved a long way in a week (usage_watch.py);
- api: a company refused a part of a request (a dated beta, a tool version, a setting) for a
  model, which is now sent without it (agent/providers/parts.py; about: company, model, part);
- refused: a company refused requests for a reason FamilyDB cannot read (about: the company),
  told once it has happened twice without an answer between, since one odd request is not news.

Five come from the daily check of models and prices (model_watch.py).

Each is noted where it is seen, in a short write of its own: a refusal read by the provider
module (`AgentError.trouble`) in the loop and the gateway, the limit in `spending.admit`, Google
in the calendar client. It is forgotten when that thing is seen to work again (the company
answered, a call was let through, Google answered), so the next time is told at once.

The minute job (`run_alerts`) tells every admin with a Telegram id, in her words (`voice.EVENTS`
alert_*), and again at most every TELL_AGAIN while the trouble goes on. It reads one table and
returns when there is nothing to say. The status page lists the same troubles.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from familydb import voice
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
    "model",
    "price",
    "prices",
    "new",
    "shift",
    "api",
    "refused",
)
# About a company: the ones a company's own answer clears.
COMPANY_KINDS = ("credit", "key", "refused")
# Told only once seen this many times: a single refusal may be one odd request.
TOLD_AFTER = {"refused": 2}
TELL_AGAIN = timedelta(hours=12)
KEEP = timedelta(days=7)
TELEGRAM = "telegram"
COMPANY_NAMES = {"openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Google Gemini"}


def note(
    conn: sqlite3.Connection,
    kind: str,
    about: str,
    detail: str,
    now: datetime,
    *,
    once: bool = False,
) -> None:
    """Record a trouble, or with `once` a piece of news told once. Never raises: the failure
    being handled matters more than this note."""
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
    """A model call failed: note it when it is something only an admin can fix."""
    if exc.trouble in COMPANY_KINDS:
        note(conn, exc.trouble, provider, str(exc), now)
    elif exc.trouble == "model" and model:
        note(
            conn,
            "model",
            f"{provider}:{model.lower()}",
            f"{COMPANY_NAMES.get(provider, provider)} says it has no model called {model}, so "
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
    """A company answered once a part of the request it refused was left out: tell an admin
    once, since it is working, but without something it used to have."""
    company = COMPANY_NAMES.get(provider, provider)
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
    """A company answered. Call inside the transaction that records the call: one small delete,
    and only when there was something to forget."""
    if alert_store.any_for(conn, COMPANY_KINDS, provider):
        for kind in COMPANY_KINDS:
            alert_store.clear(conn, kind, provider)
    if model and alert_store.any_for(conn, ("model",), f"{provider}:{model.lower()}"):
        alert_store.clear(conn, "model", f"{provider}:{model.lower()}")


def working(conn: sqlite3.Connection, kind: str, about: str = "") -> None:
    """Something is seen to work again. Never raises."""
    try:
        with transaction(conn):
            alert_store.clear(conn, kind, about)
    except sqlite3.Error as exc:
        log.warning("could not clear a %s trouble: %s", kind, exc)


def wording(settings: Any, alert: alert_store.Alert) -> str:
    """What an admin is told, in her words: which company, or what the limit is."""
    company = COMPANY_NAMES.get(alert.subject, alert.subject)
    return voice.say(
        settings,
        f"alert_{alert.kind}",
        company=company,
        limit=f"{settings.daily_spend_limit:.2f}",
        detail=alert.detail,
    )


def admins_on_telegram(conn: sqlite3.Connection) -> list[members.Member]:
    return [
        person
        for person in members.list_all(conn)
        if person.role == "admin" and person.channel == TELEGRAM and person.channel_user_id
    ]


def run_alerts(app: Any) -> int:
    """Tell admins about every trouble that is due; returns how many troubles were told."""
    with closing(app.connect()) as conn:
        app.refresh(conn)
        if not app.settings.admin_alerts:
            return 0
        now = app.clock.now()
        told_before = utc_iso(now - TELL_AGAIN)
        due = [
            alert
            for alert in alert_store.due(conn, told_before=told_before)
            if alert.times >= TOLD_AFTER.get(alert.kind, 1)
        ]
        if not due:
            return 0
        admins = admins_on_telegram(conn)
        if not admins or TELEGRAM not in app.senders:
            # Nobody to tell on Telegram, or Telegram is not running here: the status page says
            # so, and the job tries again next minute.
            return 0
        told = 0
        for alert in due:
            text = wording(app.settings, alert)
            stored: list[tuple[int, str]] = []
            with transaction(conn):
                # Again under the write lock: a second process may have told them a moment ago.
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
            # Stored first, sent second: a send that fails stays queued for the retry job.
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
