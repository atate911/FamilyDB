"""The evening before a plan: look at its weather and its place's hours again. No model call.

A plan was made against the forecast and the opening hours of the day it was made. The evening
before, this job checks again, in code: an outdoor idea, or one that needs it dry, against
tomorrow's forecast, and the place's hours as last looked up against the plan's time. When all
is well it says nothing. When something is off it says so in the chat the plan was made in, in
her words, with a backup when the suggestion engine finds one for the same time: indoors when it
is the rain, anything open when it is the hours. Each plan is checked once (`plans.checked_at`),
whether or not anything was said.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import date, timedelta

from familydb import voice
from familydb.app import App
from familydb.calendar_sync import sync_plans
from familydb.dates import utc_iso
from familydb.integrations.open_meteo import DayForecast
from familydb.store import ideas, messages, places, plans
from familydb.store.db import transaction
from familydb.store.ideas import Idea
from familydb.store.plans import Plan
from familydb.suggest.engine import run as suggest
from familydb.suggest.evaluate import doable
from familydb.suggest.shortlist import day_is_dry
from familydb.suggest.types import DAY_END, DAY_START, SuggestInput, clock
from familydb.tools.places import format_ranges, open_on
from familydb.tools.registry import ToolContext
from familydb.tools.weather import forecast_days

log = logging.getLogger(__name__)

# A timed plan with no end is taken to last this long.
ASSUMED_MINUTES = 120


def run_plan_checks(app: App) -> int:
    """Check each plan that starts tomorrow and was not checked yet. Returns how many heads-ups."""
    app.refresh()
    if not app.settings.plan_checks:
        return 0
    tomorrow = app.clock.today() + timedelta(days=1)
    with closing(app.connect()) as conn:
        if not plans.due_for_check(conn, day=tomorrow.isoformat()):
            return 0
        # A heads-up about a plan somebody cancelled in Google would be noise. When Google cannot
        # be asked, the checks wait for a run that can, as the follow-ups do.
        if app.calendar is not None:
            try:
                now = utc_iso(app.clock.now())
                sync_plans(conn, app.calendar, app.settings.google_calendar_id, now)
            except Exception:
                log.exception("plan checks deferred: the calendar could not be checked")
                return 0
        forecast = _forecast(app, tomorrow)
        said = 0
        for plan in plans.due_for_check(conn, day=tomorrow.isoformat()):
            if app.senders.get(plan.channel or "") is None or plan.chat_id is None:
                log.info("plan %s is checked later: nothing here can send to it", plan.id)
                continue
            idea = ideas.get(conn, plan.idea_id) if plan.idea_id else None
            heads_up = _heads_up(app, conn, plan, idea, forecast) if idea else None
            now = utc_iso(app.clock.now())
            with transaction(conn):
                # Asked again under the write lock: a run by hand can race the scheduler.
                current = plans.get(conn, plan.id)
                if current is None or current.checked_at is not None:
                    continue
                plans.mark_checked(conn, plan.id, now=now)
                if heads_up is None:
                    continue
                event, text = heads_up
                out = messages.insert_out(
                    conn, channel=plan.channel or "", chat_id=plan.chat_id, text=text, now=now
                )
            # Stored first, sent second: one that cannot go now is the retry job's.
            voice.hand_over(
                app,
                conn,
                out.id,
                event=event,
                channel=plan.channel or "",
                chat_id=plan.chat_id,
                mention=plan.title,
            )
            said += 1
    return said


def _forecast(app: App, day: date) -> DayForecast | None:
    """Tomorrow's forecast at home; None without one, and then the weather is not checked."""
    if app.weather is None:
        return None
    try:
        found = forecast_days(app.weather, day, day, app.clock.today())
    except Exception:
        log.warning("plan checks go without the weather: the forecast failed", exc_info=True)
        return None
    return found[0] if found else None


def _heads_up(
    app: App, conn: sqlite3.Connection, plan: Plan, idea: Idea, forecast: DayForecast | None
) -> tuple[str, str] | None:
    """What to say about this plan, as (event, words), or None when all is well."""
    settings = app.settings
    day = date.fromisoformat(plan.start[:10])
    span = _span(plan)
    label = f"#{idea.id} {plan.title}"
    needs_dry = idea.setting == "outdoor" or idea.weather == "dry"
    if needs_dry and forecast is not None and day_is_dry(forecast) is False:
        chance = forecast.rain_chance
        weather = f"{chance}% chance of rain" if chance else forecast.summary.lower()
        said = voice.say(settings, "plan_rain", seed=plan.id, plan=label, weather=weather)
        return "plan_rain", _with_backup(app, conn, plan, said, span, setting="indoor")
    place = places.get(conn, idea.place_id) if idea.place_id else None
    state, ranges = open_on(place, day)
    if place is None or state == "unknown":
        return None
    if state == "open" and (plan.all_day or doable(ranges, [span])):
        return None
    hours = (
        f"listed as closed on {day:%A}s"
        if state == "closed"
        else f"listed as open {format_ranges(ranges)} on {day:%A}s"
    )
    said = voice.say(
        settings, "plan_closed", seed=plan.id, plan=label, place=place.name, hours=hours
    )
    return "plan_closed", _with_backup(app, conn, plan, said, span, setting=None)


def _span(plan: Plan) -> tuple[int, int]:
    """The plan's time on its first day, in minutes after midnight."""
    if plan.all_day or len(plan.start) < 16:
        return DAY_START, DAY_END
    start = int(plan.start[11:13]) * 60 + int(plan.start[14:16])
    if plan.end and plan.end[:10] == plan.start[:10] and len(plan.end) >= 16:
        end = int(plan.end[11:13]) * 60 + int(plan.end[14:16])
    elif plan.end:
        end = 24 * 60  # it goes on past midnight
    else:
        end = start + ASSUMED_MINUTES
    return start, max(start + 1, min(end, 24 * 60 - 1))


def _with_backup(
    app: App,
    conn: sqlite3.Connection,
    plan: Plan,
    said: str,
    span: tuple[int, int],
    *,
    setting: str | None,
) -> str:
    backup = _backup(app, conn, plan, span, setting)
    return f"{said}\n{backup}" if backup else said


def _backup(
    app: App,
    conn: sqlite3.Connection,
    plan: Plan,
    span: tuple[int, int],
    setting: str | None,
) -> str | None:
    """Another idea for the same time, from the engine, or None when none fits well.

    The calendar is left out: it holds the plan itself, which would leave no time free."""
    ctx = ToolContext(
        conn=conn,
        settings=app.settings,
        clock=app.clock,
        member=None,
        calendar=None,
        weather=app.weather,
        geocoder=app.geocoder,
    )
    asked = SuggestInput(
        window="dates",
        start=plan.start[:10],
        end=plan.start[:10],
        from_time=clock(span[0]),
        until_time=clock(span[1]),
        setting=setting,  # type: ignore[arg-type]
        discover=False,
        question=f"a backup for plan #{plan.id}",
    )
    try:
        result = suggest(ctx, asked, refresh_stale=False)
    except Exception:
        log.warning("no backup for plan %s: the engine failed", plan.id, exc_info=True)
        return None
    pick = next(
        (c for c in result.candidates if c.verdict == "good" and c.idea_id != plan.idea_id), None
    )
    if pick is None:
        return None
    why = ", ".join(pick.reasons[:2])
    return voice.say(
        app.settings, "plan_backup", seed=plan.id, idea=pick.idea_id, title=pick.title, why=why
    )
