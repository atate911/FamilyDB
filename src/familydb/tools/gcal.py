"""Google Calendar tools. Declared now so the model knows them; wired up in a later milestone."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb.config import Settings
from familydb.errors import ToolUnavailable
from familydb.tools.registry import ToolContext, tool

NOT_BUILT = "the Google Calendar integration is not built yet"
NOT_CONFIGURED = "Google Calendar is not connected (no calendar id or token configured)"


def calendar_available(settings: Settings) -> bool:
    return bool(settings.google_calendar_id) and Path(settings.google_token_path).exists()


class GetCalendarInput(BaseModel):
    start: str = Field(description="First day, YYYY-MM-DD.")
    end: str = Field(description="Last day, YYYY-MM-DD (inclusive).")


class CreateEventInput(BaseModel):
    title: str
    start: str = Field(description="YYYY-MM-DDTHH:MM in the family timezone, or YYYY-MM-DD.")
    end: str | None = Field(default=None, description="Same format. Default: start plus 2 hours.")
    all_day: bool = Field(default=False, description="True when no time is known.")
    location: str | None = None
    notes: str | None = None
    idea_id: int | None = Field(default=None, description="The idea this plan is for, if any.")


class UpdateEventInput(BaseModel):
    plan_id: int = Field(description="The plan number returned by create_event.")
    title: str | None = None
    start: str | None = None
    end: str | None = None
    all_day: bool | None = None
    location: str | None = None
    notes: str | None = None
    status: Literal["confirmed", "tentative", "cancelled"] | None = None


class DeleteEventInput(BaseModel):
    plan_id: int = Field(description="The plan number returned by create_event.")


@tool(
    name="get_calendar",
    description=(
        "Events on the shared family calendar between two dates, including ones people added by "
        "hand, plus the free blocks (morning, afternoon, evening) per day."
    ),
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
)
def get_calendar(_ctx: ToolContext, _args: GetCalendarInput) -> dict[str, Any]:
    raise ToolUnavailable(NOT_BUILT)


@tool(
    name="create_event",
    description=(
        "Put a confirmed plan on the shared family calendar and link it to an idea. Resolve the "
        "date yourself and echo it back to the family afterwards."
    ),
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
    writes=True,
)
def create_event(_ctx: ToolContext, _args: CreateEventInput) -> dict[str, Any]:
    raise ToolUnavailable(NOT_BUILT)


@tool(
    name="update_event",
    description="Change a plan on the calendar: new time, title, place, or cancel it.",
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
    writes=True,
)
def update_event(_ctx: ToolContext, _args: UpdateEventInput) -> dict[str, Any]:
    raise ToolUnavailable(NOT_BUILT)


@tool(
    name="delete_event",
    description="Remove a plan from the calendar entirely. Prefer cancelling via update_event.",
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
    writes=True,
)
def delete_event(_ctx: ToolContext, _args: DeleteEventInput) -> dict[str, Any]:
    raise ToolUnavailable(NOT_BUILT)
