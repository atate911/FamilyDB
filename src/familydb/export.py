"""The family's data to take away (docs/DESIGN.md section 16, "Taking the data away"): the plans as
a calendar file any calendar can open, the ideas and the things to do as spreadsheets, and, for an
admin, everything the family has kept as one JSON file. `familydb export DIR` writes all four from
the server. Read-only, and never a secret: no key, no password or its hash, no Telegram link, no
device a notice goes to, no session key.

Who may take what is the page's (`routes.export_*`, `settings.export_everything`): a grown-up the
calendar and the spreadsheets, with a present kept from them left out as on every page; an admin
everything, after typing their password again.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from collections.abc import Collection, Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from familydb import __version__
from familydb.base.config import Settings
from familydb.base.dates import parse_datetime
from familydb.store import db, ideas, plans, tasks

# A line of a calendar file is at most this many bytes, then folded (RFC 5545, 3.1).
FOLD = 75
IDEA_COLUMNS = (
    "id",
    "title",
    "kind",
    "status",
    "where",
    "for",
    "tags",
    "setting",
    "cost",
    "ages",
    "dates",
    "times_done",
    "rating",
    "added",
    "description",
    "url",
)
TASK_COLUMNS = ("id", "title", "status", "for", "due", "remind_at", "repeats", "notes", "added")
# Everything, table by table: the family's own records. Not the workings (calls, alerts, models,
# judgements), and never a column that is a secret or a way in.
TABLES: dict[str, tuple[str, ...]] = {
    "members": ("id", "display_name", "role", "active", "birth_date", "gender", "created_at"),
    "ideas": (),
    "places": (),
    "outcomes": (),
    "plans": (),
    "tasks": ("operation_key",),
    "reminders": (),
    "memories": (),
    "wishes": (),
    "lists": (),
    "list_items": (),
    "messages": ("claim_token", "claim_until", "channel_update_id"),
}
# For members the columns kept are listed (a new column is left out until somebody says it may
# go); for the rest, the columns left out.
KEPT_ONLY = frozenset({"members"})


def _text(value: str) -> str:
    """Text as a calendar file wants it (RFC 5545, 3.3.11)."""
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _folded(line: str) -> list[str]:
    """One content line, folded at `FOLD` bytes without splitting a character."""
    out: list[str] = []
    current = ""
    for char in line:
        limit = FOLD if not out else FOLD - 1  # a continuation starts with a space
        if len((current + char).encode("utf-8")) > limit:
            out.append(current)
            current = char
        else:
            current += char
    out.append(current)
    return [out[0], *(" " + rest for rest in out[1:])]


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def plans_ics(conn: sqlite3.Connection, settings: Settings, now: datetime) -> str:
    """Every plan not cancelled, as a calendar file: all-day ones as dates, timed ones in UTC so
    no time zone table is needed."""
    tz = settings.tzinfo
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//FamilyDB//{__version__}//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_text(settings.web_title or 'FamilyDB')}",
    ]
    for plan in plans.everything(conn):
        lines += ["BEGIN:VEVENT", f"UID:plan-{plan.id}@familydb", f"DTSTAMP:{_stamp(now)}"]
        if plan.all_day:
            first = date.fromisoformat(plan.start[:10])
            last = date.fromisoformat(plan.end[:10]) if plan.end else first
            lines.append(f"DTSTART;VALUE=DATE:{first:%Y%m%d}")
            lines.append(f"DTEND;VALUE=DATE:{last + timedelta(days=1):%Y%m%d}")  # exclusive
        else:
            start = parse_datetime(plan.start, tz)
            end = parse_datetime(plan.end, tz) if plan.end else start + timedelta(hours=2)
            lines.append(f"DTSTART:{_stamp(start)}")
            lines.append(f"DTEND:{_stamp(end)}")
        lines.append(f"SUMMARY:{_text(plan.title)}")
        if plan.location:
            lines.append(f"LOCATION:{_text(plan.location)}")
        if plan.notes:
            lines.append(f"DESCRIPTION:{_text(plan.notes)}")
        if plan.status == "tentative":
            lines.append("STATUS:TENTATIVE")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in _folded(line)) + "\r\n"


def _csv(header: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def ideas_csv(conn: sqlite3.Connection, kept_from: Collection[int] = ()) -> str:
    """Every idea not dropped, one a row, leaving out the presents kept from whoever asks."""
    rows = []
    for idea in ideas.list_all(conn):
        if idea.status == "dropped" or idea.id in kept_from:
            continue
        dates = " to ".join(d for d in (idea.happens_from, idea.happens_until) if d)
        rows.append(
            (
                idea.id,
                idea.title,
                idea.kind,
                idea.status,
                idea.location_name or "",
                ", ".join(idea.participants),
                ", ".join(idea.tags),
                idea.setting,
                "" if idea.cost_level is None else idea.cost_level,
                ideas.ages_text(idea) or "",
                dates,
                idea.times_done,
                "" if idea.avg_rating is None else f"{idea.avg_rating:g}",
                idea.created_at[:10],
                idea.description or "",
                idea.url or "",
            )
        )
    return _csv(IDEA_COLUMNS, rows)


def tasks_csv(conn: sqlite3.Connection) -> str:
    """Every thing to do, open, done or cancelled, one a row."""
    rows = []
    for task in tasks.everything(conn):
        repeats = f"every {task.repeat_every} {task.repeat_unit}" if task.repeats else ""
        rows.append(
            (
                task.id,
                task.title,
                task.status,
                task.owner or "everyone",
                task.due_at or "",
                task.reminder.remind_at if task.reminder else "",
                repeats,
                task.notes or "",
                task.created_at[:10],
            )
        )
    return _csv(TASK_COLUMNS, rows)


def everything(conn: sqlite3.Connection, now: datetime) -> dict[str, Any]:
    """The family's records, table by table, with nothing that is a secret or a way in."""
    dump: dict[str, Any] = {
        "familydb": __version__,
        "exported_at": now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    for table, columns in TABLES.items():
        rows = db.dump_table(conn, table)
        if table in KEPT_ONLY:
            rows = [{key: row.get(key) for key in columns} for row in rows]
        else:
            rows = [{k: v for k, v in row.items() if k not in columns} for row in rows]
        dump[table] = rows
    return dump


def everything_json(conn: sqlite3.Connection, now: datetime) -> str:
    return json.dumps(everything(conn, now), ensure_ascii=False, indent=1, sort_keys=True)


def write_all(
    conn: sqlite3.Connection, settings: Settings, folder: Path, now: datetime
) -> list[Path]:
    """All four into `folder` (`familydb export`), presents included: whoever runs it on the server
    can read the database anyway."""
    folder.mkdir(parents=True, exist_ok=True)
    written = {
        "plans.ics": plans_ics(conn, settings, now),
        "ideas.csv": ideas_csv(conn),
        "tasks.csv": tasks_csv(conn),
        "everything.json": everything_json(conn, now),
    }
    for name, text in written.items():
        (folder / name).write_text(text, "utf-8", newline="")
    return [folder / name for name in written]
