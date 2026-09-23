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
from familydb.tools.registry import ToolContext, tool


class AddTaskInput(BaseModel):
    title: str
    notes: str = ""
    owner: str | None = Field(
        default=None, description="Family member name; defaults to the sender."
    )
    due_at: str | None = Field(
        default=None,
        description=(
            "Optional deadline, YYYY-MM-DDTHH:MM in family timezone. Does not schedule a reminder. "
        ),
    )
    preferred_window: str = Field(
        default="", description="Flexible intent, e.g. some Saturday morning. Not a scheduled time."
    )
    remind_at: str | None = Field(
        default=None,
        description=(
            "Explicit reminder time YYYY-MM-DDTHH:MM in family timezone. Ask for time "
            "if ambiguous. "
        ),
    )


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
        "Save an intention or obligation, optionally with an explicit reminder. "
        "Does not create a calendar event. Reminders return to this chat; browser "
        "reminders appear in web chat. "
    ),
    writes=True,
)
def add_task(ctx: ToolContext, args: AddTaskInput) -> dict[str, Any]:
    scope = ctx.operation_id or (
        f"message:{ctx.message_id}" if ctx.message_id else uuid.uuid4().hex
    )
    key = hashlib.sha256((scope + to_json(args.model_dump())).encode()).hexdigest()
    previous = ctx.conn.execute("SELECT id FROM tasks WHERE operation_key=?", (key,)).fetchone()
    if previous:
        task = tasks.get(ctx.conn, previous["id"])
        return {"task": task, "reminder_destination": task["channel"], "timezone": ctx.clock.tz.key}
    values = args.model_dump(exclude={"owner", "remind_at"})
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
    )
    return {"task": task, "reminder_destination": channel, "timezone": ctx.clock.tz.key}


@tool(
    name="update_task",
    description=(
        "Edit, complete, cancel, reopen, or snooze a saved task. Completing or "
        "cancelling stops pending reminders. Reopening does not restore old "
        "reminders. "
    ),
    writes=True,
)
def update_task(ctx: ToolContext, args: UpdateTaskInput) -> dict[str, Any]:
    values = {
        k: v
        for k, v in args.model_dump(
            exclude={"task_id", "owner", "remind_at", "clear_due", "clear_reminder"}
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
    reminder = _time(ctx, args.remind_at, future=True)
    return {
        "task": task_service.update(
            ctx.conn,
            args.task_id,
            values,
            now=ctx.now_iso(),
            reminder=reminder,
            replace_reminder=bool(args.remind_at or args.clear_reminder),
            revision=ctx.task_revision,
        )
    }


@tool(
    name="list_tasks",
    description=(
        "Find saved tasks and obligations, including their deadlines, flexible "
        "windows, reminder delivery state and task IDs. Defaults to open tasks; "
        "search before editing or answering what is unfinished. "
    ),
)
def list_tasks(ctx: ToolContext, args: ListTasksInput) -> dict[str, Any]:
    return {
        "tasks": tasks.list_all(
            ctx.conn,
            status=args.status,
            query=args.query,
            owner_id=_owner(ctx, args.owner) if args.owner else None,
        ),
        "limit": 100,
    }
