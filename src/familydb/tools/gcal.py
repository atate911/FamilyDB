"""Google Calendar tools: what is on the family calendar, and putting plans on it."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from familydb.availability import calendar_available
from familydb.calendar_sync import event_changes, refresh_plan, sync_plans
from familydb.dates import (
    ensure_not_past,
    iso_date,
    iso_datetime,
    parse_date,
    parse_date_range,
    parse_datetime,
)
from familydb.errors import ToolError, ToolUnavailable
from familydb.free_time import events_by_day, free_blocks
from familydb.integrations.google_calendar import CalendarAPI, CalendarEvent
from familydb.store import calendar_ops, ideas, messages, plans
from familydb.store.db import to_json, transaction
from familydb.tools.registry import ToolContext, tool

NOT_CONFIGURED = "Google Calendar is not connected (no calendar id or key configured)"
MAX_WINDOW_DAYS = 60
DEFAULT_DURATION = timedelta(hours=2)
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


PLAN_HELP = "The plan number, from create_event, search_plans or get_calendar."
EVENT_HELP = (
    "Instead of plan_id, for an event somebody put on the calendar by hand (get_calendar shows "
    "it with no plan_id): its google_event_id."
)


class UpdateEventInput(BaseModel):
    plan_id: int | None = Field(default=None, description=PLAN_HELP)
    event_id: str | None = Field(default=None, description=EVENT_HELP)
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
    plan_id: int | None = Field(default=None, description=PLAN_HELP)
    event_id: str | None = Field(default=None, description=EVENT_HELP)


class SearchPlansInput(BaseModel):
    query: str = Field(
        default="", description="Words in the plan title, or empty for recent plans."
    )
    include_cancelled: bool = False


@tool(
    name="search_plans",
    description="Find saved plans and their plan_id before moving or cancelling one. "
    "Checks current Google dates when connected; use get_calendar to see other Google events.",
)
def search_plans(ctx: ToolContext, args: SearchPlansInput) -> dict[str, Any]:
    checked = ctx.calendar is not None
    if checked:
        sync_plans(ctx.conn, ctx.calendar, ctx.settings.google_calendar_id, ctx.now_iso())
    rows = ctx.conn.execute(
        "SELECT * FROM plans WHERE lower(title) LIKE ? AND (? OR status != 'cancelled') "
        "ORDER BY start DESC LIMIT 50",
        ("%" + args.query.strip().lower() + "%", args.include_cancelled),
    )
    return {
        "calendar_checked": checked,
        "plans": [
            {"plan_id": row["id"], **plans.Plan.from_row(row).model_dump(mode="json")}
            for row in rows
        ],
    }


def _calendar(ctx: ToolContext) -> CalendarAPI:
    if ctx.calendar is None:
        raise ToolUnavailable(NOT_CONFIGURED)
    return ctx.calendar


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
    start: str, end: str | None, was_all_day: bool, new_start: str, all_day: bool, tz: ZoneInfo
) -> str | None:
    """When only the start moves, carry the plan's length over to the new start."""
    if end is None or all_day != was_all_day:
        return None
    if all_day:
        span = parse_date(end) - parse_date(start)
        return iso_date(parse_date(new_start[:10]) + span)
    duration = parse_datetime(end, tz) - parse_datetime(start, tz)
    return iso_datetime(parse_datetime(new_start, tz) + duration)


def calendar_days(
    calendar: CalendarAPI, start: date, end: date, tz: ZoneInfo
) -> list[dict[str, Any]]:
    """Per-day timed events, all-day entries and free blocks, as `get_calendar` reports them."""
    return [
        {
            "date": day.isoformat(),
            "weekday": day.strftime("%A"),
            "events": [
                {
                    "google_event_id": e.id,
                    "title": e.title,
                    "start": e.start.strftime("%H:%M"),  # type: ignore[union-attr]
                    "end": e.end.strftime("%H:%M"),  # type: ignore[union-attr]
                    "location": e.location,
                }
                for e in todays
                if not e.all_day
            ],
            "all_day": [e.title for e in todays if e.all_day],
            "all_day_events": [e.to_public() for e in todays if e.all_day],
            "free": free_blocks(todays, day, tz),
        }
        for day, todays in events_by_day(calendar, start, end, tz)
    ]


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
    start, end = parse_date_range(args.start, args.end)
    if (end - start).days > MAX_WINDOW_DAYS:
        raise ToolError(f"ask for at most {MAX_WINDOW_DAYS} days at a time")
    days = calendar_days(calendar, start, end, ctx.clock.tz)
    sync_plans(ctx.conn, calendar, ctx.settings.google_calendar_id, ctx.now_iso())
    owned = {
        event_id: plan.id
        for event_id, plan in plans.by_google_event(
            ctx.conn, ctx.settings.google_calendar_id
        ).items()
    }
    for day in days:
        for event in day["events"]:
            event["plan_id"] = owned.get(event["google_event_id"])
        for event in day["all_day_events"]:
            event["plan_id"] = owned.get(event["id"])
    return {"calendar": ctx.settings.google_calendar_id, "days": days}


def _created(ctx: ToolContext, plan: plans.Plan, event: CalendarEvent | None) -> dict[str, Any]:
    """What creating a plan answers: the plan, its event, and the idea it put on the calendar."""
    idea = ideas.get(ctx.conn, plan.idea_id) if plan.idea_id is not None else None
    return {
        "plan": plan.model_dump(mode="json"),
        "event": event.to_public() if event else None,
        "idea": idea.model_dump(mode="json") if idea else None,
    }


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
    # Persist identity before contacting Google. The same inbound request and normalized
    # event intent reuse it even after a crash or a lost successful response.
    scope = (
        str(ctx.message_id)
        if ctx.message_id is not None
        else ctx.operation_id or ctx.scratch.setdefault("calendar_scope", uuid.uuid4().hex)
    )
    intent = {
        "calendar": ctx.settings.google_calendar_id,
        "title": args.title.strip().casefold(),
        "start": stored_start,
        "end": stored_end,
        "idea_id": args.idea_id,
    }
    key = hashlib.sha256((scope + to_json(intent)).encode()).hexdigest()
    # A form drawn again after a lost reply has a new identity. The same browser session asking
    # for the same event takes over the unfinished attempt, which may already have made it.
    resume = (
        hashlib.sha256((ctx.resume_scope + to_json(intent)).encode()).hexdigest()
        if ctx.resume_scope
        else None
    )
    with transaction(ctx.conn):
        event_id = calendar_ops.get(ctx.conn, key)
        if event_id is None:
            earlier = calendar_ops.unfinished(ctx.conn, resume) if resume else None
            if earlier is not None:
                event_id = calendar_ops.reserve(ctx.conn, key, earlier)
            else:
                event_id = calendar_ops.reserve(ctx.conn, key, uuid.uuid4().hex, resume_key=resume)
    event = calendar.get_event(event_id)
    existing = plans.for_event(ctx.conn, event_id)
    if existing is not None:
        return _created(ctx, existing, event)  # this attempt finished before: say so again
    if event is None:
        ensure_not_past(start, ctx.clock)
        event = calendar.insert_event(
            title=args.title.strip(),
            start=start,
            end=end,
            all_day=all_day,
            location=args.location,
            description=args.notes,
            event_id=event_id,
        )
    origin = messages.get(ctx.conn, ctx.message_id) if ctx.message_id is not None else None
    with transaction(ctx.conn):
        plan = plans.for_event(ctx.conn, event_id)  # an attempt running beside this one finished
        if plan is None:
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
            if args.idea_id is not None:
                ideas.update(ctx.conn, args.idea_id, {"status": "planned"}, now=ctx.now_iso())
        return _created(ctx, plan, event)


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


def _target(
    ctx: ToolContext, plan_id: int | None, event_id: str | None
) -> tuple[plans.Plan | None, CalendarEvent | None]:
    """The plan, or the hand-made event, that a change is for: exactly one of the two.

    An event the bot made is always worked on as its plan, however it was named, so the plan
    and its idea stay in step. Only an event nobody made through the bot is changed directly.
    """
    if (plan_id is None) == (event_id is None):
        raise ToolError("give plan_id, or event_id for an event put on the calendar by hand")
    calendar = _calendar(ctx)
    if plan_id is None:
        assert event_id is not None
        owned = plans.for_event(ctx.conn, event_id)
        if owned is None or owned.calendar_id != ctx.settings.google_calendar_id:
            event = calendar.get_event(event_id)
            if event is None:
                raise ToolError(f"no event {event_id} on the calendar; get_calendar lists them")
            return None, event
        plan_id = owned.id
    plan = plans.get(ctx.conn, plan_id)
    if plan is None:
        raise ToolError(f"no plan #{plan_id}")
    if plan.calendar_id != ctx.settings.google_calendar_id:
        raise ToolError("this plan belongs to a different calendar")
    return plan, None


def _remove_event(ctx: ToolContext, event: CalendarEvent) -> dict[str, Any]:
    """Take an event that is not the bot's own off the calendar, and say which it was."""
    _calendar(ctx).delete_event(event.id)
    return {"plan": None, "removed": event.to_public()}


@tool(
    name="update_event",
    description=(
        "Change a plan on the calendar: new time, title, place, notes, or cancel it. Moving only "
        "the start keeps the plan's length. An event put on the calendar by hand is changed by "
        "its event_id."
    ),
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
    writes=True,
)
def update_event(ctx: ToolContext, args: UpdateEventInput) -> dict[str, Any]:
    calendar = _calendar(ctx)
    plan, event = _target(ctx, args.plan_id, args.event_id)
    if plan is not None:
        plan = refresh_plan(
            ctx.conn, calendar, plan, ctx.settings.google_calendar_id, ctx.now_iso()
        )
        if plan.status == "cancelled":
            raise ToolError(f"plan #{plan.id} is cancelled; create a new event instead")
        if args.status == "cancelled":
            return _cancel(ctx, plan)
    elif args.status == "cancelled":
        assert event is not None
        return _remove_event(ctx, event)
    # What it is now, spelled the way plans are stored, for a plan and a hand-made event alike.
    current = plan.model_dump() if plan is not None else event_changes(event)  # type: ignore[arg-type]

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
        patch["status"] = args.status

    if args.start is not None or args.end is not None or args.all_day is not None:
        tz = ctx.clock.tz
        all_day = current["all_day"] if args.all_day is None else args.all_day
        start_text = args.start if args.start is not None else current["start"]
        if args.end is not None:
            end_text: str | None = args.end
        elif args.start is not None:
            end_text = _end_keeping_duration(
                current["start"], current["end"], current["all_day"], args.start, all_day, tz
            )
        else:
            end_text = current["end"]
        start, end, all_day, stored_start, stored_end = _timed_or_all_day(
            start_text, end_text, all_day, tz, strict=args.all_day is False
        )
        ensure_not_past(start, ctx.clock)
        changes.update({"start": stored_start, "end": stored_end, "all_day": all_day})
        patch.update({"start": start, "end": end, "all_day": all_day})

    if not changes:
        raise ToolError("nothing to change")
    if plan is None:
        assert event is not None
        moved = calendar.patch_event(event.id, **patch)
        return {"plan": None, "event": moved.to_public(), "was": event.to_public()}
    patched = None
    if patch and plan.google_event_id:
        patched = calendar.patch_event(plan.google_event_id, **patch)
    with transaction(ctx.conn):
        updated = plans.update(ctx.conn, plan.id, changes, now=ctx.now_iso())
    return {
        "plan": updated.model_dump(mode="json") if updated else None,
        "event": patched.to_public() if patched else None,
    }


@tool(
    name="delete_event",
    description=(
        "Take something off the calendar entirely: a plan by plan_id, or an event put there by "
        "hand by its event_id. Prefer cancelling a plan via update_event."
    ),
    available=calendar_available,
    unavailable_reason=NOT_CONFIGURED,
    writes=True,
)
def delete_event(ctx: ToolContext, args: DeleteEventInput) -> dict[str, Any]:
    plan, event = _target(ctx, args.plan_id, args.event_id)
    if plan is None:
        assert event is not None
        return _remove_event(ctx, event)
    if plan.status == "cancelled":
        return {"plan": plan.model_dump(mode="json"), "note": "already cancelled"}
    return _cancel(ctx, plan)
