"""The pages. Every view reads; nothing here writes to the database."""

from __future__ import annotations

from contextlib import closing
from datetime import timedelta
from typing import Any

from flask import Blueprint, Response, abort, current_app, render_template, request, session

from familydb.app import App
from familydb.availability import calendar_available
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import outcomes as outcome_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.store.ideas import KIND_SUGGESTIONS
from familydb.web import status as status_page
from familydb.web import views
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
        asking = _who(conn)
    return render_template(
        "idea.html",
        idea=record,
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


@bp.get("/plans")
def plans() -> str:
    """What is on the family calendar: the next three months, then the past month."""
    app = _app()
    today = app.clock.today()
    with closing(app.connect()) as conn:
        # list_between excludes its end, and a date sorts before that day's timed plans, so the
        # exclusive bound is the day after the last one we want to show.
        upcoming = plan_store.list_between(
            conn, today.isoformat(), (today + timedelta(days=PLANS_AHEAD_DAYS + 1)).isoformat()
        )
        recent = plan_store.list_between(
            conn, (today - timedelta(days=PLANS_BEHIND_DAYS)).isoformat(), today.isoformat()
        )
        titles = {row.id: row.title for row in idea_store.list_all(conn, include_dropped=True)}
        asking = _who(conn)
    return render_template(
        "plans.html",
        today=today.isoformat(),
        can_schedule=calendar_available(_app().settings),
        **asking,
        upcoming=[views.plan_row(plan, today) for plan in upcoming],
        recent=[views.plan_row(plan, today) for plan in reversed(recent)],
        titles=titles,
        ahead=PLANS_AHEAD_DAYS,
    )
