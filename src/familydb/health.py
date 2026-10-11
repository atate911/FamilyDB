"""Whether FamilyDB is well, for /healthz, `familydb health` and Docker's HEALTHCHECK: the
database answers, and a scheduler that should be running is ticking (store/heartbeat.py). A page
served on its own (`familydb web`) has no scheduler, and one stopped on purpose is not trouble;
only one that went quiet while running is. No model call, one small read."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from familydb.base.dates import utc_iso
from familydb.store import db, heartbeat
from familydb.store.db import transaction

log = logging.getLogger(__name__)

# The settings watch ticks every five minutes (jobs/scheduler.py): three missed is not a hiccup.
QUIET = timedelta(minutes=15)


def check(app: Any) -> tuple[bool, str]:
    """(well, what to say): "ok", or what is wrong."""
    try:
        with closing(app.connect()) as conn:
            db.answers(conn)
            try:
                beat = heartbeat.read(conn)
            except sqlite3.OperationalError:
                beat = None  # not migrated yet: no scheduler has run on it
    except sqlite3.Error as exc:
        log.warning("health: the database did not answer: %s", exc)
        return False, "the database does not answer"
    if beat is None or beat.stopped_at is not None:
        return True, "ok"
    since = app.clock.now() - datetime.fromisoformat(beat.jobs_at.replace("Z", "+00:00"))
    if since > QUIET:
        minutes = int(since.total_seconds() // 60)
        return False, f"the scheduled jobs have not run for {minutes} minutes"
    return True, "ok"


def ticked(app: Any) -> None:
    """The scheduler is running: said at start and on each settings watch."""
    with closing(app.connect()) as conn, transaction(conn):
        heartbeat.beat(conn, utc_iso(app.clock.now()))


def stopped(app: Any) -> None:
    """Stopped on purpose: its silence from now on is not trouble."""
    with closing(app.connect()) as conn, transaction(conn):
        heartbeat.stopped(conn, utc_iso(app.clock.now()))
