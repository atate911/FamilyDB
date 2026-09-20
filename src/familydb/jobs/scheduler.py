"""The in-process scheduler for background jobs."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from familydb.app import App
from familydb.jobs.retry_failed import run_retries

log = logging.getLogger(__name__)


def build_scheduler(app: App) -> BackgroundScheduler:
    """A scheduler with every job registered, not yet started."""
    scheduler = BackgroundScheduler(timezone=app.settings.tzinfo)
    scheduler.add_job(
        run_retries,
        IntervalTrigger(minutes=app.settings.retry_interval_minutes),
        args=[app],
        id="retry_failed",
        name="retry failed messages",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
