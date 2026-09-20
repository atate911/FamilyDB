"""Stage: the calendar's free blocks and the forecast for the window."""

from __future__ import annotations

from datetime import date, timedelta

from familydb.clock import season_for
from familydb.errors import ToolError
from familydb.suggest.types import Context, DayContext
from familydb.tools import ToolContext
from familydb.tools.gcal import calendar_days
from familydb.tools.weather import forecast_days

ALL_BLOCKS = ["morning", "afternoon", "evening"]


def build_context(ctx: ToolContext, window: tuple[date, date] | None) -> Context:
    """Free blocks and forecast per day. A missing service becomes a skipped check, not an error."""
    today = ctx.clock.today()
    southern = ctx.settings.southern_hemisphere
    skipped: list[str] = []
    if window is None:
        return Context(None, [], season_for(today, southern=southern), today, skipped)
    start, end = window
    tz = ctx.clock.tz

    free_by_day: dict[str, list[str]] = {}
    free_known = True
    if ctx.calendar is None:
        skipped.append("calendar not connected")
        free_known = False
    else:
        try:
            for day in calendar_days(ctx.calendar, start, end, tz):
                free_by_day[day["date"]] = list(day["free"])
        except ToolError as exc:
            skipped.append(f"calendar check failed: {exc}")
            free_known = False

    forecasts = {}
    if ctx.weather is None:
        skipped.append("weather not configured")
    else:
        try:
            for forecast in forecast_days(ctx.weather, start, end, today):
                forecasts[forecast.date] = forecast
        except ToolError as exc:
            skipped.append(f"forecast failed: {exc}")
        if not forecasts:
            skipped.append("no forecast for those dates")

    days: list[DayContext] = []
    day = start
    while day <= end:
        days.append(
            DayContext(
                date=day,
                free=free_by_day.get(day.isoformat(), list(ALL_BLOCKS)),
                free_known=free_known,
                forecast=forecasts.get(day),
            )
        )
        day += timedelta(days=1)
    return Context((start, end), days, season_for(start, southern=southern), today, skipped)
