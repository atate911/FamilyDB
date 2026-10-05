"""Where a member is, for a few hours: shared on Telegram, or sent by the web chat.

A Telegram share is confirmed once in code's words (a paid call to acknowledge is not worth it);
a live location moving along and the web page's position are recorded silently. Each is named
once with the free reverse geocoder, so the chat model and discovery worker know where the family
is without anyone typing it.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
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

FRESH = timedelta(hours=3)
# Kept no longer than a day: deleted by the next share or by `forget_old` on the scheduler's round.
KEEP = timedelta(hours=24)

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
    member = members.resolve(conn, channel, channel_user_id)
    if member is None:
        return None
    now = app.clock.now()
    before = locations.get(conn, member.id)
    label = _name(app, before, lat, lon)
    with transaction(conn):
        _keep(conn, member.id, lat, lon, live, label, now)
        if live and before is not None and before.live and _fresh(before, now):
            return None
        text = shared_text(label, app.settings)
        out = messages.insert_out(
            conn, channel=channel, chat_id=chat_id, text=text, now=utc_iso(now)
        )
    return OutgoingMessage(chat_id, text, "ok", out_message_id=out.id)


def note(app: App, conn: sqlite3.Connection, member_id: int, lat: float, lon: float) -> None:
    now = app.clock.now()
    label = _name(app, locations.get(conn, member_id), lat, lon)
    with transaction(conn):
        _keep(conn, member_id, lat, lon, True, label, now)


def forget_old(app: App) -> int:
    with closing(app.connect()) as conn, transaction(conn):
        return locations.forget_before(conn, utc_iso(app.clock.now() - KEEP))


def shared_text(label: str | None, settings: Any) -> str:
    return voice.say(settings, "location_shared", where=f" ({label})" if label else "")


def _keep(conn, member_id, lat, lon, live, label, now) -> None:
    locations.record(conn, member_id, lat=lat, lon=lon, live=live, now=utc_iso(now), label=label)
    locations.forget_before(conn, utc_iso(now - KEEP))


def _name(app: App, before: SharedLocation | None, lat: float, lon: float) -> str | None:
    if (
        before is not None
        and before.label
        and haversine_km(before.lat, before.lon, lat, lon) < (SAME_PLACE_KM)
    ):
        return before.label
    reverse = getattr(app.geocoder, "reverse", None)
    return reverse(lat, lon) if reverse is not None else None


def current(conn: sqlite3.Connection, member_id: int, now: datetime) -> SharedLocation | None:
    shared = locations.get(conn, member_id)
    return shared if shared is not None and _fresh(shared, now) else None


def minutes_ago(shared: SharedLocation, now: datetime) -> int:
    return max(0, int((now - datetime.fromisoformat(shared.shared_at)).total_seconds() // 60))


def _fresh(shared: SharedLocation, now: datetime) -> bool:
    return now - datetime.fromisoformat(shared.shared_at) <= FRESH
