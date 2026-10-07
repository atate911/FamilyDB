"""Household tasks with their current reminder. The rules for changing them live in task_service."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel


class Reminder(BaseModel):
    id: int
    task_id: int
    remind_at: str
    message_id: int | None = None
    cancelled_at: str | None = None
    delivered_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Reminder:
        return cls(**dict(row))


Unit = Literal["day", "week", "month", "year"]


class Task(BaseModel):
    id: int
    title: str
    notes: str = ""
    owner_id: int | None = None
    owner: str | None = None
    due_at: str | None = None
    preferred_window: str = ""
    # The last day "this weekend" in preferred_window means (windows.until), YYYY-MM-DD.
    window_until: str | None = None
    status: Literal["open", "done", "cancelled"] = "open"
    revision: int = 1
    # Coming round again (task_service.py): all four set, or none.
    repeat_every: int | None = None
    repeat_unit: Unit | None = None
    repeat_from: Literal["schedule", "done"] | None = None
    repeat_anchor: str | None = None
    last_done_at: str | None = None
    # Whose birthday or anniversary it is: its reminder lists the gifts saved for them.
    gift_for: str | None = None
    nudged_at: str | None = None
    # A reminder tied to a plan, and which (plan_service.REMIND_BEFORE): it moves with the plan.
    plan_id: int | None = None
    plan_remind: str | None = None
    channel: str
    chat_id: str
    created_at: str
    updated_at: str
    reminder: Reminder | None = None

    @property
    def repeats(self) -> bool:
        return self.repeat_every is not None and self.repeat_unit is not None

    @property
    def until(self) -> date | None:
        """The last day its window holds, when it said "this weekend" (windows.read)."""
        return date.fromisoformat(self.window_until) if self.window_until else None

    @classmethod
    def from_row(cls, row: sqlite3.Row, reminder: Reminder | None) -> Task:
        data = dict(row)
        data.pop("operation_key", None)
        return cls(**data, reminder=reminder)


def get(conn: sqlite3.Connection, task_id: int) -> Task | None:
    row = conn.execute(
        "SELECT t.*, m.display_name AS owner FROM tasks t "
        "LEFT JOIN members m ON m.id=t.owner_id WHERE t.id=?",
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    reminder = conn.execute(
        "SELECT r.*, m.delivered_at FROM reminders r LEFT JOIN messages m ON m.id=r.message_id "
        "WHERE r.task_id=? AND r.cancelled_at IS NULL ORDER BY r.id DESC LIMIT 1",
        (task_id,),
    ).fetchone()
    return Task.from_row(row, Reminder.from_row(reminder) if reminder else None)


def list_all(
    conn: sqlite3.Connection, *, status: str = "open", query: str = "", owner_id: int | None = None
) -> list[Task]:
    rows = conn.execute(
        "SELECT id FROM tasks WHERE (?='all' OR status=?) "
        "AND (? IS NULL OR owner_id=?) AND (instr(lower(title),lower(?))>0 "
        "OR instr(lower(notes),lower(?))>0) ORDER BY due_at IS NULL, due_at, id LIMIT 100",
        (status, status, owner_id, owner_id, query, query),
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def everything(conn: sqlite3.Connection) -> list[Task]:
    """Every task, whatever became of it, oldest first: for the spreadsheet (export.py)."""
    rows = conn.execute("SELECT id FROM tasks ORDER BY id").fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def in_chat(
    conn: sqlite3.Connection, channel: str, chat_id: str, *, limit: int = 100
) -> list[Task]:
    """Open tasks asked for in one chat (their reminders go there): deadlines first, then oldest."""
    rows = conn.execute(
        "SELECT id FROM tasks WHERE status='open' AND channel=? AND chat_id=? "
        "ORDER BY due_at IS NULL, due_at, id LIMIT ?",
        (channel, chat_id, limit),
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def linked_to(conn: sqlite3.Connection, plan_id: int) -> list[Task]:
    """The open reminders tied to a plan (plan_service)."""
    rows = conn.execute(
        "SELECT id FROM tasks WHERE plan_id=? AND status='open' ORDER BY id", (plan_id,)
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def cancel(conn: sqlite3.Connection, task_id: int, now: str) -> None:
    """Cancel one open task with its reminders. Call inside a transaction."""
    _cancel(conn, "SELECT id FROM tasks WHERE id = ? AND status = 'open'", (task_id,), now)


def finish_linked(conn: sqlite3.Connection, *, ended_before: str, now: str) -> int:
    """Mark done the open reminders tied to a plan that ended before `ended_before` (a date),
    cancelling any reminder of theirs not yet sent; returns how many. Dates compare as the
    plans' own (`plans.due_for_follow_up`). Call inside a transaction."""
    return _cancel(
        conn,
        "SELECT t.id FROM tasks t JOIN plans p ON p.id = t.plan_id WHERE t.plan_id IS NOT NULL "
        "AND t.status = 'open' AND substr(coalesce(p.end, p.start), 1, 10) < ?",
        (ended_before,),
        now,
        status="done",
    )


def find_by_operation(conn: sqlite3.Connection, operation_key: str) -> Task | None:
    """The task an earlier attempt at the same request saved, if any."""
    row = conn.execute("SELECT id FROM tasks WHERE operation_key=?", (operation_key,)).fetchone()
    return get(conn, row["id"]) if row else None


def creators(conn: sqlite3.Connection, task_ids: list[int]) -> dict[int, str]:
    """Who made each of these tasks, by name, where that is known (migration 0040). Only the page
    asks: it is not part of the record the model reads."""
    if not task_ids:
        return {}
    marks = ",".join("?" * len(task_ids))
    rows = conn.execute(
        f"SELECT t.id, m.display_name AS name FROM tasks t JOIN members m "
        f"ON m.id = t.created_by_member_id WHERE t.id IN ({marks})",
        task_ids,
    )
    return {row["id"]: row["name"] for row in rows}


def insert(
    conn: sqlite3.Connection,
    *,
    title: str,
    notes: str,
    owner_id: int | None,
    due_at: str | None,
    preferred_window: str,
    operation_key: str,
    channel: str,
    chat_id: str,
    now: str,
    repeat: dict[str, Any] | None = None,
    gift_for: str | None = None,
    created_by_member_id: int | None = None,
    plan_id: int | None = None,
    plan_remind: str | None = None,
    window_until: str | None = None,
) -> int:
    """A new task. `repeat` holds the four repeat_ columns, when it comes round again."""
    row = {
        "title": title,
        "notes": notes,
        "owner_id": owner_id,
        "due_at": due_at,
        "preferred_window": preferred_window,
        "operation_key": operation_key,
        "channel": channel,
        "chat_id": chat_id,
        "created_at": now,
        "updated_at": now,
        **(repeat or {}),
        **({"gift_for": gift_for} if gift_for else {}),
        **({"created_by_member_id": created_by_member_id} if created_by_member_id else {}),
        **({"plan_id": plan_id, "plan_remind": plan_remind} if plan_id is not None else {}),
        **({"window_until": window_until} if window_until else {}),
    }
    cur = conn.execute(
        f"INSERT INTO tasks({','.join(row)}) VALUES ({','.join('?' * len(row))})",
        tuple(row.values()),
    )
    return int(cur.lastrowid or 0)


def update(conn: sqlite3.Connection, task_id: int, changes: dict[str, Any]) -> None:
    """Set the given columns and bump the revision; callers pass only editable columns."""
    assignment = ", ".join(f"{key}=?" for key in changes)
    conn.execute(
        f"UPDATE tasks SET {assignment}, revision=revision+1 WHERE id=?",
        (*changes.values(), task_id),
    )


def add_reminder(conn: sqlite3.Connection, task_id: int, remind_at: str) -> None:
    conn.execute("INSERT INTO reminders(task_id,remind_at) VALUES (?,?)", (task_id, remind_at))


def has_pending_reminder(conn: sqlite3.Connection, task_id: int) -> bool:
    """Whether a live reminder has no message yet."""
    row = conn.execute(
        "SELECT 1 FROM reminders WHERE task_id=? AND cancelled_at IS NULL AND message_id IS NULL",
        (task_id,),
    ).fetchone()
    return row is not None


def reminder_in_flight(conn: sqlite3.Connection, task_id: int, now: str) -> bool:
    """Whether a live reminder's message is claimed for sending right now."""
    row = conn.execute(
        "SELECT 1 FROM reminders r JOIN messages m ON m.id=r.message_id "
        "WHERE r.task_id=? AND r.cancelled_at IS NULL AND m.claim_until>?",
        (task_id, now),
    ).fetchone()
    return row is not None


def cancel_reminders(conn: sqlite3.Connection, task_id: int, now: str) -> None:
    """Cancel a task's live reminders and any of their messages not yet delivered."""
    conn.execute(
        "UPDATE messages SET cancelled_at=? WHERE delivered_at IS NULL AND id IN "
        "(SELECT message_id FROM reminders WHERE task_id=? AND cancelled_at IS NULL)",
        (now, task_id),
    )
    conn.execute(
        "UPDATE reminders SET cancelled_at=? WHERE task_id=? AND cancelled_at IS NULL",
        (now, task_id),
    )


def cancel_in_chat(conn: sqlite3.Connection, channel: str, chat_id: str, now: str) -> int:
    """Cancel every open task in one chat with its reminders (somebody taken off the list);
    returns how many. Call inside a transaction."""
    return _cancel(
        conn,
        "SELECT id FROM tasks WHERE channel = ? AND chat_id = ? AND status = 'open'",
        (channel, chat_id),
        now,
    )


def cancel_owned_by(conn: sqlite3.Connection, member_id: int, now: str) -> int:
    """Cancel the open tasks somebody owns that were asked for outside a group (on the page, or
    in somebody's own chat), with their reminders. Taking them off the list would leave each
    nobody's, which is everyone's, and send their errand to the family's chat
    (routing.for_task). One asked for in a group stays there, the family's, as it always has.
    Returns how many. Call inside a transaction."""
    return _cancel(
        conn,
        "SELECT id FROM tasks WHERE owner_id = ? AND status = 'open' "
        "AND NOT (channel = 'telegram' AND chat_id LIKE '-%')",
        (member_id,),
        now,
    )


def open_for(
    conn: sqlite3.Connection, channel: str, chat_id: str, member_id: int | None, *, limit: int = 100
) -> list[Task]:
    """Open tasks asked for in this chat and, wherever they were asked for, this person's own:
    what /tasks and /today list, so a task Sam set for Alex is on Alex's list too."""
    rows = conn.execute(
        "SELECT id FROM tasks WHERE status='open' AND ((channel=? AND chat_id=?) "
        "OR (? IS NOT NULL AND owner_id=?)) ORDER BY due_at IS NULL, due_at, id LIMIT ?",
        (channel, chat_id, member_id, member_id, limit),
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def _cancel(
    conn: sqlite3.Connection,
    query: str,
    params: tuple[Any, ...],
    now: str,
    *,
    status: Literal["cancelled", "done"] = "cancelled",
) -> int:
    open_ids = [int(row["id"]) for row in conn.execute(query, params)]
    for task_id in open_ids:
        cancel_reminders(conn, task_id, now)
        conn.execute(
            "UPDATE tasks SET status = ?, revision = revision + 1, updated_at = ? WHERE id = ?",
            (status, now, task_id),
        )
    return len(open_ids)


def unchased(
    conn: sqlite3.Connection, *, delivered_from: str, delivered_until: str
) -> list[tuple[int, Task]]:
    """Reminders that went between the two times and were neither done nor snoozed nor brought
    up since, each with its task, which does not repeat and is no plan's heads-up: what the
    morning message chases, once (`chased_at`)."""
    rows = conn.execute(
        "SELECT r.id AS reminder_id, r.task_id FROM reminders r "
        "JOIN messages m ON m.id = r.message_id JOIN tasks t ON t.id = r.task_id "
        "WHERE m.delivered_at >= ? AND m.delivered_at < ? AND r.cancelled_at IS NULL "
        "AND r.chased_at IS NULL AND t.status = 'open' AND t.repeat_every IS NULL "
        "AND t.plan_id IS NULL AND (t.nudged_at IS NULL OR t.nudged_at < m.delivered_at) "
        "ORDER BY r.remind_at",
        (delivered_from, delivered_until),
    ).fetchall()
    return [
        (int(row["reminder_id"]), task)
        for row in rows
        if (task := get(conn, row["task_id"])) is not None
    ]


def mark_chased(conn: sqlite3.Connection, reminder_ids: list[int], now: str) -> None:
    conn.executemany(
        "UPDATE reminders SET chased_at = ? WHERE id = ?", [(now, rid) for rid in reminder_ids]
    )


def due_between(conn: sqlite3.Connection, start: str, end: str) -> list[Task]:
    """Open tasks due from `start` until before `end` (UTC instants), soonest first."""
    rows = conn.execute(
        "SELECT id FROM tasks WHERE status = 'open' AND due_at >= ? AND due_at < ? "
        "ORDER BY due_at, id",
        (start, end),
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def reminded_between(conn: sqlite3.Connection, start: str, end: str) -> list[Task]:
    """Open tasks with a reminder still to go from `start` until before `end`, soonest first."""
    rows = conn.execute(
        "SELECT DISTINCT t.id, r.remind_at FROM tasks t JOIN reminders r ON r.task_id = t.id "
        "WHERE t.status = 'open' AND r.cancelled_at IS NULL AND r.message_id IS NULL "
        "AND r.remind_at >= ? AND r.remind_at < ? ORDER BY r.remind_at, t.id",
        (start, end),
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def waiting(conn: sqlite3.Connection, *, said_before: str) -> list[Task]:
    """Open one-off tasks said before `said_before` with no reminder still to go and no plan:
    what the weekly round-up looks at (its window is read by the caller), oldest first."""
    rows = conn.execute(
        "SELECT t.id FROM tasks t WHERE t.status = 'open' AND t.repeat_every IS NULL "
        "AND t.plan_id IS NULL AND t.created_at < ? AND NOT EXISTS (SELECT 1 FROM reminders r "
        "WHERE r.task_id = t.id AND r.cancelled_at IS NULL AND r.message_id IS NULL) "
        "ORDER BY t.created_at, t.id",
        (said_before,),
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def reword_queued(conn: sqlite3.Connection, task_id: int, text: str) -> None:
    """Give a queued but unsent reminder message for this task new words."""
    conn.execute(
        "UPDATE messages SET text=? WHERE delivered_at IS NULL AND cancelled_at IS NULL "
        "AND id IN (SELECT message_id FROM reminders WHERE task_id=?)",
        (text, task_id),
    )


def due_reminders(conn: sqlite3.Connection, now: str, *, limit: int = 100) -> list[Reminder]:
    """Live reminders of open tasks whose time has come and that have no message yet."""
    rows = conn.execute(
        "SELECT r.id,r.task_id,r.remind_at FROM reminders r JOIN tasks t ON t.id=r.task_id "
        "WHERE r.cancelled_at IS NULL AND r.message_id IS NULL AND r.remind_at<=? "
        "AND t.status='open' ORDER BY r.remind_at LIMIT ?",
        (now, limit),
    ).fetchall()
    return [Reminder.from_row(row) for row in rows]


def attach_message(conn: sqlite3.Connection, reminder_id: int, message_id: int) -> None:
    conn.execute("UPDATE reminders SET message_id=? WHERE id=?", (message_id, reminder_id))


def nudge_candidates(
    conn: sqlite3.Connection, *, said_before: str, nudged_before: str, chats_quiet_since: str
) -> list[Task]:
    """Open tasks with a preferred window and nothing else to bring them up (no pending reminder
    or repeat), created before `said_before`, not nudged since `nudged_before`, in a chat quiet
    since `chats_quiet_since`; never-nudged first, then longest ago. Reading the window is the
    caller's."""
    rows = conn.execute(
        "SELECT t.id FROM tasks t WHERE t.status='open' AND t.preferred_window!='' "
        "AND t.repeat_every IS NULL AND t.created_at<? "
        "AND (t.nudged_at IS NULL OR t.nudged_at<?) "
        "AND NOT EXISTS (SELECT 1 FROM reminders r WHERE r.task_id=t.id "
        "AND r.cancelled_at IS NULL AND r.message_id IS NULL) "
        "AND NOT EXISTS (SELECT 1 FROM tasks o WHERE o.channel=t.channel AND o.chat_id=t.chat_id "
        "AND o.nudged_at>=?) "
        "ORDER BY t.nudged_at IS NOT NULL, t.nudged_at, t.id LIMIT 100",
        (said_before, nudged_before, chats_quiet_since),
    ).fetchall()
    return [task for row in rows if (task := get(conn, row["id"])) is not None]


def mark_nudged(conn: sqlite3.Connection, task_id: int, now: str) -> None:
    """Note a nudge; the revision stays, so a form drawn before it still saves."""
    conn.execute("UPDATE tasks SET nudged_at=? WHERE id=?", (now, task_id))
