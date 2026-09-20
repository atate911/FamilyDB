"""Place tools: looked-up facts about where an idea happens. Enrichment is a later milestone."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb.errors import ToolUnavailable
from familydb.tools.registry import ToolContext, never, tool

NOT_BUILT = "place lookups are not built yet"
Day = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class OpeningHours(BaseModel):
    day: Day
    open: str = Field(description="HH:MM, 24-hour.")
    close: str = Field(description="HH:MM, 24-hour.")


class LookupPlaceInput(BaseModel):
    idea_id: int | None = Field(default=None, description="The idea whose place to look up.")
    name: str | None = Field(default=None, description="Or a place name, with an area.")
    area: str | None = None


class CheckOpenInput(BaseModel):
    idea_id: int = Field(description="The idea number.")
    date: str = Field(description="YYYY-MM-DD.")


class SavePlaceInput(BaseModel):
    idea_id: int
    name: str
    summary: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    website: str | None = None
    booking_url: str | None = None
    phone: str | None = None
    hours: list[OpeningHours] = Field(default_factory=list)
    price_note: str | None = None
    source_urls: list[str] = Field(default_factory=list)


@tool(
    name="lookup_place",
    description=(
        "Cached facts about an idea's place: address, hours, booking link, travel time from home."
    ),
    available=never,
    unavailable_reason=NOT_BUILT,
)
def lookup_place(_ctx: ToolContext, _args: LookupPlaceInput) -> dict[str, Any]:
    raise ToolUnavailable(NOT_BUILT)


@tool(
    name="check_open",
    description="Whether an idea's place is open on a given date, and its hours that day.",
    available=never,
    unavailable_reason=NOT_BUILT,
)
def check_open(_ctx: ToolContext, _args: CheckOpenInput) -> dict[str, Any]:
    raise ToolUnavailable(NOT_BUILT)


@tool(
    name="save_place",
    description="Store looked-up place details for an idea. Used by the enrichment job.",
    available=never,
    unavailable_reason=NOT_BUILT,
    writes=True,
)
def save_place(_ctx: ToolContext, _args: SavePlaceInput) -> dict[str, Any]:
    raise ToolUnavailable(NOT_BUILT)
