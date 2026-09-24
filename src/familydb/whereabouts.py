"""Where a member is, when they have said: a location shared on Telegram, used for a few hours.

Sharing is an explicit act (the paperclip, then Location), and the confirmation is worded by code,
not a model: saving where someone is is not worth a paid call to acknowledge. A live location
moving along is recorded without a word. The coordinates never reach a model; the suggestion
engine reads them to estimate travel, and the model is told only whose location it was.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from familydb.app import App
from familydb.channels.base import OutgoingMessage
from familydb.dates import utc_iso
from familydb.store import locations, members, messages
from familydb.store.db import transaction
from familydb.store.locations import SharedLocation

# Long enough for an afternoon out; after that "here" is probably somewhere else.
FRESH = timedelta(hours=3)
# Kept no longer than a day, then deleted.
KEEP = timedelta(hours=24)

SHARED = (
    'Got your location. For the next 3 hours, "what\'s near here?" and "open now" start from '
    "there instead of home."
)


def share(
    app: App,
    conn: sqlite3.Connection,
    *,
    channel: str,
    channel_user_id: str,
    chat_id: str,
    lat: float,
    lon: float,
    live: bool,
) -> OutgoingMessage | None:
    """Record a member's shared location. Returns the confirmation to deliver, or None."""
    member = members.resolve(conn, channel, channel_user_id)
    if member is None:
        return None  # a stranger's location is not ours to keep
    now = app.clock.now()
    with transaction(conn):
        before = locations.get(conn, member.id)
        locations.record(conn, member.id, lat=lat, lon=lon, live=live, now=utc_iso(now))
        locations.forget_before(conn, utc_iso(now - KEEP))
        if live and before is not None and before.live and _fresh(before, now):
            return None  # the same live location moving along
        out = messages.insert_out(
            conn, channel=channel, chat_id=chat_id, text=SHARED, now=utc_iso(now)
        )
    return OutgoingMessage(chat_id, SHARED, "ok", out_message_id=out.id)


def current(conn: sqlite3.Connection, member_id: int, now: datetime) -> SharedLocation | None:
    """Where the member shared from within the last few hours, or None."""
    shared = locations.get(conn, member_id)
    return shared if shared is not None and _fresh(shared, now) else None


def minutes_ago(shared: SharedLocation, now: datetime) -> int:
    return max(0, int((now - datetime.fromisoformat(shared.shared_at)).total_seconds() // 60))


def _fresh(shared: SharedLocation, now: datetime) -> bool:
    return now - datetime.fromisoformat(shared.shared_at) <= FRESH
