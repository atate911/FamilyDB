"""Weather forecast tool over Open-Meteo."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field

from familydb.availability import weather_available
from familydb.dates import parse_date_range
from familydb.errors import ToolError, ToolUnavailable
from familydb.integrations.open_meteo import MAX_DAYS_AHEAD, DayForecast, ForecastAPI
from familydb.tools.registry import ToolContext, tool

NOT_CONFIGURED = "weather is not configured (HOME_LAT and HOME_LON are unset)"


class GetForecastInput(BaseModel):
    start: str = Field(description="First day, YYYY-MM-DD.")
    end: str = Field(description="Last day, YYYY-MM-DD (inclusive). Up to 15 days ahead.")


def forecast_days(weather: ForecastAPI, start: date, end: date, today: date) -> list[DayForecast]:
    """The forecast for the part of a window inside the horizon; empty when none of it is."""
    horizon = today + timedelta(days=MAX_DAYS_AHEAD)
    if end < today or start > horizon:
        return []
    return weather.daily(max(start, today), min(end, horizon))


@tool(
    name="get_forecast",
    description=(
        "Daily forecast at home for a date range: conditions, high, low and chance of rain. "
        "Covers today and the next 15 days."
    ),
    available=weather_available,
    unavailable_reason=NOT_CONFIGURED,
)
def get_forecast(ctx: ToolContext, args: GetForecastInput) -> dict[str, Any]:
    if ctx.weather is None:
        raise ToolUnavailable(NOT_CONFIGURED)
    start, end = parse_date_range(args.start, args.end)
    today = ctx.clock.today()
    horizon = today + timedelta(days=MAX_DAYS_AHEAD)
    if end < today or start > horizon:
        raise ToolError(f"the forecast covers {today.isoformat()} to {horizon.isoformat()}")
    days = forecast_days(ctx.weather, start, end, today)
    units = ctx.settings.weather_units
    return {
        "home": ctx.settings.home_area or None,
        "units": units,
        "days": [day.to_public(units) for day in days],
    }
