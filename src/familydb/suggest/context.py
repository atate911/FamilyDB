"""Stage: the calendar's free time and the forecast for the window.

Free time is the stretches of each day between its bounds with the busy events taken out, in
minutes, so "the next four hours" and "Saturday from 2" are answered as asked, and a question on
Saturday afternoon does not count the morning that has gone.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from familydb.clock import season_for
from familydb.errors import ToolError
from familydb.suggest.types import Context, DayBounds, DayContext
from familydb.tools import ToolContext
from familydb.tools.gcal import events_by_day, free_spans
from familydb.tools.weather import forecast_days

log = logging.getLogger(__name__)


def build_context(
    ctx: ToolContext, window: tuple[date, date] | None, bounds: DayBounds | None = None
) -> Context:
    """Free time and forecast per day. A missing service becomes a skipped check, not an error."""
    today = ctx.clock.today()
    southern = ctx.settings.southern_hemisphere
    skipped: list[str] = []
    if window is None:
        return Context(None, [], season_for(today, southern=southern), today, skipped)
    start, end = window
    tz = ctx.clock.tz
    bounds = bounds or DayBounds()
    limits = {
        start + timedelta(days=n): bounds.for_day(start + timedelta(days=n), start, end)
        for n in range((end - start).days + 1)
    }

    free_by_day: dict[str, list[tuple[int, int]]] = {}
    commitments: dict[str, list[str]] = {}
    free_known = True
    if ctx.calendar is None:
        skipped.append("calendar not connected")
        free_known = False
    else:
        try:
            for day, todays in events_by_day(ctx.calendar, start, end, tz):
                free_by_day[day.isoformat()] = free_spans(todays, day, tz, *limits[day])
                commitments[day.isoformat()] = [e.title for e in todays if e.all_day] + [
                    e.title for e in todays if not e.all_day
                ]
        except Exception as exc:  # a transport error must not fail the whole suggestion
            if not isinstance(exc, ToolError):
                log.exception("calendar check failed")
            skipped.append(f"calendar check failed: {exc}")
            free_known = False

    forecasts = {}
    if ctx.weather is None:
        skipped.append("weather not configured")
    else:
        try:
            for forecast in forecast_days(ctx.weather, start, end, today):
                forecasts[forecast.date] = forecast
        except Exception as exc:
            if not isinstance(exc, ToolError):
                log.exception("forecast failed")
            skipped.append(f"forecast failed: {exc}")
        if not forecasts:
            skipped.append("no forecast for those dates")

    days: list[DayContext] = []
    day = start
    while day <= end:
        days.append(
            DayContext(
                date=day,
                spans=free_by_day.get(day.isoformat(), _unknown(limits[day])),
                free_known=free_known,
                forecast=forecasts.get(day),
                commitments=commitments.get(day.isoformat(), []),
                bounds=limits[day],
            )
        )
        day += timedelta(days=1)
    return Context((start, end), days, season_for(start, southern=southern), today, skipped)


def _unknown(limits: tuple[int, int]) -> list[tuple[int, int]]:
    """With no calendar to ask, the whole of the time asked about is taken to be free."""
    return [limits] if limits[1] > limits[0] else []
