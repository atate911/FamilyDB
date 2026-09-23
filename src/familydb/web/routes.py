"""The pages. Every view reads; nothing here writes to the database."""

from __future__ import annotations

import calendar as month_calendar
from contextlib import closing
from datetime import date, datetime, time, timedelta
from typing import Any

from flask import Blueprint, Response, abort, current_app, render_template, request

from familydb.app import App
from familydb.calendar_sync import event_changes
from familydb.store import ideas as idea_store
from familydb.store import outcomes as outcome_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.web import status as status_page
from familydb.web import views

bp = Blueprint("web", __name__)

LIST_LIMIT = 200
MAX_ID = 2**63 - 1  # beyond this SQLite raises rather than simply finding nothing
STATUSES = ("idea", "planned", "done", "dropped")
RESTAURANT_KIND = "restaurant"
PLANS_AHEAD_DAYS = 90
PLANS_BEHIND_DAYS = 30


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _saved_plans(conn, first, last, tz):
    # Include spanning events and a day's margin for stored UTC/foreign offsets.
    rows = conn.execute(
        "SELECT * FROM plans WHERE status != 'cancelled' AND start < ? "
        "AND coalesce(end,start) >= ? ORDER BY start",
        ((last + timedelta(days=1)).isoformat(), (first - timedelta(days=1)).isoformat()),
    )
    local = [views.local_plan(plan_store.Plan.from_row(row), tz) for row in rows]
    return sorted(
        (p for p in local if views.plan_overlaps(p, first, last, tz)), key=lambda p: p.start
    )


def _choices(rows: list[Any]) -> tuple[list[str], list[str]]:
    """The kinds and participants actually in use, so the filters offer only real options."""
    kinds = sorted({row.kind for row in rows})
    people = sorted({name for row in rows for name in row.participants})
    return kinds, people


@bp.get("/healthz")
def healthz() -> Response:
    """A plain-text liveness check for a monitor or a reverse proxy. No password needed."""
    return Response("ok\n", mimetype="text/plain")


@bp.get("/status")
def status() -> str:
    """Is it working, and what is it costing us? A handful of small queries, no model call."""
    app = _app()
    with closing(app.connect()) as conn:
        return render_template("status.html", **status_page.status(app, conn))


@bp.get("/home")
def home() -> str:
    app = _app()
    with closing(app.connect()) as conn:
        saved = idea_store.list_all(conn)
        upcoming = _saved_plans(
            conn,
            app.clock.today(),
            app.clock.today() + timedelta(days=PLANS_AHEAD_DAYS + 1),
            app.settings.tzinfo,
        )[:4]
    return render_template(
        "home.html",
        today=app.clock.today().strftime("%A, %B %d"),
        ideas=[views.idea_row(row, app.settings.tzinfo) for row in saved[-4:][::-1]],
        idea_count=len(saved),
        restaurant_count=sum(row.kind == "restaurant" for row in saved),
        plans=[views.plan_row(row, app.clock.today()) for row in upcoming],
    )


@bp.get("/calendar")
def calendar() -> str:
    app = _app()
    today = app.clock.today()
    try:
        month = date.fromisoformat(request.args.get("month", today.strftime("%Y-%m")) + "-01")
        if not 1970 <= month.year <= 2100:
            raise ValueError
    except ValueError:
        abort(400)
    weeks = month_calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month)
    first, last = weeks[0][0], weeks[-1][-1] + timedelta(days=1)
    with closing(app.connect()) as conn:
        stored = _saved_plans(conn, first, last, app.settings.tzinfo)
        owned = {
            row["google_event_id"]: plan_store.Plan.from_row(row)
            for row in conn.execute(
                "SELECT * FROM plans WHERE calendar_id = ?", (app.settings.google_calendar_id,)
            )
        }
    note = "Saved family plans. Connect Google Calendar to see the full calendar."
    if app.calendar is not None:
        try:
            events = app.calendar.list_events(
                datetime.combine(first, time.min, app.clock.tz),
                datetime.combine(last, time.min, app.clock.tz),
            )
            stored = []
            for event in events:
                local = owned.get(event.id)
                stored.append(
                    local.model_copy(update=event_changes(event))
                    if local
                    else plan_store.Plan(id=0, created_at="", updated_at="", **event_changes(event))
                )
            note = (
                "Live Google Calendar. "
                "Events added outside FamilyDB are managed in Google Calendar."
            )
        except Exception:
            note = "Google Calendar is unavailable. Showing saved plans; dates may be outdated."
    days = []
    stored = [views.local_plan(p, app.settings.tzinfo) for p in stored]
    for week in weeks:
        cells = []
        for day in week:
            events = []
            for plan in stored:
                if views.plan_overlaps(plan, day, day + timedelta(days=1), app.settings.tzinfo):
                    events.append(plan)
            cells.append({"date": day, "events": events, "current": day.month == month.month})
        days.append(cells)
    return render_template(
        "calendar.html",
        weeks=days,
        month=month,
        today=today,
        note=note,
        previous=(month - timedelta(days=1)).strftime("%Y-%m"),
        next=(month + timedelta(days=32)).strftime("%Y-%m"),
    )


@bp.get("/")
def ideas() -> str:
    app = _app()
    query = request.args.get("q", "").strip()
    kind = request.args.get("kind", "").strip()
    status = request.args.get("status", "").strip()
    who = request.args.get("who", "").strip()
    with closing(app.connect()) as conn:
        found = idea_store.search(
            conn,
            text=query or None,
            kind=kind or None,
            status=status if status in STATUSES else None,
            participant=who or None,
            limit=LIST_LIMIT,
        )
        kinds, people = _choices(idea_store.list_all(conn, include_dropped=True))
    filtered = bool(query or kind or status or who)
    return render_template(
        "ideas.html",
        rows=[views.idea_row(idea, app.settings.tzinfo) for idea in found],
        kinds=kinds,
        people=people,
        statuses=STATUSES,
        selected={"q": query, "kind": kind, "status": status, "who": who},
        filtered=filtered,
        limit=LIST_LIMIT,
    )


@bp.get(f"/idea/<int(max={MAX_ID}):idea_id>")
def idea(idea_id: int) -> str:
    app = _app()
    settings = app.settings
    now = app.clock.now()
    today = app.clock.today()
    with closing(app.connect()) as conn:
        record = idea_store.get(conn, idea_id)
        if record is None:
            abort(404)
        place = place_store.get(conn, record.place_id) if record.place_id else None
        outcomes = outcome_store.list_for_idea(conn, idea_id)
        plans = plan_store.for_idea(conn, idea_id)
    return render_template(
        "idea.html",
        idea=record,
        row=views.idea_row(record, settings.tzinfo),
        setting=views.SETTINGS.get(record.setting, record.setting),
        weather=views.WEATHER.get(record.weather),
        place=views.place_panel(place, now, settings.place_stale_days),
        outcomes=[views.outcome_row(o) for o in reversed(outcomes)],
        plans=[
            views.plan_row(views.local_plan(p, settings.tzinfo), today) for p in reversed(plans)
        ],
    )


@bp.get("/restaurants")
def restaurants() -> str:
    """The restaurant list on its own, each card linking out to where you can read more."""
    app = _app()
    now = app.clock.now()
    today = app.clock.today()
    stale_days = app.settings.place_stale_days
    with closing(app.connect()) as conn:
        found = idea_store.search(conn, kind=RESTAURANT_KIND, limit=LIST_LIMIT)
        cards = [
            views.restaurant_card(
                idea,
                place_store.get(conn, idea.place_id) if idea.place_id else None,
                today,
                now,
                stale_days,
            )
            for idea in found
        ]
    return render_template("restaurants.html", cards=cards)


@bp.get("/plans")
def plans() -> str:
    """What is on the family calendar: the next three months, then the past month."""
    app = _app()
    today = app.clock.today()
    with closing(app.connect()) as conn:
        upcoming = _saved_plans(
            conn, today, today + timedelta(days=PLANS_AHEAD_DAYS + 1), app.settings.tzinfo
        )
        recent = [
            p
            for p in _saved_plans(
                conn, today - timedelta(days=PLANS_BEHIND_DAYS), today, app.settings.tzinfo
            )
            if p not in upcoming
        ]
        titles = {row.id: row.title for row in idea_store.list_all(conn, include_dropped=True)}
        owned = {
            r["google_event_id"]: plan_store.Plan.from_row(r)
            for r in conn.execute(
                "SELECT * FROM plans WHERE calendar_id = ?", (app.settings.google_calendar_id,)
            )
        }
    calendar_note = "Saved bot plans only; Google Calendar is not connected."
    if app.calendar is not None:
        try:
            events = app.calendar.list_events(
                datetime.combine(today - timedelta(days=PLANS_BEHIND_DAYS), time.min, app.clock.tz),
                datetime.combine(
                    today + timedelta(days=PLANS_AHEAD_DAYS + 1), time.min, app.clock.tz
                ),
            )
            live = []
            for event in events:
                local = owned.get(event.id)
                if local is not None:
                    live.append(local.model_copy(update=event_changes(event)))
                else:
                    live.append(
                        plan_store.Plan(id=0, created_at="", updated_at="", **event_changes(event))
                    )
            live = [
                views.local_plan(p, app.settings.tzinfo) for p in live if p.status != "cancelled"
            ]
            upcoming = [
                p
                for p in live
                if views.plan_overlaps(
                    p, today, today + timedelta(days=PLANS_AHEAD_DAYS + 1), app.settings.tzinfo
                )
            ]
            recent = [p for p in live if p not in upcoming]
            calendar_note = "Live Google Calendar, including events added outside FamilyDB."
        except Exception:
            calendar_note = (
                "Google Calendar could not be reached. "
                "Showing saved bot plans; dates may be outdated."
            )
    return render_template(
        "plans.html",
        upcoming=[views.plan_row(plan, today) for plan in upcoming],
        recent=[views.plan_row(plan, today) for plan in reversed(recent)],
        titles=titles,
        ahead=PLANS_AHEAD_DAYS,
        calendar_note=calendar_note,
    )
