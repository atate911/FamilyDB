"""The hourly upkeep, with no model call: what only an admin can put right on the server itself,
noted as alerts (familydb/alerts.py) where it is seen and forgotten when it is right again.

- backup: no sound backup for `BACKUP_HOURS`, once one has ever been recorded (an install may
  choose to keep none, and nobody is told about a habit it never had).
- disk: less than `FREE_MB_WANTED` free where the database lives; a full disk stops every write,
  messages included.

A Telegram token that is refused is noted by the channel itself (channels/telegram.py), since
only it knows; that one is shown on the Status page, as Telegram cannot carry it.
"""

from __future__ import annotations

import logging
import shutil
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from familydb import alerts
from familydb.store import backups

log = logging.getLogger(__name__)

BACKUP_HOURS = 36
FREE_MB_WANTED = 500


def run_upkeep(app: Any) -> int:
    """Note or forget the server's troubles; returns how many there are now."""
    app.refresh()
    now = app.clock.now()
    troubles = 0
    with closing(app.connect()) as conn:
        stale = backup_trouble(conn, now)
        if stale:
            alerts.note(conn, "backup", "", stale, now)
            troubles += 1
        else:
            alerts.working(conn, "backup")
        short = disk_trouble(app.settings.familydb_path)
        if short:
            alerts.note(conn, "disk", "", short, now)
            troubles += 1
        else:
            alerts.working(conn, "disk")
    return troubles


def backup_trouble(conn: Any, now: datetime) -> str | None:
    """What is wrong with the backups, or None: none recorded is no trouble."""
    if backups.latest(conn) is None:
        return None
    good = backups.latest(conn, good=True)
    if good is None:
        return "no backup has passed its check yet"
    made = datetime.fromisoformat(good.made_at.replace("Z", "+00:00"))
    if now - made > timedelta(hours=BACKUP_HOURS):
        return f"the last good backup was made {good.made_at[:16].replace('T', ' ')} UTC"
    return None


def disk_trouble(path: Any) -> str | None:
    """How little room is left where the database lives, or None when there is enough."""
    try:
        free = shutil.disk_usage(path.parent if path.parent.exists() else ".").free
    except OSError as exc:
        log.warning("upkeep: could not read the free space: %s", exc)
        return None
    megabytes = free // (1024 * 1024)
    return f"{megabytes} MB free" if megabytes < FREE_MB_WANTED else None
