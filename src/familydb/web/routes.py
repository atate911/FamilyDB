"""The pages. Every view reads; nothing here writes to the database."""

from __future__ import annotations

from contextlib import closing
from typing import Any

from flask import Blueprint, Response, abort, current_app, render_template, request

from familydb.app import App
from familydb.store import ideas as idea_store
from familydb.store import outcomes as outcome_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.web import views

bp = Blueprint("web", __name__)

LIST_LIMIT = 200
STATUSES = ("idea", "planned", "done", "dropped")


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _choices(rows: list[Any]) -> tuple[list[str], list[str]]:
    """The kinds and participants actually in use, so the filters offer only real options."""
    kinds = sorted({row.kind for row in rows})
    people = sorted({name for row in rows for name in row.participants})
    return kinds, people


@bp.get("/healthz")
def healthz() -> Response:
    """A plain-text liveness check for a monitor or a reverse proxy. No password needed."""
    return Response("ok\n", mimetype="text/plain")


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
        rows=[views.idea_row(idea) for idea in found],
        kinds=kinds,
        people=people,
        statuses=STATUSES,
        selected={"q": query, "kind": kind, "status": status, "who": who},
        filtered=filtered,
        limit=LIST_LIMIT,
    )


@bp.get("/idea/<int:idea_id>")
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
        row=views.idea_row(record),
        setting=views.SETTINGS.get(record.setting, record.setting),
        weather=views.WEATHER.get(record.weather),
        place=views.place_panel(place, now, settings.place_stale_days),
        outcomes=[views.outcome_row(o) for o in reversed(outcomes)],
        plans=[views.plan_row(p, today) for p in reversed(plans)],
    )
