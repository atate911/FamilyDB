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
import time
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


class Renewer:
    """One thread renews every claim this process holds, every `RENEW_SECONDS`, on one
    connection a round: a long model turn keeps its claim, and a hundred deliveries do not mean a
    hundred threads. Started on the first claim; a daemon, so it never holds the process up."""

    def __init__(self) -> None:
        self._held: dict[str, App] = {}
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def add(self, app: App, token: str) -> None:
        with self._lock:
            self._held[token] = app
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, name="familydb-claims", daemon=True
                )
                self._thread.start()

    def drop(self, token: str) -> None:
        with self._lock:
            self._held.pop(token, None)

    def holding(self) -> int:
        with self._lock:
            return len(self._held)

    def renew_all(self) -> None:
        """Every claim held, kept for another `LEASE_SECONDS` from now; a round that fails is
        logged and tried again next time (the claim lapses only after `LEASE_SECONDS`)."""
        with self._lock:
            by_app: dict[int, tuple[App, list[str]]] = {}
            for token, app in self._held.items():
                by_app.setdefault(id(app), (app, []))[1].append(token)
        for app, tokens in by_app.values():
            try:
                with closing(app.connect()) as own, transaction(own):
                    until = utc_iso(app.clock.now() + timedelta(seconds=LEASE_SECONDS))
                    for token in tokens:
                        messages.renew_claim(own, token, until=until)
            except Exception:
                log.exception("could not renew %d message claim(s)", len(tokens))

    def _run(self) -> None:
        while True:
            time.sleep(RENEW_SECONDS)
            self.renew_all()


RENEWER = Renewer()


@contextmanager
def lease(app: App, conn: sqlite3.Connection, message_id: int) -> Iterator[Claim]:
    """Claim one message for as long as the block runs; yields a false Claim when someone else has
    it. A message held for gathering is taken over.

    Renewed by the process's one `Renewer` so a long model turn keeps its claim; released at the
    end, success or not, with every row taken under it (`claim_also`).
    """
    token = uuid.uuid4().hex
    now = utc_iso(app.clock.now())
    until = utc_iso(app.clock.now() + timedelta(seconds=LEASE_SECONDS))
    with transaction(conn):
        won = messages.claim(conn, message_id, token=token, until=until, now=now, held_as=GATHER)
    if not won:
        yield Claim(None)
        return
    RENEWER.add(app, token)
    try:
        yield Claim(token)
    finally:
        RENEWER.drop(token)
        try:
            with transaction(conn):
                messages.release_claim(conn, token)
        except sqlite3.Error:
            # The claim lapses by itself; what the turn raised is what matters.
            log.exception("could not let go of message claim %s", message_id)


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
