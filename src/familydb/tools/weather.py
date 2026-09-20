"""Weather forecast tool. Declared now; the Open-Meteo integration lands in a later milestone."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from familydb.availability import weather_available
from familydb.errors import ToolUnavailable
from familydb.tools.registry import ToolContext, tool


class GetForecastInput(BaseModel):
    start: str = Field(description="First day, YYYY-MM-DD.")
    end: str = Field(description="Last day, YYYY-MM-DD (inclusive). Up to 16 days ahead.")


@tool(
    name="get_forecast",
    description=(
        "Daily forecast at home for a date range: conditions, high, low and chance of rain."
    ),
    available=weather_available,
    unavailable_reason="weather is not configured (HOME_LAT and HOME_LON are unset)",
)
def get_forecast(_ctx: ToolContext, _args: GetForecastInput) -> dict[str, Any]:
    raise ToolUnavailable("the weather integration is not built yet")
