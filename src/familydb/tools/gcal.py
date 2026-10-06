"""Calendar tools: what is on, and plans made, moved and cancelled.

With Google connected the plans are its events, kept in step both ways (calendar_sync.py). Without
it they are still kept, here, holding the id their event will have once Google is connected
(`calendar_ops`), when they are put on it (`calendar_sync.adopt_local`). A plan on Google is never
changed here alone while Google cannot be reached: the two would drift apart.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from familydb import plan_service, routing, task_service
from familydb import undo as taking_back
from familydb.availability import calendar_available
from familydb.calendar_sync import adopt, event_changes, refresh_plan, sync_plans
from familydb.dates import (
    ensure_not_past,
    iso_date,
    iso_datetime,
    parse_date,
    parse_date_range,
    parse_datetime,
    utc_iso,
)
from familydb.errors import ToolError, ToolUnavailable
from familydb.free_time import events_by_day, free_blocks
from familydb.integrations.google_calendar import CalendarAPI, CalendarEvent
from familydb.plan_service import RemindBefore
from familydb.saved_plans import SavedPlans
from familydb.store import calendar_ops, ideas, messages, plans, tasks
from familydb.store.db import to_json, transaction
from familydb.tools.registry import ToolContext, tool

NOT_CONFIGURED = "Google Calendar is not connected (no calendar id or key configured)"
KEPT_HERE = "no Google calendar is connected: kept here, and put on it once one is"
ON_GOOGLE_ONLY = (
    "plan #{plan} is on the Google calendar, which is not connected now; connect it again to "
    "change it"
)
MAX_WINDOW_DAYS = 60
DEFAULT_DURATION = timedelta(hours=2)
# plan field -> Google event field
TEXT_FIELDS = {"title": "title", "location": "location", "notes": "description"}


class GetCalendarInput(BaseModel):
    start: str = Field(description="First day, YYYY-MM-DD.")
    end: str = Field(description="Last day, YYYY-MM-DD (inclusive).")


REMIND_HELP = "Reminders before it, which move with it; at most 2."


class CreateEventInput(BaseModel):
    title: str
    start: str = Field(description="YYYY-MM-DDTHH:MM in the family timezone, or YYYY-MM-DD.")
    end: str | None = Field(default=None, description="Same format. Default: start plus 2 hours.")
    all_day: bool = Field(default=False, description="True when no time is known.")
    location: str | None = None
    notes: str | None = None
    idea_id: int | None = Field(default=None, description="The idea this plan is for, if any.")
    remind_before: list[RemindBefore] = Field(default_factory=list, description=REMIND_HELP)


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
    remind_before: list[RemindBefore] | None = Field(
        default=None, description="Replaces its reminders; [] takes them off."
    )


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
        sync_plans(
            ctx.conn, ctx.calendar, ctx.settings.google_calendar_id, ctx.now_iso(), tz=ctx.clock.tz
        )
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


def _google(ctx: ToolContext) -> CalendarAPI | None:
    """The Google calendar plans go on, or None when none is configured and plans are kept here.
    Configured but not reachable from here is unavailable, never quietly kept here instead."""
    return _calendar(ctx) if calendar_available(ctx.settings) else None


def _on_google(ctx: ToolContext, plan: plans.Plan) -> bool:
    """Whether the plan is an event on the calendar configured now (not one kept here)."""
    return (
        bool(plan.google_event_id)
        and plan.calendar_id is not None
        and plan.calendar_id == ctx.settings.google_calendar_id
    )


def _timed_or_all_day(
    start_text: str,
    end_text: str | None,
    all_day: bool,
    tz: ZoneInfo,
    *,
    strict: bool = False,
) -> tuple[datetime | date, datetime | date, bool, str, str | None]:
    """Resolve start/end into calendar values and stored strings; a date-only start is all-day
    unless `strict` requires a time."""
    date_only = len(start_text.strip()) == 10
    if date_only and strict and not all_day:
        raise ToolError("give a start time (YYYY-MM-DDTHH:MM) to make this a timed plan")
    if all_day or date_only:
        start_d = parse_date(start_text.strip()[:10])
        end_d = parse_date(end_text.strip()[:10]) if end_text else start_d
        if end_d < start_d:
            raise ToolError("end is before start")
        # Google's all-day end is exclusive
        return start_d, end_d + timedelta(days=1), True, iso_date(start_d), iso_date(end_d)
    start_dt = parse_datetime(start_text, tz)
    end_dt = parse_datetime(end_text, tz) if end_text else start_dt + DEFAULT_DURATION
    if end_dt <= start_dt:
        raise ToolError("end must be after start")
    return start_dt, end_dt, False, iso_datetime(start_dt), iso_datetime(end_dt)


def _end_keeping_duration(
    start: str, end: str | None, was_all_day: bool, new_start: str, all_day: bool, tz: ZoneInfo
) -> str | None:
    """Carry the plan's length over to a moved start."""
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
    """Per-day timed events, all-day entries and free blocks, as `get_calendar` reports."""
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
)
def get_calendar(ctx: ToolContext, args: GetCalendarInput) -> dict[str, Any]:
    start, end = parse_date_range(args.start, args.end)
    if (end - start).days > MAX_WINDOW_DAYS:
        raise ToolError(f"ask for at most {MAX_WINDOW_DAYS} days at a time")
    calendar = _google(ctx)
    if calendar is None:
        days = calendar_days(SavedPlans(ctx.conn, ctx.clock.tz), start, end, ctx.clock.tz)
        kept = {
            plan.google_event_id: plan.id
            for plan in plans.overlapping(ctx.conn, start.isoformat(), end.isoformat())
            if plan.google_event_id
        }
        _number(days, kept)
        return {"calendar": None, "plans": KEPT_HERE, "days": days}
    days = calendar_days(calendar, start, end, ctx.clock.tz)
    sync_plans(ctx.conn, calendar, ctx.settings.google_calendar_id, ctx.now_iso(), tz=ctx.clock.tz)
    owned = {
        event_id: plan.id
        for event_id, plan in plans.by_google_event(
            ctx.conn, ctx.settings.google_calendar_id
        ).items()
    }
    _number(days, owned)
    return {"calendar": ctx.settings.google_calendar_id, "days": days}


def _number(days: list[dict[str, Any]], owned: dict[str, int]) -> None:
    """Name the plan behind each event, where the bot has one."""
    for day in days:
        for event in day["events"]:
            event["plan_id"] = owned.get(event["google_event_id"])
        for event in day["all_day_events"]:
            event["plan_id"] = owned.get(event["id"])


def _created(ctx: ToolContext, plan: plans.Plan, event: CalendarEvent | None) -> dict[str, Any]:
    idea = ideas.get(ctx.conn, plan.idea_id) if plan.idea_id is not None else None
    made = {
        "plan": plan.model_dump(mode="json"),
        "event": event.to_public() if event else None,
        "idea": idea.model_dump(mode="json") if idea else None,
    }
    return made if _on_google(ctx, plan) else {**made, "calendar": KEPT_HERE}


@tool(
    name="create_event",
    description=(
        "Put a confirmed plan on the shared family calendar (kept here when none is connected) "
        "and link it to an idea. Resolve the date yourself and echo it back to the family "
        "afterwards. Returns the plan number."
    ),
    writes=True,
)
def create_event(ctx: ToolContext, args: CreateEventInput) -> dict[str, Any]:
    calendar = _google(ctx)
    tz = ctx.clock.tz
    if args.idea_id is not None and ideas.get(ctx.conn, args.idea_id) is None:
        raise ToolError(f"no idea #{args.idea_id}")
    start, end, all_day, stored_start, stored_end = _timed_or_all_day(
        args.start, args.end, args.all_day, tz
    )
    # Persist identity before contacting Google, so the same request and event intent reuse it
    # after a crash or a lost response.
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
    # A redrawn form has a new identity; the same browser session asking for the same event
    # takes over the unfinished attempt, which may already have made it.
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
    event = calendar.get_event(event_id) if calendar is not None else None
    existing = plans.for_event(ctx.conn, event_id)
    if existing is not None:
        return _made(ctx, existing, event, args.remind_before)  # finished before: say so again
    if event is None:
        ensure_not_past(start, ctx.clock)
    if event is None and calendar is not None:
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
    # Made on the page there is no chat to answer in: the family's, so the evening-before check
    # goes where everybody reads and the day-after question to its maker (routing.for_person).
    channel, chat_id = (
        (origin.channel, origin.chat_id)
        if origin is not None
        else routing.family_chat(ctx.settings) or ("web", "web")
    )
    with transaction(ctx.conn):
        plan = plans.for_event(ctx.conn, event_id)  # a concurrent attempt may have finished
        made = plan is None
        if plan is None:
            plan = plans.insert(
                ctx.conn,
                title=args.title.strip(),
                start=stored_start,
                end=stored_end,
                all_day=all_day,
                idea_id=args.idea_id,
                # Kept here, it holds the id its event will have, for when it goes on Google.
                google_event_id=event.id if event is not None else event_id,
                calendar_id=ctx.settings.google_calendar_id if event is not None else None,
                location=args.location,
                notes=args.notes,
                created_by=ctx.member.id if ctx.member else None,
                channel=channel,
                chat_id=chat_id,
                now=ctx.now_iso(),
            )
            if args.idea_id is not None:
                ideas.update(ctx.conn, args.idea_id, {"status": "planned"}, now=ctx.now_iso())
    if made:
        taking_back.keep(
            ctx,
            "cancel_plan",
            f"put {plan.title} on the calendar (plan #{plan.id})",
            plan=plan.id,
            updated_at=plan.updated_at,
        )
    return _made(ctx, plan, event, args.remind_before)


def _made(
    ctx: ToolContext, plan: plans.Plan, event: CalendarEvent | None, remind_before: list[str]
) -> dict[str, Any]:
    made = _created(ctx, plan, event)
    return {**made, **_remind(ctx, plan, remind_before)} if remind_before else made


def _cancel(ctx: ToolContext, plan: plans.Plan) -> dict[str, Any]:
    if _on_google(ctx, plan):
        _calendar(ctx).delete_event(plan.google_event_id)  # type: ignore[arg-type]
    with transaction(ctx.conn):
        updated = plans.update(ctx.conn, plan.id, {"status": "cancelled"}, now=ctx.now_iso())
        if updated is not None:
            plan_service.changed(ctx.conn, plan, updated, now=ctx.now_iso(), tz=ctx.clock.tz)
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
    """The plan, or the hand-made event, a change is for (exactly one). The bot's own event is
    always worked on as its plan, so plan and idea stay in step."""
    if (plan_id is None) == (event_id is None):
        raise ToolError("give plan_id, or event_id for an event put on the calendar by hand")
    calendar = _google(ctx)
    if plan_id is None:
        assert event_id is not None
        owned = plans.for_event(ctx.conn, event_id)
        ours = owned is not None and owned.calendar_id in (None, ctx.settings.google_calendar_id)
        if not ours:
            event = calendar.get_event(event_id) if calendar is not None else None
            if event is None:
                raise ToolError(f"no event {event_id} on the calendar; get_calendar lists them")
            return None, event
        assert owned is not None
        plan_id = owned.id
    plan = plans.get(ctx.conn, plan_id)
    if plan is None:
        raise ToolError(f"no plan #{plan_id}")
    still_to_come = (plan.end or plan.start)[:10] >= ctx.clock.today().isoformat()
    if plan.calendar_id is None and calendar is not None:
        if plan.status != "cancelled" and still_to_come:
            # Kept here before Google was connected: on Google first, then changed there.
            plan = adopt(ctx.conn, calendar, plan, ctx.settings.google_calendar_id, ctx.now_iso())
    elif plan.calendar_id is not None and calendar is None:
        raise ToolUnavailable(ON_GOOGLE_ONLY.format(plan=plan.id))
    elif plan.calendar_id not in (None, ctx.settings.google_calendar_id):
        raise ToolError("this plan belongs to a different calendar")
    return plan, None


def _remove_event(ctx: ToolContext, event: CalendarEvent) -> dict[str, Any]:
    """Take an event that is not the bot's own off the calendar."""
    _calendar(ctx).delete_event(event.id)
    return {"plan": None, "removed": event.to_public()}


@tool(
    name="update_event",
    description=(
        "Change a plan on the calendar: new time, title, place, notes, or cancel it. Moving only "
        "the start keeps the plan's length. An event put on the calendar by hand is changed by "
        "its event_id."
    ),
    writes=True,
)
def update_event(ctx: ToolContext, args: UpdateEventInput) -> dict[str, Any]:
    calendar = _google(ctx)
    plan, event = _target(ctx, args.plan_id, args.event_id)
    if plan is not None:
        if calendar is not None:
            plan = refresh_plan(
                ctx.conn,
                calendar,
                plan,
                ctx.settings.google_calendar_id,
                ctx.now_iso(),
                tz=ctx.clock.tz,
            )
        if plan.status == "cancelled":
            raise ToolError(f"plan #{plan.id} is cancelled; create a new event instead")
        if args.status == "cancelled":
            return _cancel(ctx, plan)
    elif args.status == "cancelled":
        assert event is not None
        return _remove_event(ctx, event)
    # Current state in plan-storage form, for a plan or a hand-made event.
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

    if not changes and args.remind_before is None:
        raise ToolError("nothing to change")
    if plan is None:
        assert event is not None and calendar is not None
        if args.remind_before is not None:
            raise ToolError("reminders go only on the bot's own plans; add_task for this one")
        moved = calendar.patch_event(event.id, **patch)
        return {"plan": None, "event": moved.to_public(), "was": event.to_public()}
    patched = None
    updated: plans.Plan | None = plan
    if changes:
        if patch and calendar is not None and _on_google(ctx, plan):
            patched = calendar.patch_event(plan.google_event_id, **patch)  # type: ignore[arg-type]
        with transaction(ctx.conn):
            updated = plans.update(ctx.conn, plan.id, changes, now=ctx.now_iso())
            if updated is not None:
                plan_service.changed(ctx.conn, plan, updated, now=ctx.now_iso(), tz=ctx.clock.tz)
        if updated is not None and set(changes) <= MOVES:
            taking_back.keep(
                ctx,
                "restore_plan",
                f"changed plan #{plan.id} {plan.title}",
                plan=plan.id,
                updated_at=updated.updated_at,
                before={key: getattr(plan, key) for key in MOVES},
            )
    result = {
        "plan": updated.model_dump(mode="json") if updated else None,
        "event": patched.to_public() if patched else None,
    }
    if args.remind_before is not None and updated is not None:
        result.update(_remind(ctx, updated, args.remind_before, replace=True))
    return result


MAX_REMINDERS = 2
# A change to these can be put back (undo.py); a new place or notes, or a cancel, cannot.
MOVES = frozenset({"title", "start", "end", "all_day"})


def _remind(
    ctx: ToolContext, plan: plans.Plan, words: list[str], *, replace: bool = False
) -> dict[str, Any]:
    """Reminders tied to a plan, one task each (plan_service): they move with it and go with it.
    `replace` takes off the ones not named again. Each goes to the person asking, as any
    reminder they set would (routing.for_task)."""
    wanted = list(dict.fromkeys(words))
    if len(wanted) > MAX_REMINDERS:
        raise ToolError(f"at most {MAX_REMINDERS} reminders for one plan")
    now = ctx.now_iso()
    have = {task.plan_remind: task for task in tasks.linked_to(ctx.conn, plan.id)}
    if replace:
        with transaction(ctx.conn):
            for word, task in have.items():
                if word not in wanted:
                    tasks.cancel(ctx.conn, task.id, now)
    origin = messages.get(ctx.conn, ctx.message_id) if ctx.message_id is not None else None
    channel, chat_id = (origin.channel, origin.chat_id) if origin else ("web", "web")
    if channel == "console":  # nobody hears the console once it is closed
        channel, chat_id = "web", "web"
    scope = ctx.operation_id or (
        f"message:{ctx.message_id}" if ctx.message_id is not None else uuid.uuid4().hex
    )
    member = ctx.member.id if ctx.member else None
    set_for: list[dict[str, Any]] = []
    not_set: list[str] = []
    for word in wanted:
        if word in have:
            set_for.append(_reminder_brief(ctx, have[word]))
            continue
        try:
            when = plan_service.remind_at(ctx.conn, plan, word, ctx.clock.tz)
        except ToolError as exc:
            not_set.append(f"{word}: {exc}")
            continue
        if when <= ctx.clock.now():
            not_set.append(f"{word}: that time has passed")
            continue
        key = f"plan:{plan.id}:{word}:{scope}"
        earlier = tasks.find_by_operation(ctx.conn, key)
        if earlier is not None and earlier.status != "open":
            key = f"{key}:{earlier.id}"  # taken off earlier in this request, and wanted again
        task = task_service.create(
            ctx.conn,
            {
                "title": plan.title,
                "owner_id": member,
                "created_by_member_id": member,
                "plan_id": plan.id,
                "plan_remind": word,
            },
            reminder=utc_iso(when),
            operation_key=key,
            channel=channel,
            chat_id=chat_id,
            now=now,
        )
        set_for.append(_reminder_brief(ctx, task))
    found: dict[str, Any] = {"reminders": set_for}
    if not_set:
        found["reminders_not_set"] = not_set
    return found


def _reminder_brief(ctx: ToolContext, task: tasks.Task) -> dict[str, Any]:
    at = task.reminder.remind_at if task.reminder else None
    local = (
        datetime.fromisoformat(at).astimezone(ctx.clock.tz).strftime("%Y-%m-%dT%H:%M")
        if at
        else None
    )
    return {"task": task.id, "before": task.plan_remind, "at": local}


@tool(
    name="delete_event",
    description=(
        "Take something off the calendar entirely: a plan by plan_id, or an event put there by "
        "hand by its event_id. Prefer cancelling a plan via update_event."
    ),
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
