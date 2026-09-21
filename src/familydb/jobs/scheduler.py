"""The in-process scheduler for background jobs.

Each job's schedule comes from the settings, which the family can now change from the web page.
So the schedule is described once in `job_specs` and applied twice: when the scheduler is built,
and again whenever a settings change moves one. Nothing here calls the model.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.base import BaseTrigger
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
# How often to look for a settings change. One query against a small table, no model call.
SETTINGS_INTERVAL_MINUTES = 5


@dataclass(frozen=True)
class JobSpec:
    """One background job and when it should run, as the settings in force describe it."""

    id: str
    name: str
    func: Callable[..., Any]
    trigger: BaseTrigger
    wanted: bool = True
    misfire_grace_time: int | None = None


def job_specs(app: App) -> list[JobSpec]:
    """Every recurring job under the settings in force. Rebuilt whenever those change."""
    settings = app.settings
    zone = settings.tzinfo
    return [
        JobSpec(
            "retry_failed",
            "retry failed messages",
            run_retries,
            IntervalTrigger(minutes=settings.retry_interval_minutes),
        ),
        JobSpec(
            "enrich",
            "look up new ideas",
            run_enrichment,
            IntervalTrigger(minutes=settings.enrich_interval_minutes),
            wanted=enrichment_available(settings),
        ),
        JobSpec(
            "weekend_digest",
            "weekend digest",
            run_digest,
            CronTrigger(day_of_week=settings.digest_day, hour=settings.digest_hour, timezone=zone),
            wanted=digest_configured(settings),
            misfire_grace_time=3600,
        ),
        JobSpec(
            "follow_ups",
            "ask how plans went",
            run_follow_ups,
            CronTrigger(hour=settings.follow_up_hour, timezone=zone),
            misfire_grace_time=3600,
        ),
    ]


def same_schedule(current: BaseTrigger, wanted: BaseTrigger) -> bool:
    """Whether a live job already runs on this schedule.

    By shape, not identity: two triggers built from the same settings are different objects. An
    interval trigger also carries the moment it was built, which is not part of the schedule, so
    only the interval itself is compared.
    """
    if type(current) is not type(wanted):
        return False
    if isinstance(wanted, IntervalTrigger):
        return current.interval == wanted.interval  # type: ignore[attr-defined]
    return str(current) == str(wanted)


def _add(scheduler: BaseScheduler, app: App, spec: JobSpec) -> None:
    scheduler.add_job(
        spec.func,
        spec.trigger,
        args=[app],
        id=spec.id,
        name=spec.name,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=spec.misfire_grace_time,
        replace_existing=True,
    )


def sync_jobs(app: App, scheduler: BaseScheduler) -> list[str]:
    """Bring the running jobs in line with the settings. Returns what moved, for the log."""
    moved: list[str] = []
    for spec in job_specs(app):
        existing = scheduler.get_job(spec.id)
        if not spec.wanted:
            if existing is not None:
                scheduler.remove_job(spec.id)
                moved.append(f"{spec.id} off")
            continue
        if existing is None:
            _add(scheduler, app, spec)
            moved.append(f"{spec.id} on")
        elif not same_schedule(existing.trigger, spec.trigger):
            scheduler.reschedule_job(spec.id, trigger=spec.trigger)
            moved.append(spec.id)
    return moved


def apply_settings(app: App, scheduler: BaseScheduler) -> list[str]:
    """Notice a change made on the settings page and move the jobs it affects."""
    if not app.refresh():
        return []
    moved = sync_jobs(app, scheduler)
    if moved:
        log.info("settings changed; %s", ", ".join(moved))
    return moved


def build_scheduler(app: App) -> BackgroundScheduler:
    """A scheduler with every job registered, not yet started."""
    scheduler = BackgroundScheduler(timezone=app.settings.tzinfo)
    for spec in job_specs(app):
        if spec.wanted:
            _add(scheduler, app, spec)
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
    scheduler.add_job(
        apply_settings,
        IntervalTrigger(minutes=SETTINGS_INTERVAL_MINUTES),
        args=[app, scheduler],
        id="settings_watch",
        name="pick up settings changed on the page",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
