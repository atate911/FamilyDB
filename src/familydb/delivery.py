"""Durable outgoing messages and renewable claims shared by channel and job workers.

Delivery is at least once: Telegram provides no idempotency key, so a lost successful
send response can still cause a duplicate notice. It never reruns the model or calendar.
"""

from __future__ import annotations

import logging
import threading
import uuid
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


@contextmanager
def lease(app: App, conn, message_id: int):
    """Only one process owns a message; a crashed process's claim expires."""
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

    def renew():
        while not stop.wait(30):
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


def deliver(app: App, message_id: int, sender=None) -> bool:
    """Send one persisted reply, acknowledging it only after a successful send."""
    with closing(app.connect()) as conn, lease(app, conn, message_id) as owned:
        if not owned:
            return False
        row = messages.get(conn, message_id)
        if row is None or row.direction != "out" or row.delivered_at:
            return False
        send = sender or app.senders.get(row.channel)
        if send is None:
            return False
        try:
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
    with closing(app.connect()) as conn:
        ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM messages WHERE direction = 'out' "
                "AND delivered_at IS NULL ORDER BY id"
            )
        ]
    return sum(deliver(app, message_id) for message_id in ids)
