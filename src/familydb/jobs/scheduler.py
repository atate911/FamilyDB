"""The in-process scheduler. Schedules come from the settings, so `job_specs` describes them
once and they are applied at build and whenever a setting moves one. No model call here."""

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

from familydb import health
from familydb.alerts import run_alerts
from familydb.app import App
from familydb.availability import digest_configured, enrichment_available
from familydb.jobs.catch_up import run_catch_up
from familydb.jobs.enrich import run_enrichment
from familydb.jobs.follow_ups import run_follow_ups
from familydb.jobs.morning import any_on as morning_on
from familydb.jobs.morning import run_morning
from familydb.jobs.nudges import run_nudges
from familydb.jobs.plan_checks import run_plan_checks
from familydb.jobs.reminders import run_reminders
from familydb.jobs.retry_failed import run_retries
from familydb.jobs.tidy import run_tidy
from familydb.jobs.weekend_digest import run_digest
from familydb.judgement import run_judgements
from familydb.model_watch import run_model_watch
from familydb.upkeep import run_upkeep
from familydb.whereabouts import forget_old

log = logging.getLogger(__name__)

# The Telegram sender registers a moment after the scheduler; wait for it.
CATCH_UP_DELAY_SECONDS = 60
FORGET_INTERVAL_MINUTES = 10
SETTINGS_INTERVAL_MINUTES = 5
NUDGE_INTERVAL_MINUTES = 15


@dataclass(frozen=True)
class JobSpec:
    """One background job and when it should run."""

    id: str
    name: str
    func: Callable[..., Any]
    trigger: BaseTrigger
    wanted: bool = True
    misfire_grace_time: int | None = None


def job_specs(app: App) -> list[JobSpec]:
    """Every recurring job under the settings in force."""
    settings = app.settings
    zone = settings.tzinfo
    return [
        JobSpec("reminders", "deliver task reminders", run_reminders, IntervalTrigger(minutes=1)),
        JobSpec(
            "alerts",
            "tell admins what needs fixing",
            run_alerts,
            IntervalTrigger(minutes=1),
            wanted=settings.admin_alerts,
        ),
        JobSpec(
            "forget_locations",
            "delete shared locations after a day",
            forget_old,
            IntervalTrigger(minutes=FORGET_INTERVAL_MINUTES),
        ),
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
            wanted=settings.follow_ups,
            misfire_grace_time=3600,
        ),
        JobSpec(
            "plan_checks",
            "check tomorrow's plans",
            run_plan_checks,
            # From the hour until ten, so a plan made late for tomorrow is checked too; each run
            # looks only at plans not checked yet, so a quiet evening costs one query an hour.
            CronTrigger(hour=_until_ten(settings.plan_check_hour), timezone=zone),
            wanted=settings.plan_checks,
            misfire_grace_time=3600,
        ),
        JobSpec(
            "morning",
            "the morning message",
            run_morning,
            CronTrigger(hour=settings.morning_hour, timezone=zone),
            wanted=morning_on(settings),
            misfire_grace_time=3600,
        ),
        JobSpec(
            "model_watch",
            "check models and prices",
            run_model_watch,
            CronTrigger(hour=5, minute=17, timezone=zone),
            wanted=settings.model_watch,
            misfire_grace_time=6 * 3600,
        ),
        JobSpec(
            "judgements",
            "weigh changes in the models",
            run_judgements,
            IntervalTrigger(minutes=15),
            wanted=settings.judgements,
        ),
        JobSpec(
            "nudges",
            "bring up tasks kept for a part of the week",
            run_nudges,
            IntervalTrigger(minutes=NUDGE_INTERVAL_MINUTES),
            wanted=settings.task_nudges,
        ),
        JobSpec(
            "upkeep",
            "check the backups and the disk",
            run_upkeep,
            IntervalTrigger(hours=1),
        ),
        JobSpec(
            "tidy",
            "take off ideas whose dates are past, and forget old messages' words",
            run_tidy,
            CronTrigger(hour=3, minute=30, timezone=zone),
            wanted=settings.tidy_ideas or bool(settings.keep_messages_days),
            misfire_grace_time=6 * 3600,
        ),
    ]


def _until_ten(hour: int) -> str:
    """Every hour from `hour` to 22:00, as a cron field; just `hour` from ten at night on."""
    return str(hour) if hour >= 22 else f"{hour}-22"


def same_schedule(current: BaseTrigger, wanted: BaseTrigger) -> bool:
    """Whether a live job already runs on this schedule, compared by shape: two triggers from the
    same settings are different objects, and an interval trigger carries its build time."""
    if type(current) is not type(wanted):
        return False
    # A cron trigger's text omits its timezone, so a changed timezone would keep the old clock.
    if str(getattr(current, "timezone", "")) != str(getattr(wanted, "timezone", "")):
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
    """Bring the running jobs in line with the settings; returns what moved."""
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
    """Move the jobs a settings change affects. Triggers are compared on every tick, not gated on
    `refresh()`, which a page view will often already have consumed."""
    app.refresh()
    moved = sync_jobs(app, scheduler)
    if moved:
        log.info("settings changed; %s", ", ".join(moved))
    health.ticked(app)  # the jobs are running (familydb/health.py)
    return moved


def build_scheduler(app: App) -> BackgroundScheduler:
    """A scheduler with every job registered, not yet started."""
    scheduler = BackgroundScheduler(timezone=app.settings.tzinfo)
    for spec in job_specs(app):
        if spec.wanted:
            _add(scheduler, app, spec)
    # Cron jobs live in memory, so one missed while the bot was off is run once after start.
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
