"""Durable outgoing messages, and the claims that stop two workers doing one message's work.

A reply is stored before it is sent and marked delivered only once the send succeeded, so a
send that fails is tried again by the next job rather than lost. Delivery is therefore at least
once: Telegram offers no idempotency key, so a send that succeeded but whose answer was lost
can arrive twice. Sending again never runs the model or touches the calendar again.

A claim (`lease`) is a row-level lock with an expiry. The worker holding it renews it while it
works; one that dies simply lets it lapse, and the next retry job can take the message over.
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

from familydb.dates import utc_iso
from familydb.store import messages
from familydb.store.db import transaction

if TYPE_CHECKING:
    from familydb.app import App

log = logging.getLogger(__name__)
LEASE_SECONDS = 300
RENEW_SECONDS = 30
Sender = Callable[[str, str], None]


@contextmanager
def lease(app: App, conn: sqlite3.Connection, message_id: int) -> Iterator[bool]:
    """Claim one message for as long as the block runs. Yields False when someone else has it.

    Renewed on its own thread and connection while the block runs, so a long model turn does
    not lose its claim halfway; released at the end whether the block succeeded or not.
    """
    token = uuid.uuid4().hex
    now = utc_iso(app.clock.now())
    until = utc_iso(app.clock.now() + timedelta(seconds=LEASE_SECONDS))
    with transaction(conn):
        won = (
            conn.execute(
                "UPDATE messages SET claim_token = ?, claim_until = ? "
                "WHERE id = ? AND (claim_until IS NULL OR claim_until <= ?)",
                (token, until, message_id, now),
            ).rowcount
            == 1
        )
    if not won:
        yield False
        return
    stop = threading.Event()

    def renew() -> None:
        while not stop.wait(RENEW_SECONDS):
            try:
                with closing(app.connect()) as own, transaction(own):
                    own.execute(
                        "UPDATE messages SET claim_until = ? WHERE id = ? AND claim_token = ?",
                        (
                            utc_iso(app.clock.now() + timedelta(seconds=LEASE_SECONDS)),
                            message_id,
                            token,
                        ),
                    )
            except Exception:
                log.exception("could not renew message claim %s", message_id)

    thread = threading.Thread(target=renew, daemon=True)
    thread.start()
    try:
        yield True
    finally:
        stop.set()
        thread.join(timeout=10)
        with transaction(conn):
            conn.execute(
                "UPDATE messages SET claim_token = NULL, claim_until = NULL "
                "WHERE id = ? AND claim_token = ?",
                (message_id, token),
            )


def deliver(app: App, message_id: int, sender: Sender | None = None) -> bool:
    """Send one stored reply and mark it delivered, in that order. True when it went.

    `sender` stands in for the channel's own, for a caller that is holding the conversation
    open (the console, a Telegram update being answered).
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
        # Its buttons go with it where the channel can show them; anywhere else, its words do.
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
            conn.execute(
                "UPDATE messages SET delivered_at = ? WHERE id = ?",
                (utc_iso(app.clock.now()), message_id),
            )
        return True


def run_deliveries(app: App) -> int:
    """Try every reply that has not gone yet. Returns how many went this time."""
    with closing(app.connect()) as conn:
        ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM messages WHERE direction = 'out' "
                "AND delivered_at IS NULL AND cancelled_at IS NULL ORDER BY id"
            )
        ]
    # A message held for the conversation under way waits for it (voice.hand_over).
    now = app.clock.now()
    return sum(deliver(app, i) for i in ids if not app.held.is_held(i, now))
