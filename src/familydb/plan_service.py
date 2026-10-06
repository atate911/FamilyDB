"""What follows a plan, kept in step when the plan changes.

A plan changes two ways: through the tools (`update_event`, a cancel) and in Google, when somebody
moves or deletes its event there (`calendar_sync.apply_event`). Both call `changed`, inside the
transaction that stored the change, so what hangs on the plan never lags behind it: a plan that
moved is checked again the evening before its new day and asked about after it
(`checked_at`, `followed_up_at`).
"""

from __future__ import annotations

import sqlite3

from familydb.store import plans
from familydb.store.plans import Plan


def changed(conn: sqlite3.Connection, before: Plan, after: Plan, *, now: str) -> None:
    """Put right what follows a plan that changed from `before` to `after`. Call inside the
    transaction that stored `after`."""
    if after.status != "cancelled" and after.start != before.start:
        # Checked or asked about for the day it was on: its new day has its own evening before,
        # and its own day after.
        plans.ask_again(conn, after.id)
