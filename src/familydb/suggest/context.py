"""Stage: the calendar's free time (each day's bounds minus busy events, in minutes) and the
forecast for the window."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from familydb.availability import calendar_available
from familydb.base.clock import season_for
from familydb.base.errors import ToolError
from familydb.free_time import events_by_day, free_spans
from familydb.integrations.open_meteo import DayForecast
from familydb.saved_plans import SavedPlans
from familydb.suggest.types import Context, DayBounds, DayContext
from familydb.tools import ToolContext
from familydb.tools.weather import forecast_days

log = logging.getLogger(__name__)


def build_context(
    ctx: ToolContext, window: tuple[date, date] | None, bounds: DayBounds | None = None
) -> Context:
    """Free time and forecast per day; a missing service is a skipped check, not an error."""
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
    calendar = ctx.calendar
    if calendar is None and not ctx.ignore_busy and not calendar_available(ctx.settings):
        # No Google calendar: the plans kept here are what takes time up (saved_plans.py).
        calendar = SavedPlans(ctx.conn, tz)
        skipped.append("no Google calendar connected: only the plans saved here count as busy")
    if calendar is None:
        skipped.append("calendar not connected")
        free_known = False
    else:
        try:
            for day, todays in events_by_day(calendar, start, end, tz):
                free_by_day[day.isoformat()] = free_spans(todays, day, tz, *limits[day])
                commitments[day.isoformat()] = [e.title for e in todays if e.all_day] + [
                    e.title for e in todays if not e.all_day
                ]
        except Exception as exc:  # must not fail the whole suggestion
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
                forecast=_part(forecasts.get(day), limits[day]),
                commitments=commitments.get(day.isoformat(), []),
                bounds=limits[day],
            )
        )
        day += timedelta(days=1)
    return Context((start, end), days, season_for(start, southern=southern), today, skipped)


def _part(forecast: DayForecast | None, limits: tuple[int, int]) -> DayForecast | None:
    """The day's weather for the hours asked about, when the forecast has them: rain at six in
    the morning says nothing about this afternoon."""
    return forecast.between(*limits) if forecast is not None else None


def _unknown(limits: tuple[int, int]) -> list[tuple[int, int]]:
    """With no calendar, all of the time asked about counts as free."""
    return [limits] if limits[1] > limits[0] else []
