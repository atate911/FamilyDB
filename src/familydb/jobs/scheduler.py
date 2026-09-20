"""The in-process scheduler for background jobs."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from familydb.app import App
from familydb.availability import digest_configured, enrichment_available
from familydb.jobs.enrich import run_enrichment
from familydb.jobs.follow_ups import run_follow_ups
from familydb.jobs.retry_failed import run_retries
from familydb.jobs.weekend_digest import run_digest

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
    if digest_configured(app.settings):
        scheduler.add_job(
            run_digest,
            CronTrigger(day_of_week=app.settings.digest_day, hour=app.settings.digest_hour),
            args=[app],
            id="weekend_digest",
            name="weekend digest",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,  # a restart within the hour still sends it
        )
    scheduler.add_job(
        run_follow_ups,
        CronTrigger(hour=app.settings.follow_up_hour),
        args=[app],
        id="follow_ups",
        name="ask how plans went",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    return scheduler
