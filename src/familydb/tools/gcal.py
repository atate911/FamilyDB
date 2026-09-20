"""Google Calendar tools: what is on the family calendar, and putting plans on it."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from familydb.availability import calendar_available
from familydb.dates import (
    ensure_not_past,
    iso_date,
    iso_datetime,
    parse_date,
    parse_date_range,
    parse_datetime,
)
from familydb.errors import ToolError, ToolUnavailable
from familydb.integrations.google_calendar import CalendarAPI, CalendarEvent
from familydb.store import ideas, messages, plans
from familydb.store.db import transaction
from familydb.tools.registry import ToolContext, tool

NOT_CONFIGURED = "Google Calendar is not connected (no calendar id or token configured)"
MAX_WINDOW_DAYS = 60
DEFAULT_DURATION = timedelta(hours=2)
BLOCKS: tuple[tuple[str, time, time], ...] = (
    ("morning", time(8, 0), time(12, 0)),
    ("afternoon", time(12, 0), time(17, 0)),
    ("evening", time(17, 0), time(22, 0)),
)
# plan field -> Google event field, for the simple text attributes
TEXT_FIELDS = {"title": "title", "location": "location", "notes": "description"}


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
    start: str | None = Field(
        default=None, description="New start. With no new end, the plan keeps its duration."
    )
    end: str | None = None
    all_day: bool | None = Field(
        default=None, description="False needs a start time; true drops the time."
    )
    location: str | None = None
    notes: str | None = None
    status: Literal["confirmed", "tentative", "cancelled"] | None = None


class DeleteEventInput(BaseModel):
    plan_id: int = Field(description="The plan number returned by create_event.")


def _calendar(ctx: ToolContext) -> CalendarAPI:
    if ctx.calendar is None:
        raise ToolUnavailable(NOT_CONFIGURED)
    return ctx.calendar


def _day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start, start + timedelta(days=1)


def on_day(event: CalendarEvent, day: date, tz: ZoneInfo) -> bool:
    if event.all_day:
        first = event.start if isinstance(event.start, date) else event.start.date()
        last_exclusive = event.end if isinstance(event.end, date) else event.end.date()
        if last_exclusive <= first:
            last_exclusive = first + timedelta(days=1)
        return first <= day < last_exclusive
    day_start, day_end = _day_bounds(day, tz)
    return event.start < day_end and event.end > day_start  # type: ignore[operator]


def free_blocks(events: list[CalendarEvent], day: date, tz: ZoneInfo) -> list[str]:
    """Which of morning, afternoon and evening have no timed event. All-day events don't block."""
    free: list[str] = []
    for name, start_t, end_t in BLOCKS:
        block_start = datetime.combine(day, start_t, tzinfo=tz)
        block_end = datetime.combine(day, end_t, tzinfo=tz)
        busy = any(
            not event.all_day and event.start < block_end and event.end > block_start  # type: ignore[operator]
            for event in events
        )
        if not busy:
            free.append(name)
    return free


def _timed_or_all_day(
    start_text: str,
    end_text: str | None,
    all_day: bool,
    tz: ZoneInfo,
    *,
    strict: bool = False,
) -> tuple[datetime | date, datetime | date, bool, str, str | None]:
    """Resolve the user-facing start/end into calendar values and stored strings.

    A date-only start makes the plan all-day unless `strict` says a time was required.
    """
    date_only = len(start_text.strip()) == 10
    if date_only and strict and not all_day:
        raise ToolError("give a start time (YYYY-MM-DDTHH:MM) to make this a timed plan")
    if all_day or date_only:
        start_d = parse_date(start_text.strip()[:10])
        end_d = parse_date(end_text.strip()[:10]) if end_text else start_d
        if end_d < start_d:
            raise ToolError("end is before start")
        # Google's all-day end is exclusive.
        return start_d, end_d + timedelta(days=1), True, iso_date(start_d), iso_date(end_d)
    start_dt = parse_datetime(start_text, tz)
    end_dt = parse_datetime(end_text, tz) if end_text else start_dt + DEFAULT_DURATION
    if end_dt <= start_dt:
        raise ToolError("end must be after start")
    return start_dt, end_dt, False, iso_datetime(start_dt), iso_datetime(end_dt)


def _end_keeping_duration(
    plan: plans.Plan, new_start: str, all_day: bool, tz: ZoneInfo
) -> str | None:
    """When only the start moves, carry the plan's length over to the new start."""
    if plan.end is None or all_day != plan.all_day:
        return None
    if all_day:
        span = parse_date(plan.end) - parse_date(plan.start)
        return iso_date(parse_date(new_start[:10]) + span)
    duration = parse_datetime(plan.end, tz) - parse_datetime(plan.start, tz)
    return iso_datetime(parse_datetime(new_start, tz) + duration)


@tool(
    name="get_calendar",
    description=(
        "Events on the shared family calendar between two dates, including ones people added by "
        "hand, plus the free blocks (morning, afternoon, evening) per day."
    ),
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
)
def get_calendar(ctx: ToolContext, args: GetCalendarInput) -> dict[str, Any]:
    calendar = _calendar(ctx)
    tz = ctx.clock.tz
    start, end = parse_date_range(args.start, args.end)
    if (end - start).days > MAX_WINDOW_DAYS:
        raise ToolError(f"ask for at most {MAX_WINDOW_DAYS} days at a time")
    window_start, _ = _day_bounds(start, tz)
    _, window_end = _day_bounds(end, tz)
    events = calendar.list_events(window_start, window_end)
    days = []
    day = start
    while day <= end:
        todays = [event for event in events if on_day(event, day, tz)]
        days.append(
            {
                "date": day.isoformat(),
                "weekday": day.strftime("%A"),
                "events": [
                    {
                        "title": e.title,
                        "start": e.start.strftime("%H:%M"),  # type: ignore[union-attr]
                        "end": e.end.strftime("%H:%M"),  # type: ignore[union-attr]
                        "location": e.location,
                    }
                    for e in todays
                    if not e.all_day
                ],
                "all_day": [e.title for e in todays if e.all_day],
                "free": free_blocks(todays, day, tz),
            }
        )
        day += timedelta(days=1)
    return {"calendar": ctx.settings.google_calendar_id, "days": days}


@tool(
    name="create_event",
    description=(
        "Put a confirmed plan on the shared family calendar and link it to an idea. Resolve the "
        "date yourself and echo it back to the family afterwards. Returns the plan number."
    ),
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
    writes=True,
)
def create_event(ctx: ToolContext, args: CreateEventInput) -> dict[str, Any]:
    calendar = _calendar(ctx)
    tz = ctx.clock.tz
    if args.idea_id is not None and ideas.get(ctx.conn, args.idea_id) is None:
        raise ToolError(f"no idea #{args.idea_id}")
    start, end, all_day, stored_start, stored_end = _timed_or_all_day(
        args.start, args.end, args.all_day, tz
    )
    ensure_not_past(start, ctx.clock)
    event = calendar.insert_event(
        title=args.title.strip(),
        start=start,
        end=end,
        all_day=all_day,
        location=args.location,
        description=args.notes,
    )
    origin = messages.get(ctx.conn, ctx.message_id) if ctx.message_id is not None else None
    with transaction(ctx.conn):
        plan = plans.insert(
            ctx.conn,
            title=args.title.strip(),
            start=stored_start,
            end=stored_end,
            all_day=all_day,
            idea_id=args.idea_id,
            google_event_id=event.id,
            calendar_id=ctx.settings.google_calendar_id,
            location=args.location,
            notes=args.notes,
            created_by=ctx.member.id if ctx.member else None,
            channel=origin.channel if origin else None,
            chat_id=origin.chat_id if origin else None,
            now=ctx.now_iso(),
        )
        idea = None
        if args.idea_id is not None:
            idea = ideas.update(ctx.conn, args.idea_id, {"status": "planned"}, now=ctx.now_iso())
    return {
        "plan": plan.model_dump(mode="json"),
        "event": event.to_public(),
        "idea": idea.model_dump(mode="json") if idea else None,
    }


def _cancel(ctx: ToolContext, plan: plans.Plan) -> dict[str, Any]:
    calendar = _calendar(ctx)
    if plan.google_event_id:
        calendar.delete_event(plan.google_event_id)
    with transaction(ctx.conn):
        updated = plans.update(ctx.conn, plan.id, {"status": "cancelled"}, now=ctx.now_iso())
        idea = None
        if plan.idea_id is not None:
            current = ideas.get(ctx.conn, plan.idea_id)
            if current is not None and current.status == "planned":
                idea = ideas.update(ctx.conn, plan.idea_id, {"status": "idea"}, now=ctx.now_iso())
    return {
        "plan": updated.model_dump(mode="json") if updated else None,
        "idea": idea.model_dump(mode="json") if idea else None,
    }


@tool(
    name="update_event",
    description=(
        "Change a plan on the calendar: new time, title, place, notes, or cancel it. Moving only "
        "the start keeps the plan's length."
    ),
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
    writes=True,
)
def update_event(ctx: ToolContext, args: UpdateEventInput) -> dict[str, Any]:
    calendar = _calendar(ctx)
    plan = plans.get(ctx.conn, args.plan_id)
    if plan is None:
        raise ToolError(f"no plan #{args.plan_id}")
    if plan.status == "cancelled":
        raise ToolError(f"plan #{plan.id} is cancelled; create a new event instead")
    if args.status == "cancelled":
        return _cancel(ctx, plan)

    changes: dict[str, Any] = {}
    patch: dict[str, Any] = {}
    for field, google_field in TEXT_FIELDS.items():
        value = getattr(args, field)
        if value is not None:
            value = value.strip() if field == "title" else value
            changes[field] = value
            patch[google_field] = value
    if args.status is not None:
        changes["status"] = args.status

    if args.start is not None or args.end is not None or args.all_day is not None:
        tz = ctx.clock.tz
        all_day = plan.all_day if args.all_day is None else args.all_day
        start_text = args.start if args.start is not None else plan.start
        if args.end is not None:
            end_text: str | None = args.end
        elif args.start is not None:
            end_text = _end_keeping_duration(plan, args.start, all_day, tz)
        else:
            end_text = plan.end
        start, end, all_day, stored_start, stored_end = _timed_or_all_day(
            start_text, end_text, all_day, tz, strict=args.all_day is False
        )
        ensure_not_past(start, ctx.clock)
        changes.update({"start": stored_start, "end": stored_end, "all_day": all_day})
        patch.update({"start": start, "end": end, "all_day": all_day})

    if not changes:
        raise ToolError("nothing to change")
    event = None
    if patch and plan.google_event_id:
        event = calendar.patch_event(plan.google_event_id, **patch)
    with transaction(ctx.conn):
        updated = plans.update(ctx.conn, plan.id, changes, now=ctx.now_iso())
    return {
        "plan": updated.model_dump(mode="json") if updated else None,
        "event": event.to_public() if event else None,
    }


@tool(
    name="delete_event",
    description="Remove a plan from the calendar entirely. Prefer cancelling via update_event.",
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
    writes=True,
)
def delete_event(ctx: ToolContext, args: DeleteEventInput) -> dict[str, Any]:
    plan = plans.get(ctx.conn, args.plan_id)
    if plan is None:
        raise ToolError(f"no plan #{args.plan_id}")
    if plan.status == "cancelled":
        return {"plan": plan.model_dump(mode="json"), "note": "already cancelled"}
    return _cancel(ctx, plan)
