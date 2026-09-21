"""Catch up on start: the cron jobs live in memory, so a restart after the hour would skip them.

Both jobs are idempotent (one digest per day, one question per plan), so running them once
shortly after start costs nothing when they already ran.
"""

from __future__ import annotations

import logging
from typing import Any

from familydb.agent.loop import MessagesAPI
from familydb.app import App
from familydb.availability import digest_configured
from familydb.jobs.follow_ups import run_follow_ups
from familydb.jobs.weekend_digest import run_digest

log = logging.getLogger(__name__)

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def digest_due(app: App) -> bool:
    """Whether today is the digest day and its hour has passed."""
    now = app.clock.now()
    settings = app.settings
    return (
        digest_configured(settings)
        and WEEKDAYS[now.weekday()] == settings.digest_day
        and now.hour >= settings.digest_hour
    )


def run_catch_up(app: App, *, api: MessagesAPI | None = None) -> dict[str, Any]:
    """Run the follow-ups, and the digest when it was due earlier today."""
    app.refresh()
    result: dict[str, Any] = {"follow_ups": run_follow_ups(app), "digest": "not due"}
    if digest_due(app):
        reply = run_digest(app, api=api)
        result["digest"] = "skipped" if reply is None else reply.status
    log.info("catch-up on start: %s", result)
    return result
