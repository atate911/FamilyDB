"""The in-process scheduler for background jobs."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from familydb.app import App
from familydb.availability import enrichment_available
from familydb.jobs.enrich import run_enrichment
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
    if enrichment_available(app.settings):
        scheduler.add_job(
            run_enrichment,
            IntervalTrigger(minutes=app.settings.enrich_interval_minutes),
            args=[app],
            id="enrich",
            name="look up new ideas",
            max_instances=1,
            coalesce=True,
        )
    return scheduler
