"""The daily spending limit: estimated dollars across every model call, checked before each one.

Every paid call goes through the turn loop, so checking there covers the chat, the lookups, the
discovery searches and the digest alike. The estimate comes from `providers/prices.py`; a model
not listed there is counted dearer than any that is, so the limit errs towards stopping.

Before a call goes out, `admit` checks the limit and sets aside the call's estimated cost as a
hold, in one short write transaction, so two processes cannot both pass on the same dollars and
no lock is held over the network. `settle` records the call and gives the hold back. Holds count
against the limit, but not against the call that made them, so one call can still cross it. A
hold older than `HOLD_MINUTES` was left by a crash and stops counting. A timed-out call whose
vendor charges are unknown is outside the estimate.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, time, timedelta
from typing import Any

from familydb.agent.providers import prices
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import calls
from familydb.store.db import transaction

# Longer than any call with its retries and a fallback can take (the SDKs time out at 120s).
HOLD_MINUTES = 30
# A rough count, used only to size a hold; the call records what the vendor reported.
CHARS_PER_TOKEN = 4

REPLY = (
    "Today's spending limit (${limit:.2f}) is used up, so I can't answer until tomorrow. "
    "Ask again then, or raise the limit on the settings page."
)


# What each writing tool did, and which record in its summary names what it wrote.
DONE = {
    "add_task": ("Saved task", "task_id"),
    "update_task": ("Updated task", "task_id"),
    "create_event": ("Created calendar plan", "plan_id"),
    "update_event": ("Updated calendar plan", "plan_id"),
    "delete_event": ("Cancelled calendar plan", "plan_id"),
    "add_idea": ("Saved idea", "idea_id"),
    "update_idea": ("Updated idea", "idea_id"),
    "record_outcome": ("Recorded outcome", "outcome_id"),
    "save_place": ("Saved place details", "idea_id"),
    "skip_place": ("Marked lookup skipped", "idea_id"),
}


def done_lines(actions: list[dict[str, Any]]) -> str:
    """What these completed writes did, one short sentence each, worded by code."""
    lines = []
    for action in actions:
        label, key = DONE.get(action["tool"], ("Completed " + action["tool"], "id"))
        identity = action.get(key, action.get("id"))
        if action.get("duplicate_of") is not None:
            label, identity = "Kept existing idea", action["duplicate_of"]
        lines.append(label + (f" #{identity}" if identity is not None else "") + ".")
    return " ".join(lines)


def completed_reply(actions: list[dict[str, Any]]) -> str:
    """Explain durable progress without spending another model call to acknowledge it."""
    return done_lines(actions) + (
        " That much is saved, but today's spending limit stopped me before I finished. "
        "Check what is saved before asking for the rest, so nothing is done twice."
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


def estimate(
    provider: str,
    model: str | None,
    *,
    input_chars: int,
    max_tokens: int,
    searches: int = 0,
    cache_ttl: str = "1h",
) -> float:
    """The most one call could cost: every input character uncached, every output token used."""
    usage = {
        "input_tokens": input_chars // CHARS_PER_TOKEN,
        "output_tokens": max_tokens,
        "web_searches": searches,
    }
    return prices.cost(provider, model, usage, cache_ttl=cache_ttl)[0]


def admit(conn: sqlite3.Connection, settings: Settings, now: datetime, cost: float) -> int:
    """Check the limit and hold this call's estimated cost; raise when the day is used up."""
    with transaction(conn):
        _check(conn, settings, now, other_than=None)
        return calls.hold(conn, cost_usd=cost, now=utc_iso(now))


def adjust(
    conn: sqlite3.Connection, settings: Settings, now: datetime, hold_id: int, cost: float
) -> None:
    """Hold what the call will now cost, before it is sent: a fallback to a dearer model must not
    leave the cheaper model's estimate standing while others spend the difference. Checked as
    `admit` checks, not counting this call's own hold; refused, the hold is given back."""
    with transaction(conn):
        try:
            _check(conn, settings, now, other_than=hold_id)
        except SpendingLimitReached:
            settle(conn, hold_id, now)
            raise
        calls.rehold(conn, hold_id, cost_usd=cost)


def _check(
    conn: sqlite3.Connection, settings: Settings, now: datetime, *, other_than: int | None
) -> None:
    limit = settings.daily_spend_limit
    if not limit:
        return
    since = day_start(settings, now)
    used = calls.spent_since(conn, since=since) + calls.held_since(
        conn,
        since=max(since, utc_iso(now - timedelta(minutes=HOLD_MINUTES))),
        other_than=other_than,
    )
    if used >= limit:
        raise SpendingLimitReached(used, limit)


def settle(conn: sqlite3.Connection, hold_id: int, now: datetime) -> None:
    """Give a hold back; call inside the transaction that records the call, or after a failure."""
    calls.release(conn, hold_id, stale_before=utc_iso(now - timedelta(minutes=HOLD_MINUTES)))


def day_start(settings: Settings, now: datetime) -> str:
    """Midnight today in the family's timezone, as the UTC timestamp calls are stored under."""
    local = now.astimezone(settings.tzinfo)
    return utc_iso(datetime.combine(local.date(), time(), tzinfo=settings.tzinfo))


def spent_today(conn: sqlite3.Connection, settings: Settings, now: datetime) -> float:
    return calls.spent_since(conn, since=day_start(settings, now))


def used_up(conn: sqlite3.Connection, settings: Settings, now: datetime) -> bool:
    limit = settings.daily_spend_limit
    return bool(limit) and spent_today(conn, settings, now) >= limit
