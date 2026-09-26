"""Tasks are intentions, not calendar commitments. Reminder times are explicit."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from familydb import task_service
from familydb.dates import parse_datetime, utc_iso
from familydb.errors import ToolError
from familydb.store import members, messages, tasks
from familydb.store.db import to_json
from familydb.store.tasks import Task
from familydb.tools.registry import ToolContext, tool


class AddTaskInput(BaseModel):
    title: str
    notes: str = ""
    owner: str | None = Field(
        default=None, description="Family member name; defaults to the sender."
    )
    due_at: str | None = Field(
        default=None,
        description=("Deadline, YYYY-MM-DDTHH:MM family time. Not a reminder."),
    )
    preferred_window: str = Field(
        default="", description="Flexible intent, e.g. some Saturday morning. Not a scheduled time."
    )
    remind_at: str | None = Field(
        default=None,
        description=("Reminder time, YYYY-MM-DDTHH:MM family time."),
    )
    repeat_every: int | None = Field(default=None, description="With remind_at as the first.")
    repeat_unit: Literal["day", "week", "month", "year"] | None = None
    repeat_from: Literal["schedule", "done"] = "schedule"


class UpdateTaskInput(BaseModel):
    task_id: int
    title: str | None = None
    notes: str | None = None
    owner: str | None = None
    due_at: str | None = None
    clear_due: bool = False
    preferred_window: str | None = None
    status: Literal["open", "done", "cancelled"] | None = None
    remind_at: str | None = Field(
        default=None, description="Snooze or set reminder to this future family-local date/time."
    )
    clear_reminder: bool = False
    repeat_every: int | None = None
    repeat_unit: Literal["day", "week", "month", "year"] | None = None
    repeat_from: Literal["schedule", "done"] | None = None
    stop_repeating: bool = False


class ListTasksInput(BaseModel):
    status: Literal["open", "done", "cancelled", "all"] = "open"
    query: str = ""
    owner: str | None = None


def _owner(ctx: ToolContext, name: str) -> int:
    member = members.find_by_name(ctx.conn, name)
    if member is None:
        raise ToolError(f"No active family member named {name}.")
    return member.id


def _time(ctx: ToolContext, value: str | None, *, future: bool = False) -> str | None:
    if value is None:
        return None
    if "T" not in value and " " not in value.strip():
        raise ToolError("Give a date and time, not just a day.")
    moment = parse_datetime(value, ctx.clock.tz)
    raw = datetime.fromisoformat(value.strip())
    if raw.tzinfo is None:
        if moment.astimezone(UTC).astimezone(ctx.clock.tz).replace(tzinfo=None) != raw:
            raise ToolError("That local time does not exist because the clocks change.")
        if moment.replace(fold=0).utcoffset() != moment.replace(fold=1).utcoffset():
            raise ToolError("That local time occurs twice; give an explicit UTC offset.")
    if future and moment.astimezone(UTC) <= ctx.clock.now().astimezone(UTC):
        raise ToolError("The reminder must be in the future.")
    return utc_iso(moment)


@tool(
    name="add_task",
    description=(
        "Save an obligation, optionally with a reminder. Not a calendar event. "
        "Reminders arrive in this chat; from the page, in its Chat."
    ),
    writes=True,
)
def add_task(ctx: ToolContext, args: AddTaskInput) -> dict[str, Any]:
    scope = ctx.operation_id or (
        f"message:{ctx.message_id}" if ctx.message_id else uuid.uuid4().hex
    )
    key = hashlib.sha256((scope + to_json(args.model_dump())).encode()).hexdigest()
    previous = tasks.find_by_operation(ctx.conn, key)
    if previous:
        return {
            "task": previous.model_dump(mode="json"),
            "reminder_destination": previous.channel,
            "timezone": ctx.clock.tz.key,
        }
    values = args.model_dump(
        exclude={"owner", "remind_at", "repeat_every", "repeat_unit", "repeat_from"}
    )
    values["owner_id"] = (
        _owner(ctx, args.owner) if args.owner else (ctx.member.id if ctx.member else None)
    )
    values["due_at"] = _time(ctx, args.due_at)
    reminder = _time(ctx, args.remind_at, future=True)
    origin = messages.get(ctx.conn, ctx.message_id) if ctx.message_id else None
    channel, chat_id = (origin.channel, origin.chat_id) if origin else ("web", "web")
    # Console cannot receive future notifications after it exits.
    if channel == "console":
        channel, chat_id = "web", "web"
    task = task_service.create(
        ctx.conn,
        values,
        reminder=reminder,
        operation_key=key,
        channel=channel,
        chat_id=chat_id,
        now=ctx.now_iso(),
        repeat=_repeat(args),
    )
    return {
        "task": task.model_dump(mode="json"),
        "reminder_destination": channel,
        "timezone": ctx.clock.tz.key,
    }


@tool(
    name="update_task",
    description=(
        "Edit, complete, cancel, reopen or snooze a task. Completing or cancelling "
        "stops its reminders; reopening does not restore them."
    ),
    writes=True,
)
def update_task(ctx: ToolContext, args: UpdateTaskInput) -> dict[str, Any]:
    values = {
        k: v
        for k, v in args.model_dump(
            exclude={
                "task_id",
                "owner",
                "remind_at",
                "clear_due",
                "clear_reminder",
                "repeat_every",
                "repeat_unit",
                "repeat_from",
                "stop_repeating",
            }
        ).items()
        if v is not None
    }
    if args.owner is not None:
        values["owner_id"] = _owner(ctx, args.owner)
    if args.clear_due and args.due_at:
        raise ToolError("Choose a deadline or clear it, not both.")
    if args.clear_reminder and args.remind_at:
        raise ToolError("Choose a reminder or clear it, not both.")
    if args.due_at or args.clear_due:
        values["due_at"] = _time(ctx, args.due_at) if not args.clear_due else None
    if args.stop_repeating and args.repeat_every:
        raise ToolError("Choose a repeat or stop it, not both.")
    reminder = _time(ctx, args.remind_at, future=True)
    task = task_service.update(
        ctx.conn,
        args.task_id,
        values,
        now=ctx.now_iso(),
        reminder=reminder,
        replace_reminder=bool(args.remind_at or args.clear_reminder),
        revision=ctx.task_revision,
        settings=ctx.settings,
        repeat=_repeat(args),
        stop_repeating=args.stop_repeating,
    )
    return {"task": task.model_dump(mode="json")}


def _repeat(args: AddTaskInput | UpdateTaskInput) -> dict[str, Any] | None:
    """How often it comes round, as asked, or None when nothing was said about it."""
    if args.repeat_every is None and args.repeat_unit is None:
        return None
    return {
        "repeat_every": args.repeat_every,
        "repeat_unit": args.repeat_unit,
        "repeat_from": args.repeat_from or "schedule",
    }


@tool(
    name="list_tasks",
    description=(
        "Find tasks and their ids, deadlines and reminders; open ones by default. "
        "Use before changing one or saying what is unfinished."
    ),
)
def list_tasks(ctx: ToolContext, args: ListTasksInput) -> dict[str, Any]:
    found = tasks.list_all(
        ctx.conn,
        status=args.status,
        query=args.query,
        owner_id=_owner(ctx, args.owner) if args.owner else None,
    )
    return {
        "tasks": [_brief(ctx, task) for task in found[:LISTED]],
        "not_shown": max(0, len(found) - LISTED),
    }


# Enough to answer "what's unfinished?"; a narrower query finds the rest.
LISTED = 25
NOTES_SHOWN = 200


def _brief(ctx: ToolContext, task: Task) -> dict[str, Any]:
    """What the model needs to talk about a task or change it, and nothing it does not."""

    def local(value: str | None) -> str | None:
        if not value:
            return None
        return datetime.fromisoformat(value).astimezone(ctx.clock.tz).strftime("%Y-%m-%dT%H:%M")

    notes = task.notes
    brief = {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "owner": task.owner,
        "notes": notes if len(notes) <= NOTES_SHOWN else notes[:NOTES_SHOWN] + "…",
        "due": local(task.due_at),
        "window": task.preferred_window,
    }
    reminder = task.reminder
    if reminder:
        brief["reminder"] = local(reminder.remind_at)
        brief["reminder_sent"] = bool(reminder.delivered_at)
    brief["repeats"] = task_service.repeat_words(task)
    brief["last_done"] = local(task.last_done_at)
    return {k: v for k, v in brief.items() if v not in (None, "")}
