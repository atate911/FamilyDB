"""The daily spending limit: estimated dollars (`providers/prices.py`), checked before every call
(the loop, `gateway.listen`, `gateway.look`).

`admit` holds the call's estimated cost in one short write transaction, so two processes cannot
pass on the same dollars and no lock spans the network; `settle` gives the hold back. Holds count
against other calls, not their own, so one call can cross the limit. A hold older than
`HOLD_MINUTES` was left by a crash and stops counting."""

from __future__ import annotations

import sqlite3
from datetime import datetime, time, timedelta
from typing import Any

from familydb.agent.providers import LOOK_TOKENS, companies, prices
from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import alerts as alert_store
from familydb.store import calls
from familydb.store.db import transaction

# Longer than any call with its retries and a fallback (the SDKs time out at 120s).
HOLD_MINUTES = 30
# Sizes a hold only; the call records what the vendor reported.
CHARS_PER_TOKEN = 4

# What each writing tool did, and the summary key naming what it wrote.
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
    """Report completed writes with no further model call; the message chooses the wording
    (`voice.say`), `plain` is for a kid's chat (audience.py)."""
    from familydb import voice

    said = voice.say(settings, "limit_partial", seed=message_id, plain=plain)
    return done_lines(actions) + " " + said


class SpendingLimitReached(AgentError):
    """The day's limit is used up; not retryable. The chat says it in `voice.py`'s words."""

    def __init__(self, spent: float, limit: float) -> None:
        super().__init__(
            f"daily spending limit reached: ${spent:.2f} of ${limit:.2f}", retryable=False
        )
        self.spent = spent
        self.limit = limit


class CompanyLimitReached(AgentError):
    """The most the family said to spend on one company in a month is spent. Not retryable: a use
    chosen to it is answered by a stand-in, and with none it waits for the month to turn."""

    def __init__(self, company: str, spent: float, limit: float) -> None:
        super().__init__(
            f"the monthly limit for {company} is reached: ${spent:.2f} of ${limit:.2f}",
            retryable=False,
        )
        self.company = company
        self.spent = spent
        self.limit = limit


def month_start(settings: Settings, now: datetime) -> str:
    """When this calendar month began, in the family's time zone, as a UTC timestamp."""
    local = now.astimezone(settings.tzinfo)
    return utc_iso(datetime.combine(local.date().replace(day=1), time(), tzinfo=settings.tzinfo))


def company_spent(
    conn: sqlite3.Connection, settings: Settings, now: datetime, company: str
) -> float:
    """Estimated dollars spent on this company so far this month."""
    return calls.spent_by_provider(conn, company, since=month_start(settings, now))


def company_full(conn: sqlite3.Connection, settings: Settings, now: datetime, company: str) -> bool:
    """Whether the company's monthly limit, if the family set one, is spent."""
    limit = companies.monthly_limit(company, settings)
    return limit is not None and company_spent(conn, settings, now, company) >= limit


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


# Sizes the hold on a recording only: audio at Gemini's 32 tokens a second, words a generous 8.
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


# Sizes the hold on a photo only: a large picture, the ask, and every token the answer may use.
PICTURE_TOKENS = 2500
ASK_TOKENS = 300


def estimate_looking(provider: str, model: str | None) -> float:
    """The most looking at one photo could cost."""
    usage = {"input_tokens": PICTURE_TOKENS + ASK_TOKENS, "output_tokens": LOOK_TOKENS}
    return prices.cost(provider, model, usage)[0]


def admit(
    conn: sqlite3.Connection,
    settings: Settings,
    now: datetime,
    cost: float,
    company: str | None = None,
) -> int:
    """Check the limit and hold this call's estimated cost; raise when the day is used up (noted
    for an admin after the check's transaction ends; let through, every day's note is cleared), or
    when the company it goes to has had its month's worth."""
    today = now.astimezone(settings.tzinfo).date().isoformat()
    try:
        with transaction(conn):
            _check(conn, settings, now, other_than=None)
            if company is not None and company_full(conn, settings, now, company):
                raise CompanyLimitReached(
                    company,
                    company_spent(conn, settings, now, company),
                    companies.monthly_limit(company, settings) or 0.0,
                )
            alert_store.clear_kind(conn, "limit")
            return calls.hold(conn, cost_usd=cost, now=utc_iso(now))
    except SpendingLimitReached as exc:
        from familydb import alerts

        alerts.note(conn, "limit", today, str(exc), now)
        raise


def adjust(
    conn: sqlite3.Connection, settings: Settings, now: datetime, hold_id: int, cost: float
) -> None:
    """Re-hold at the fallback's price before it is asked, so a dearer model's difference is not
    left unheld. Checked as `admit`, not counting its own hold; refused, the hold is released."""
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
    """Whether a kid's own share of the day is spent (docs/WISHES.md); one message may cross it."""
    share = settings.kid_daily_spend
    spent = calls.spent_since_by(conn, since=day_start(settings, now), member_id=member_id)
    return bool(share) and spent >= share


def used_up(conn: sqlite3.Connection, settings: Settings, now: datetime) -> bool:
    limit = settings.daily_spend_limit
    return bool(limit) and spent_today(conn, settings, now) >= limit
