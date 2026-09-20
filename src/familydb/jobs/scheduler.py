"""The in-process scheduler for background jobs."""

from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from familydb.app import App
from familydb.availability import digest_configured, enrichment_available
from familydb.jobs.catch_up import run_catch_up
from familydb.jobs.enrich import run_enrichment
from familydb.jobs.follow_ups import run_follow_ups
from familydb.jobs.retry_failed import run_retries
from familydb.jobs.weekend_digest import run_digest

log = logging.getLogger(__name__)

# The Telegram sender registers once polling starts, a moment after the scheduler; wait for it.
CATCH_UP_DELAY_SECONDS = 60


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
            misfire_grace_time=3600,
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
    # The cron jobs above live in memory: a bot that was off at their hour would skip them until
    # the next day or week, so run them once shortly after start (both are idempotent).
    scheduler.add_job(
        run_catch_up,
        DateTrigger(run_date=app.clock.now() + timedelta(seconds=CATCH_UP_DELAY_SECONDS)),
        args=[app],
        id="catch_up",
        name="catch up after a restart",
        misfire_grace_time=3600,
    )
    return scheduler
