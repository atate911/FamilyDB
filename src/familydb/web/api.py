"""The API (docs/INTERFACE.md section 11): the family's pages as data, for a script on the page
or anything else signed in as a person. Read only, code only.

- `GET /api` says who is asking, what may be read, and the token a write needs.
- `GET /api/<path>` is any page of the family's at its own address (`/api/now` is Now, then
  `/api/eat`, `/api/week/2026-10-17`, `/api/place/57`…) as the page's own view-model
  (web/answers.py), with the box and the row. The page's permission holds, checked for the page.
  `?asked=<id>` on any of them carries what that message brought back, as the page shows it.
- `GET /api/find?q=` is search in the box.
- Writing is the page's own doors: `POST /api/say` (web/chat.py) sends a message, as the box
  does; `POST /api/act` (web/edits.py) is any of the page's forms by name, run by the form's own
  view, so it is the tool call the button makes. Each takes the token from `GET /api` in an
  `X-CSRF-Token` header, from this page's own origin.

The session cookie is the key, as for the page: there is no other way in.
"""

from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta
from typing import Any

from flask import Blueprint, Response, current_app, g, jsonify, request, url_for
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect

from familydb import happening, presents, roles
from familydb.app import App
from familydb.store import finds as find_store
from familydb.store import ideas as idea_store
from familydb.store import lists as list_store
from familydb.store import members as member_store
from familydb.store import plans as plan_store
from familydb.store import tasks as task_store
from familydb.web import answers, auth, views

bp = Blueprint("api", __name__, url_prefix="/api")

# The pages the API answers for: the family's, each at the address the page has. The back office's
# forms, the guide and editing by hand are pages, not answers.
PAGES = {
    "web.home": "Now",
    "go.about": "What about",
    "go.board": "The kitchen board",
    "chat.show": "The conversation",
    "web.restaurants": "Where should we eat?",
    "web.ideas": "What could we do?",
    "web.idea": "A place or an idea",
    "go.week": "This week",
    "go.day": "A day",
    "go.plan": "A plan",
    "web.edit_task": "A reminder",
    "web.tasks": "Every to-do",
    "web.wishes": "The kids, or my list",
    "web.happening_page": "Happening soon",
    "web.find": "One thing near home",
    "web.lists_page": "Lists",
    "go.did": "What we did",
    "go.outing": "One outing",
    "web.plans": "Plans as a list",
    "web.plans_month": "Plans as a month",
    "web.memory": "What Vera knows",
    "web.status": "Status",
}
# Addresses the API takes that are not the page's own: Now is /api/now.
ALIASES = {"now": "/"}
NOT_A_PAGE = "There is no page there."
NOT_YOURS = "That page is not yours to read."


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _error(words: str, status: int) -> tuple[Response, int]:
    return jsonify({"error": words}), status


@bp.get("")
def index() -> Response:
    """Who is asking, the pages they may read, and the token a write needs."""
    visitor = auth.visitor()
    readable = []
    for endpoint, title in PAGES.items():
        if auth.needed_for(endpoint, visitor) is None:
            readable.append({"endpoint": endpoint, "title": title})
    acts = []
    for rule in current_app.url_map.iter_rules():
        prefix, _, name = rule.endpoint.partition(".")
        if prefix == "edits" and name != "act" and auth.needed_for(rule.endpoint, visitor) is None:
            acts.append({"act": name, "takes": sorted(rule.arguments)})
    return jsonify(
        {
            "who": visitor.name,
            "role": visitor.member.role if visitor.member else None,
            "pages": readable,
            "read": "/api/<the page's address>, e.g. /api/now, /api/eat, /api/place/57",
            "find": url_for("api.find"),
            "say": url_for("chat.say"),
            "act": url_for("edits.act"),
            "acts": sorted(acts, key=lambda one: one["act"]),
            "csrf": auth.csrf_token(),
            "csrf_header": auth.CSRF_HEADER,
        }
    )


@bp.get("/<path:path>")
def page(path: str) -> Any:
    """Any page of the family's, at its own address, as data."""
    address = ALIASES.get(path, "/" + path)
    adapter = current_app.url_map.bind_to_environ(request.environ)
    try:
        rule, args = adapter.match(address, method="GET", return_rule=True)
    except (NotFound, MethodNotAllowed, RequestRedirect):
        return _error(NOT_A_PAGE, 404)
    if rule.endpoint not in PAGES:
        return _error(NOT_A_PAGE, 404)
    if auth.needed_for(rule.endpoint, auth.visitor()) is not None:
        return _error(NOT_YOURS, 403)
    # From here the request is the page's: its endpoint marks the row, its arguments its links.
    request.url_rule = rule
    request.view_args = args
    g.setdefault(answers.API, True)
    found = current_app.view_functions[rule.endpoint](**args)
    status = 200
    if isinstance(found, tuple):
        found, status = found[0], found[1]
    if isinstance(found, Response) and 300 <= found.status_code < 400:
        return jsonify({"redirect": found.location})
    if isinstance(found, Response) and found.mimetype != "application/json":
        return _error(NOT_A_PAGE, found.status_code if found.status_code >= 400 else 404)
    return found, status


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
