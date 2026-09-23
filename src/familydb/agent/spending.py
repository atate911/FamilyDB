"""The daily spending limit: estimated dollars across every model call, checked before each one.

Every paid call goes through the turn loop, so checking there covers the chat, the lookups, the
discovery searches and the digest alike. The estimate comes from `providers/prices.py`; a model
not listed there is counted dearer than any that is, so the limit errs towards stopping.

Paid calls and their accounting are serialized per database by agent.admission. The limit is
checked after acquiring that lock. One successfully accounted call can cross the estimated
limit; a timed-out call with unknown vendor charges cannot be included in that guarantee.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, time
from typing import Any

from familydb.config import Settings
from familydb.dates import utc_iso
from familydb.errors import AgentError
from familydb.store import calls

REPLY = (
    "Today's spending limit (${limit:.2f}) is used up, so I can't answer until tomorrow. "
    "Ask again then, or raise the limit on the settings page."
)


def completed_reply(actions: list[dict[str, Any]]) -> str:
    """Explain durable progress without spending another model call to acknowledge it."""
    labels = {
        "create_event": "Created calendar plan",
        "update_event": "Updated calendar plan",
        "delete_event": "Cancelled calendar plan",
        "add_idea": "Saved idea",
        "update_idea": "Updated idea",
        "record_outcome": "Recorded outcome",
        "save_place": "Saved place details",
        "skip_place": "Marked lookup skipped",
    }
    lines = []
    for action in actions:
        label = labels.get(action["tool"], "Completed " + action["tool"])
        identity = next(
            (
                action[k]
                for k in ("plan_id", "idea_id", "id", "outcome_id")
                if action.get(k) is not None
            ),
            None,
        )
        if action.get("duplicate_of") is not None:
            label, identity = "Kept existing idea", action["duplicate_of"]
        lines.append(label + (f" #{identity}" if identity is not None else "") + ".")
    return " ".join(lines) + (
        " These changes are saved. Today's spending limit stopped the rest of this request. "
        "Review the saved changes before asking for any remaining work; do not repeat them."
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
