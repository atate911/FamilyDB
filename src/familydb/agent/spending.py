"""The daily spending limit: estimated dollars across every model call, checked before each one.

Every paid call is checked here first: each model call of a turn by the turn loop, which covers
the chat, the lookups, the discovery searches and the digest, and each voice note by
`gateway.listen`. The estimate comes from `providers/prices.py`; a model not listed there is
counted dearer than any that is, so the limit errs towards stopping.

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

from familydb.agent.providers import LOOK_TOKENS, prices
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import alerts as alert_store
from familydb.store import calls
from familydb.store.db import transaction

# Longer than any call with its retries and a fallback can take (the SDKs time out at 120s).
HOLD_MINUTES = 30
# A rough count, used only to size a hold; the call records what the vendor reported.
CHARS_PER_TOKEN = 4

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
    "remember": ("Noted what you told me", "memory_id"),
    "add_wish": ("Put it on the wish list", "wish_id"),
    "update_wish": ("Updated wish", "wish_id"),
    "turn_away": ("Noted the request", "wish_id"),
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


def completed_reply(
    actions: list[dict[str, Any]],
    settings: Settings,
    message_id: int | None = None,
    *,
    plain: bool = False,
) -> str:
    """Explain durable progress without spending another model call to acknowledge it. The
    message being answered, when there is one, chooses the wording (`voice.say`); `plain` is for
    a chat a kid reads (audience.py)."""
    from familydb import voice

    said = voice.say(settings, "limit_partial", seed=message_id, plain=plain)
    return done_lines(actions) + " " + said


class SpendingLimitReached(AgentError):
    """The day's limit is used up. Not retryable: the answer is tomorrow or a higher limit.

    In the chat the family is told in the voice layer's words (`voice.py`), not this message."""

    def __init__(self, spent: float, limit: float) -> None:
        super().__init__(
            f"daily spending limit reached: ${spent:.2f} of ${limit:.2f}", retryable=False
        )
        self.spent = spent
        self.limit = limit


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


# Only to size the hold on hearing a recording; the call records what was billed. Audio at 32
# tokens a second, Gemini's rate and more than OpenAI counts, and its words at a generous 8.
AUDIO_TOKENS_PER_SECOND = 32
WORDS_TOKENS_PER_SECOND = 8


def estimate_hearing(provider: str, model: str | None, seconds: int) -> float:
    """The most hearing one recording could cost, whether it is billed by token or by minute."""
    seconds = max(seconds, 1)
    usage = {
        "input_tokens": seconds * AUDIO_TOKENS_PER_SECOND + 200,
        "output_tokens": seconds * WORDS_TOKENS_PER_SECOND + 400,
        "audio_seconds": seconds,
    }
    return prices.cost(provider, model, usage)[0]


# Only to size the hold on looking at a photo; the call records what was billed. A large picture,
# as the vendors count one, the words asking for it, and every token the answer may use.
PICTURE_TOKENS = 2500
ASK_TOKENS = 300


def estimate_looking(provider: str, model: str | None) -> float:
    """The most looking at one photo could cost."""
    usage = {"input_tokens": PICTURE_TOKENS + ASK_TOKENS, "output_tokens": LOOK_TOKENS}
    return prices.cost(provider, model, usage)[0]


def admit(conn: sqlite3.Connection, settings: Settings, now: datetime, cost: float) -> int:
    """Check the limit and hold this call's estimated cost; raise when the day is used up.

    Used up, it is noted for an admin (alerts.py), under the family's date, once the check's own
    transaction is over; let through, a note of it for today, if any, is forgotten."""
    today = now.astimezone(settings.tzinfo).date().isoformat()
    try:
        with transaction(conn):
            _check(conn, settings, now, other_than=None)
            if alert_store.any_for(conn, ("limit",), today):
                alert_store.clear(conn, "limit", today)
            return calls.hold(conn, cost_usd=cost, now=utc_iso(now))
    except SpendingLimitReached as exc:
        from familydb import alerts

        alerts.note(conn, "limit", today, str(exc), now)
        raise


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


def kid_used_up(
    conn: sqlite3.Connection, settings: Settings, now: datetime, member_id: int
) -> bool:
    """Whether a kid's own share of the day is spent (docs/WISHES.md). Checked before each of
    her messages, so one message may cross it; the family's limit still holds every call."""
    share = settings.kid_daily_spend
    spent = calls.spent_since_by(conn, since=day_start(settings, now), member_id=member_id)
    return bool(share) and spent >= share


def used_up(conn: sqlite3.Connection, settings: Settings, now: datetime) -> bool:
    limit = settings.daily_spend_limit
    return bool(limit) and spent_today(conn, settings, now) >= limit
