"""The pages. Every view reads; nothing here writes to the database."""

from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta
from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from familydb.app import App
from familydb.availability import calendar_available
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import messages as message_store
from familydb.store import outcomes as outcome_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.store import tasks as task_store
from familydb.store.ideas import KIND_SUGGESTIONS
from familydb.web import agenda, views
from familydb.web import status as status_page
from familydb.web.chat import WHO_KEY

bp = Blueprint("web", __name__)

LIST_LIMIT = 200
MAX_ID = 2**63 - 1  # beyond this SQLite raises rather than simply finding nothing
STATUSES = ("idea", "planned", "done", "dropped")
SETTINGS = ("either", "indoor", "outdoor")
WEATHERS = ("any", "dry", "warm", "snow")
SEASONS = ("spring", "summer", "autumn", "winter")
COSTS = ((0, "free"), (1, "cheap"), (2, "moderate"), (3, "pricey"), (4, "expensive"))
RATINGS = tuple(range(10, 0, -1))
RESTAURANT_KIND = "restaurant"
FILTERS = ("q", "kind", "status", "who")
HOME_AHEAD_DAYS = 60
HOME_PLANS = 5
HOME_IDEAS = 4
WEEKEND_QUESTION = "What should we do this weekend?"
PLANS_AHEAD_DAYS = 90
PLANS_BEHIND_DAYS = 30


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _who(conn: Any) -> dict[str, Any]:
    """What every form on a page needs to say who is doing this: the family, and who last did."""
    return {
        "family": [member.display_name for member in member_store.list_all(conn)],
        "who": session.get(WHO_KEY),
    }


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


@bp.get("/")
def home() -> Response | str:
    """What is coming up, what was added lately, and one tap to ask or add something."""
    if any(request.args.get(key) for key in FILTERS):
        # The ideas list used to live here; a bookmarked search should still find it.
        return redirect(url_for("web.ideas", **request.args))
    app = _app()
    today = app.clock.today()
    with closing(app.connect()) as conn:
        seen = agenda.read(app, conn, today, today + timedelta(days=HOME_AHEAD_DAYS))
        everything = idea_store.list_all(conn)
        unfinished = status_page.setup_steps(app, conn)
    coming = [entry for entry in seen.entries if entry.days()[-1] >= today][:HOME_PLANS]
    newest = sorted(everything, key=lambda idea: idea.created_at, reverse=True)[:HOME_IDEAS]
    return render_template(
        "home.html",
        today=views.day_text(today.isoformat()),
        coming=[views.entry_row(entry, today) for entry in coming],
        blips=views.radar_blips(coming, today),
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
        ideas=[views.idea_row(idea, app.settings.tzinfo) for idea in newest],
        idea_count=len(everything),
        restaurant_count=sum(1 for idea in everything if idea.kind == RESTAURANT_KIND),
        weekend_question=WEEKEND_QUESTION,
        setup=unfinished,
    )


@bp.get("/ideas")
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
        capture_people = member_store.list_all(conn)
    filtered = bool(query or kind or status or who)
    return render_template(
        "ideas.html",
        capture_people=capture_people,
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
        original = (
            message_store.get(conn, record.source_message_id) if record.source_message_id else None
        )
        place = place_store.get(conn, record.place_id) if record.place_id else None
        outcomes = outcome_store.list_for_idea(conn, idea_id)
        plans = plan_store.for_idea(conn, idea_id)
        asking = _who(conn)
    return render_template(
        "idea.html",
        idea=record,
        original_message=message_store.as_said(original.text) if original else None,
        today=today.isoformat(),
        ratings=RATINGS,
        can_schedule=calendar_available(settings),
        **asking,
        row=views.idea_row(record, settings.tzinfo),
        setting=views.SETTINGS.get(record.setting, record.setting),
        weather=views.WEATHER.get(record.weather),
        place=views.place_panel(place, now, settings.place_stale_days),
        outcomes=[views.outcome_row(o) for o in reversed(outcomes)],
        plans=[views.plan_row(p, today) for p in reversed(plans)],
    )


def _idea_form(record: Any = None) -> str:
    """The boxes for adding or changing an idea. Drawing it is reading; `edits.py` saves it."""
    app = _app()
    with closing(app.connect()) as conn:
        kinds = sorted({row.kind for row in idea_store.list_all(conn, include_dropped=True)})
        family = [member.display_name for member in member_store.list_all(conn)]
    return render_template(
        "idea_form.html",
        idea=record,
        revision=idea_store.revision(record) if record else None,
        kinds=sorted(set(kinds) | set(KIND_SUGGESTIONS)),
        statuses=STATUSES,
        settings=SETTINGS,
        weathers=WEATHERS,
        seasons=SEASONS,
        costs=COSTS,
        family=family,
        who=session.get(WHO_KEY),
    )


@bp.get("/ideas/new")
def new_idea() -> str:
    return _idea_form()


@bp.get(f"/idea/<int(max={MAX_ID}):idea_id>/edit")
def edit_idea(idea_id: int) -> str:
    with closing(_app().connect()) as conn:
        record = idea_store.get(conn, idea_id)
    if record is None:
        abort(404)
    return _idea_form(record)


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


def _month(asked: str | None, today: date) -> date:
    """The first of the month asked for as YYYY-MM, or of this one. Anything else is a 404."""
    if not asked:
        return today.replace(day=1)
    try:
        first = date.fromisoformat(f"{asked}-01")
    except ValueError:
        abort(404)
    if not 2000 <= first.year <= 2100:
        abort(404)
    return first


@bp.get("/plans")
def plans() -> str:
    """What is on: the next three months, then the past month, as a list."""
    app = _app()
    today = app.clock.today()
    with closing(app.connect()) as conn:
        seen = agenda.read(
            app,
            conn,
            today - timedelta(days=PLANS_BEHIND_DAYS),
            today + timedelta(days=PLANS_AHEAD_DAYS),
        )
        titles = {row.id: row.title for row in idea_store.list_all(conn, include_dropped=True)}
        asking = _who(conn)
    # Something that ends today or later is still to come, or going on now.
    upcoming = [entry for entry in seen.entries if entry.days()[-1] >= today]
    recent = [entry for entry in seen.entries if entry.days()[-1] < today]
    return render_template(
        "plans.html",
        upcoming=[views.entry_row(entry, today) for entry in upcoming],
        recent=[views.entry_row(entry, today) for entry in reversed(recent)],
        titles=titles,
        ahead=PLANS_AHEAD_DAYS,
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
        today=today.isoformat(),
        can_schedule=calendar_available(app.settings),
        **asking,
    )


@bp.get("/plans/month")
def plans_month() -> str:
    """One month as a calendar, or as a list of its busy days on a screen too narrow for one."""
    app = _app()
    today = app.clock.today()
    first = _month(request.args.get("month"), today)
    weeks_first = first - timedelta(days=first.weekday())
    last_day = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    weeks_last = last_day + timedelta(days=6 - last_day.weekday())
    with closing(app.connect()) as conn:
        seen = agenda.read(app, conn, weeks_first, weeks_last)
    previous = (first - timedelta(days=1)).replace(day=1)
    following = last_day + timedelta(days=1)
    weeks = views.month_weeks(seen.entries, first, today)
    return render_template(
        "plans_month.html",
        month=f"{first:%B %Y}",
        weeks=weeks,
        busy_days=[day for week in weeks for day in week if day["current"] and day["entries"]],
        previous=f"{previous:%Y-%m}",
        following=f"{following:%Y-%m}",
        this_month=first == today.replace(day=1),
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
    )


@bp.get("/tasks")
def tasks() -> str:
    app = _app()
    status = request.args.get("status", "open")
    if status not in {"open", "done", "cancelled", "all"}:
        abort(400)
    with closing(app.connect()) as conn:
        rows = task_store.list_all(conn, status=status, query=request.args.get("q", ""))
        people = member_store.list_all(conn)
    return render_template(
        "tasks.html",
        rows=[views.task_row(task, app.settings.tzinfo) for task in rows],
        people=people,
        status=status,
        zone=app.settings.tz,
        query=request.args.get("q", ""),
    )
