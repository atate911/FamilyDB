"""Search in the box (docs/INTERFACE.md sections 3 and 11): `GET /api/find?q=`, read by ask.js
as the box is typed in. Code only, no model call. A script that is not signed in is told so in
JSON rather than sent to the sign-in form."""

from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta

from flask import Blueprint, Response, current_app, jsonify, request, url_for

from familydb import happening, presents
from familydb.app import App
from familydb.base import roles
from familydb.store import finds as find_store
from familydb.store import ideas as idea_store
from familydb.store import lists as list_store
from familydb.store import members as member_store
from familydb.store import plans as plan_store
from familydb.store import tasks as task_store
from familydb.web import auth, views

bp = Blueprint("api", __name__, url_prefix="/api")


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


# -- search in the box ---------------------------------------------------------------------------

# At most this many matches, and only once this much is typed.
FIND_MOST = 8
FIND_SHORTEST = 2
# The plans it looks at: a month back, four months on.
FIND_BACK_DAYS = 31
FIND_AHEAD_DAYS = 122
FIND_LISTED = 200


@bp.get("/find")
def find() -> Response:
    """Search in the box (docs/INTERFACE.md sections 3 and 11): what the family has by name, as
    the box is typed in and before anything is sent. Code only, no model call: ideas, plans of the
    weeks around today, open reminders, the kids, the lists and what is on near home, each with
    where it opens; what a kid may not see, and a present kept from whoever asks, never."""
    app = _app()
    today = app.clock.today()
    visitor = auth.visitor()
    grown_up = visitor.may("browse")
    words = " ".join(request.args.get("q", "").casefold().split())[:60]
    found: list[dict[str, str]] = []

    def hit(text: str | None) -> bool:
        folded = (text or "").casefold()
        return all(word in folded for word in words.split())

    if len(words) >= FIND_SHORTEST:
        with closing(app.connect()) as conn:
            kept = presents.kept_ids(conn, visitor.member)
            people = member_store.list_all(conn)
            slots = views.slot_map(people)
            for idea in idea_store.list_all(conn):
                if idea.id not in kept and hit(idea.title):
                    found.append(
                        {
                            "label": idea.title,
                            "kind": views.kind_name(idea.kind),
                            "href": url_for("web.idea", idea_id=idea.id),
                        }
                    )
            plans = plan_store.list_between(
                conn,
                (today - timedelta(days=FIND_BACK_DAYS)).isoformat(),
                (today + timedelta(days=FIND_AHEAD_DAYS)).isoformat(),
            )
            for plan in plans:
                if plan.idea_id in kept or not hit(plan.title):
                    continue
                idea = idea_store.get(conn, plan.idea_id) if plan.idea_id else None
                if not grown_up and not views.names_in(
                    views.people_for(idea, slots), visitor.member
                ):
                    continue
                found.append(
                    {
                        "label": plan.title,
                        "kind": f"Plan, {views.day_short(date.fromisoformat(plan.start[:10]))}",
                        "href": url_for("go.plan", plan_id=plan.id),
                    }
                )
            if visitor.may("change") or visitor.may("own_tasks"):
                own = None if grown_up or visitor.member is None else visitor.member.id
                tasks = task_store.list_all(conn, status="open", owner_id=own)
                for task in presents.visible_tasks(conn, tasks, visitor.member):
                    if hit(task.title):
                        found.append(
                            {
                                "label": task.title,
                                "kind": "Reminder",
                                "href": url_for("web.edit_task", task_id=task.id)
                                if visitor.may("change")
                                else url_for("go.week"),
                            }
                        )
            if visitor.may("decide"):
                for kid in people:
                    wishing = roles.may(kid.role, "wish") and not roles.may(kid.role, "decide")
                    if kid.active and wishing and hit(kid.display_name):
                        found.append(
                            {
                                "label": kid.display_name,
                                "kind": "Kid",
                                "href": url_for("web.wishes", name=views.slug(kid.display_name)),
                            }
                        )
            if visitor.may("change"):
                for name in list_store.names(conn):
                    if hit(views.list_title(name)):
                        found.append(
                            {
                                "label": views.list_title(name),
                                "kind": "List",
                                "href": url_for("web.lists_page", name=name),
                            }
                        )
            if grown_up:
                listed = find_store.upcoming(
                    conn,
                    start=today,
                    end=today + timedelta(days=happening.HORIZON_DAYS),
                    limit=FIND_LISTED,
                )
                for one in listed:
                    if hit(one.title):
                        found.append(
                            {
                                "label": one.title,
                                "kind": "Near home",
                                "href": url_for("web.find", find_id=one.id),
                            }
                        )
    return jsonify({"q": words, "found": found[:FIND_MOST]})
