"""The daily spending limit: estimated dollars across every model call, checked before each one.

Every paid call goes through the turn loop, so checking there covers the chat, the lookups, the
discovery searches and the digest alike. The estimate comes from `providers/prices.py`; a model
not listed there is counted dearer than any that is, so the limit errs towards stopping.

A turn already running when the limit is crossed stops before its next call rather than half way
through one, so a day can end slightly over the limit, by at most one call.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, time

from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import calls

REPLY = (
    "Today's spending limit (${limit:.2f}) is used up, so I can't answer until tomorrow. "
    "Ask again then, or raise the limit on the settings page."
)


class SpendingLimitReached(AgentError):
    """The day's limit is used up. Not retryable: the answer is tomorrow or a higher limit."""

    def __init__(self, spent: float, limit: float) -> None:
        super().__init__(
            f"daily spending limit reached: ${spent:.2f} of ${limit:.2f}", retryable=False
        )
        self.spent = spent
        self.limit = limit
        self.reply = REPLY.format(limit=limit)


def day_start(settings: Settings, now: datetime) -> str:
    """Midnight today in the family's timezone, as the UTC timestamp calls are stored under."""
    local = now.astimezone(settings.tzinfo)
    return utc_iso(datetime.combine(local.date(), time(), tzinfo=settings.tzinfo))


def spent_today(conn: sqlite3.Connection, settings: Settings, now: datetime) -> float:
    return calls.spent_since(conn, since=day_start(settings, now))


def used_up(conn: sqlite3.Connection, settings: Settings, now: datetime) -> bool:
    limit = settings.daily_spend_limit
    return bool(limit) and spent_today(conn, settings, now) >= limit


def check(conn: sqlite3.Connection, settings: Settings, now: datetime) -> None:
    """Raise SpendingLimitReached when today's calls have used the limit up."""
    if used_up(conn, settings, now):
        raise SpendingLimitReached(spent_today(conn, settings, now), settings.daily_spend_limit)
