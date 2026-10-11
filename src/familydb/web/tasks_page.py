"""The things to do: the list, and the form for one task or reminder."""

from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta
from typing import Any

from flask import (
    abort,
    request,
)

from familydb import personas, presents
from familydb.base.dates import utc_iso
from familydb.store import calls
from familydb.store import members as member_store
from familydb.store import tasks as task_store
from familydb.web import (
    auth,
    chat,
    views,
)
from familydb.web.answers import answer
from familydb.web.pages import bp, familydb_app

# A kid's To do page keeps what she ticked off this long, with a way to undo it.
DONE_LATELY_DAYS = 7


def _own_only() -> int | None:
    """Whose tasks this visitor sees: their own, unless they may browse the household's."""
    visitor = auth.visitor()
    if visitor.may("browse") or visitor.member is None:
        return None
    return visitor.member.id


@bp.get("/tasks")
def tasks() -> str:
    app = familydb_app()
    status = request.args.get("status", "open")
    if status not in {"open", "done", "cancelled", "all"}:
        abort(400)
    # A kid gets a plain checklist of her own open ones (docs/STYLE.md, "A kid's screen").
    simple = not auth.visitor().may("browse")
    if simple:
        status = "open"
    visitor = auth.visitor()
    with closing(app.connect()) as conn:
        rows = presents.visible_tasks(
            conn,
            task_store.list_all(
                conn,
                status=status,
                query="" if simple else request.args.get("q", ""),
                owner_id=_own_only(),
            ),
            visitor.member,
        )
        open_count = (
            len(rows) if status == "open" and not request.args.get("q") else _open_count(conn)
        )
        people = member_store.list_all(conn)
        creators = task_store.creators(conn, [task.id for task in rows]) if simple else {}
        done_lately = (
            presents.visible_tasks(
                conn,
                task_store.list_all(conn, status="done", owner_id=_own_only()),
                visitor.member,
            )
            if simple
            else []
        )
    today = app.clock.today()
    tz = app.settings.tzinfo
    slots = views.slot_map(people)
    shown = [
        views.todo_page_row(
            task,
            tz,
            today,
            slots,
            kid=simple,
            nudging=app.settings.task_nudges,
            creator=creators.get(task.id),
            me=visitor.name,
        )
        for task in rows
    ]
    groups = _todo_groups(shown) if status == "open" and not simple else []
    since = utc_iso(app.clock.now() - timedelta(days=DONE_LATELY_DAYS))
    lately = [
        views.todo_page_row(task, tz, today, slots, kid=True, me=visitor.name)
        for task in done_lately
        if task.updated_at >= since
    ]
    return answer(
        "tasks.html",
        simple=simple,
        rows=shown,
        lately=lately,
        groups=groups,
        open_count=open_count,
        late_count=sum(1 for row in shown if row["late"]) if status == "open" else None,
        repeat_options=views.REPEATS,
        people=[views.person_of(p.display_name, slots) for p in people],
        me=visitor.name,
        status=status,
        zone=app.settings.tz,
        query=request.args.get("q", ""),
    )


def _open_count(conn: Any) -> int:
    found = task_store.list_all(conn, status="open", owner_id=_own_only())
    return len(presents.visible_tasks(conn, found, auth.visitor().member))


def _todo_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Open to-dos in the order a person works through them: what is late, what has a day, what
    has none."""
    parts = (
        ("Overdue", "late", [row for row in rows if row["late"]]),
        ("Coming up", "", [row for row in rows if row["dated"] and not row["late"]]),
        ("No date", "", [row for row in rows if not row["dated"]]),
    )
    return [{"title": title, "tone": tone, "rows": found} for title, tone, found in parts if found]


@bp.get("/task/<int(max=9223372036854775807):task_id>/edit")
@bp.get("/reminder/<int(max=9223372036854775807):task_id>")
def edit_task(task_id: int) -> str:
    """A reminder's own page (docs/INTERFACE.md section 5): when or on what condition, whose,
    how it repeats, where it is sent, in words; and the form to change all of it by hand."""
    app = familydb_app()
    with closing(app.connect()) as conn:
        task = task_store.get(conn, task_id)
        if task is None or not presents.visible_tasks(conn, [task], auth.visitor().member):
            abort(404)
        people = member_store.list_all(conn)
        made_by = task_store.creators(conn, [task.id]).get(task.id)
        changed = calls.last_change(conn, task_id=task.id)
        box = chat.page_box(
            app,
            conn,
            people,
            prompt=chat.ITEM_PROMPT,
            scope={"label": task.title, "text": f"About the reminder {task.title}:"},
        )
    box["starters"] = views.task_starters(task, app.clock.today())
    tz = app.settings.tzinfo
    slots = views.slot_map(people)
    row = views.task_row(task, tz, app.clock.today(), nudging=app.settings.task_nudges)
    row["changed"] = views.changed_line(changed, tz, assistant=personas.active(app.settings).name)
    return answer(
        "task_form.html",
        task=task,
        row=row,
        words=views.todo_row(task, tz, app.clock.today(), slots),
        added=views.day_short(date.fromisoformat(views.local_day(task.created_at, tz))),
        made_by=made_by,
        people=[views.person_of(p.display_name, slots) for p in people],
        owner=views.person_of(task.owner, slots) if task.owner else None,
        zone=app.settings.tz,
        presses=chat.PAGE_BUTTONS,
    )
