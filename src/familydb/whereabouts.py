"""Where a member is, for a few hours: shared on Telegram, or sent by the web page's chat.

On Telegram sharing is an explicit act (the paperclip, then Location), confirmed once in words
written by code, not a model: saving where someone is is not worth a paid call to acknowledge. A
live location moving along is recorded without a word, and so is the position the web page sends
with a message. Each is named once ("Pearl District, Portland") with the free reverse geocoder,
so the chat model and the discovery worker are told where the family is, without anyone typing it.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from familydb import voice
from familydb.app import App
from familydb.channels.base import OutgoingMessage
from familydb.dates import utc_iso
from familydb.integrations.geocode import haversine_km
from familydb.store import locations, members, messages
from familydb.store.db import transaction
from familydb.store.locations import SharedLocation

# Long enough for an afternoon out; after that "here" is probably somewhere else.
FRESH = timedelta(hours=3)
# Kept no longer than a day, then deleted.
KEEP = timedelta(hours=24)

# Closer than this to the last named position, the name is kept rather than looked up again.
SAME_PLACE_KM = 0.2


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
    """Record a location shared on Telegram. Returns the confirmation to deliver, or None."""
    member = members.resolve(conn, channel, channel_user_id)
    if member is None:
        return None  # a stranger's location is not ours to keep
    now = app.clock.now()
    before = locations.get(conn, member.id)
    label = _name(app, before, lat, lon)
    with transaction(conn):
        _keep(conn, member.id, lat, lon, live, label, now)
        if live and before is not None and before.live and _fresh(before, now):
            return None  # the same live location moving along
        text = shared_text(label, app.settings)
        out = messages.insert_out(
            conn, channel=channel, chat_id=chat_id, text=text, now=utc_iso(now)
        )
    return OutgoingMessage(chat_id, text, "ok", out_message_id=out.id)


def note(app: App, conn: sqlite3.Connection, member_id: int, lat: float, lon: float) -> None:
    """Record the position the web page sent with a message, without a word back."""
    now = app.clock.now()
    label = _name(app, locations.get(conn, member_id), lat, lon)
    with transaction(conn):
        _keep(conn, member_id, lat, lon, True, label, now)


def shared_text(label: str | None, settings: Any) -> str:
    """The confirmation, in the assistant's voice (voice.py)."""
    return voice.say(settings, "location_shared", where=f" ({label})" if label else "")


def _keep(conn, member_id, lat, lon, live, label, now) -> None:
    locations.record(conn, member_id, lat=lat, lon=lon, live=live, now=utc_iso(now), label=label)
    locations.forget_before(conn, utc_iso(now - KEEP))


def _name(app: App, before: SharedLocation | None, lat: float, lon: float) -> str | None:
    """The place's name: kept from the last share when it is the same place, else looked up."""
    if (
        before is not None
        and before.label
        and haversine_km(before.lat, before.lon, lat, lon) < (SAME_PLACE_KM)
    ):
        return before.label
    reverse = getattr(app.geocoder, "reverse", None)
    return reverse(lat, lon) if reverse is not None else None


def current(conn: sqlite3.Connection, member_id: int, now: datetime) -> SharedLocation | None:
    """Where the member shared from within the last few hours, or None."""
    shared = locations.get(conn, member_id)
    return shared if shared is not None and _fresh(shared, now) else None


def minutes_ago(shared: SharedLocation, now: datetime) -> int:
    return max(0, int((now - datetime.fromisoformat(shared.shared_at)).total_seconds() // 60))


def _fresh(shared: SharedLocation, now: datetime) -> bool:
    return now - datetime.fromisoformat(shared.shared_at) <= FRESH
