"""Guiding a kid's wording, "we should" towards "I want" (docs/WISHES.md), decided by code.

The girls say "we should…" when they mean "I want". Code reads her message and, now and then,
asks the bot to reflect it back kindly in the reply it is writing anyway: at most once a day, on
the first "we should" of a day when she has said it often this week, and otherwise no more than
every few days, so the nudges thin out as she improves. Saying "I want" earns a warm word now and
then. No model call is made for any of it; the chat call carries one word in her turn line.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta
from typing import Literal

from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.store import messages, wishes
from familydb.store.db import transaction

Wording = Literal["nudge", "praise"]

# "we should get a puppy", "we could go to Disneyland", "can we have pizza", "let's get slime".
WE_SHOULD = re.compile(
    r"^\W*(?:(?:we|us)\s+(?:should|could|need\s+to|have\s+to|gotta|ought\s+to)"
    r"|can\s+we|could\s+we|let['\u2019]?s\s+(?:get|buy|have|go))\b",
    re.IGNORECASE,
)
# "I want", "I'd like", "I would like", "I really want". An iPad types a curly apostrophe.
I_WANT = re.compile(
    r"\bI(?:\s+(?:really\s+)?(?:want|would\s+like|wish)|['\u2019]d\s+like)\b", re.IGNORECASE
)
# Said often in a week (settings.wording_daily_after), she is nudged on the first "we should" of
# any day; less often, no more than every few days.
EVERY_FEW_DAYS = 3
PRAISE_EVERY = 3


def says_we_should(text: str) -> bool:
    return bool(WE_SHOULD.search(text))


def says_i_want(text: str) -> bool:
    return bool(I_WANT.search(text))


def _days_since(last: str | None, today: date) -> int | None:
    return None if last is None else (today - date.fromisoformat(last)).days


def choose(
    conn: sqlite3.Connection,
    settings: Settings,
    member_id: int,
    text: str,
    now: datetime,
) -> Wording | None:
    """Whether to nudge her wording, or praise it, in this reply; noted for today if so."""
    today = now.astimezone(settings.tzinfo).date()
    if says_we_should(text):
        last = _days_since(wishes.last_wording(conn, member_id, "nudge"), today)
        if last == 0:
            return None
        week = messages.said_by_since(conn, member_id, utc_iso(now - timedelta(days=7)))
        often = sum(1 for said in week if says_we_should(said)) >= settings.wording_daily_after
        if often or last is None or last >= EVERY_FEW_DAYS:
            return _noted(conn, member_id, today, "nudge")
        return None
    if says_i_want(text):
        last = _days_since(wishes.last_wording(conn, member_id, "praise"), today)
        if last is None or last >= PRAISE_EVERY:
            return _noted(conn, member_id, today, "praise")
    return None


def _noted(conn: sqlite3.Connection, member_id: int, today: date, kind: Wording) -> Wording:
    with transaction(conn):
        wishes.mark_wording(conn, member_id, today.isoformat(), kind)
    return kind
