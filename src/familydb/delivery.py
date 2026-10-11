"""Durable outgoing messages, and the claims that stop two workers doing one message's work.

A reply is stored before it is sent and marked delivered only after the send succeeded, so
delivery is at least once: Telegram offers no idempotency key, so a send whose answer was lost
can arrive twice. Sending again never reruns the model or touches the calendar.

A claim (`lease`) is a row lock with an expiry, renewed while the worker works; a worker that
dies lets it lapse and the next retry job takes over. A message kept to be answered with the ones
after it (pipeline.receive) is held under the `GATHER` mark instead: the retry job leaves it
until the mark lapses, while the turn answering it may take it over (`lease`, or `claim_also` for
a burst's earlier ones). Every row under one claim is renewed and let go with it.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from datetime import timedelta
from typing import TYPE_CHECKING

from familydb.base.dates import utc_iso
from familydb.store import messages
from familydb.store.db import transaction

if TYPE_CHECKING:
    from familydb.app import App

log = logging.getLogger(__name__)
LEASE_SECONDS = 300
RENEW_SECONDS = 30
GATHER = "gather"
Sender = Callable[[str, str], None]


class Claim:
    def __init__(self, token: str | None) -> None:
        self.token = token

    def __bool__(self) -> bool:
        return self.token is not None


@contextmanager
def lease(app: App, conn: sqlite3.Connection, message_id: int) -> Iterator[Claim]:
    """Claim one message for as long as the block runs; yields a false Claim when someone else has
    it. A message held for gathering is taken over.

    Renewed on its own thread and connection so a long model turn keeps its claim; released at
    the end, success or not, with every row taken under it (`claim_also`).
    """
    token = uuid.uuid4().hex
    now = utc_iso(app.clock.now())
    until = utc_iso(app.clock.now() + timedelta(seconds=LEASE_SECONDS))
    with transaction(conn):
        won = messages.claim(conn, message_id, token=token, until=until, now=now, held_as=GATHER)
    if not won:
        yield Claim(None)
        return
    stop = threading.Event()

    def renew() -> None:
        while not stop.wait(RENEW_SECONDS):
            try:
                with closing(app.connect()) as own, transaction(own):
                    later = utc_iso(app.clock.now() + timedelta(seconds=LEASE_SECONDS))
                    messages.renew_claim(own, token, until=later)
            except Exception:
                log.exception("could not renew message claim %s", message_id)

    thread = threading.Thread(target=renew, daemon=True)
    thread.start()
    try:
        yield Claim(token)
    finally:
        stop.set()
        thread.join(timeout=10)
        with transaction(conn):
            messages.release_claim(conn, token)


def hold_for_gathering(conn: sqlite3.Connection, message_id: int, *, until: str) -> None:
    """Keep a stored message from the retry job while it waits to be answered with the ones after
    it. Call inside a transaction.
    """
    messages.hold(conn, message_id, mark=GATHER, until=until)


def claim_also(
    app: App, conn: sqlite3.Connection, claim: Claim, message_ids: list[int]
) -> list[int]:
    """Take messages held for gathering under a claim already won. Returns the ones taken: another
    turn may have taken the rest.
    """
    until = utc_iso(app.clock.now() + timedelta(seconds=LEASE_SECONDS))
    taken = []
    with transaction(conn):
        for message_id in message_ids:
            if messages.take_held(conn, message_id, mark=GATHER, token=claim.token, until=until):
                taken.append(message_id)
    return taken


def deliver(app: App, message_id: int, sender: Sender | None = None) -> bool:
    """Send one stored reply and mark it delivered, in that order. True when it went.

    `sender` stands in for the channel's own, for a caller holding the conversation open
    (console, a Telegram update being answered).
    """
    with closing(app.connect()) as conn, lease(app, conn, message_id) as owned:
        if not owned:
            return False
        row = messages.get(conn, message_id)
        if row is None or row.direction != "out" or row.delivered_at or row.cancelled_at:
            return False
        send = sender or app.senders.get(row.channel)
        if send is None:
            return False
        with_buttons = app.button_senders.get(row.channel) if row.buttons and not sender else None
        try:
            if with_buttons is not None:
                with_buttons(row.chat_id, row.text, row.buttons)
            else:
                send(row.chat_id, row.text)
        except Exception:
            log.exception("delivery pending for message %s", message_id)
            return False
        with transaction(conn):
            messages.mark_delivered(conn, [message_id], now=utc_iso(app.clock.now()))
        # One she sent of her own accord: the channel may tell a device too (push.py). Whatever
        # becomes of that, the message is delivered.
        notify = app.notifiers.get(row.channel) if row.sent_as else None
        if notify is not None:
            try:
                notify(conn, row)
            except Exception:
                log.exception("could not tell any device of message %s", message_id)
        return True


def run_deliveries(app: App) -> int:
    with closing(app.connect()) as conn:
        ids = messages.undelivered(conn)
    now = app.clock.now()
    return sum(deliver(app, i) for i in ids if not app.held.is_held(i, now))
