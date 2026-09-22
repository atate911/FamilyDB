"""Changing an idea, an outcome or a plan from the page.

The page does not know how to save anything. Every form here turns into one call to a tool in
`familydb.tools` — `add_idea`, `update_idea`, `record_outcome`, `create_event`, `delete_event` —
which is the same code the model calls when somebody asks for the same thing in chat. So a title
typed into a box is checked the way a title said in chat is checked, a duplicate is caught the
same way, the transaction is the tool's own, and a calendar that is not connected says so
instead of half-writing a plan. Nothing in this module reaches a table by itself.

What the forms cannot do is what the tools cannot do: a number that has been set (a cost level, a
duration) can be changed but not unset, because `update_idea` reads a missing field as "leave
this one alone". Text boxes can be emptied, since an empty box is sent as an empty value rather
than as a missing one.
"""

from __future__ import annotations

import json
import logging
from contextlib import closing
from typing import Any

from flask import Blueprint, Response, current_app, flash, redirect, request, session, url_for
from werkzeug.datastructures import MultiDict

from familydb.app import App
from familydb.store import members as member_store
from familydb.tools import ToolContext
from familydb.web import auth
from familydb.web.chat import WHO_KEY

log = logging.getLogger(__name__)

bp = Blueprint("edits", __name__)

# Flashed under this name so the settings page's own messages and these never get mixed up.
NOTICE = "edit"
SAVED_IDEA = "Saved #{id} {title}."
CHANGED_IDEA = "Changed #{id} {title}."
DUPLICATE = "There is already an idea called that: #{id}. Nothing was added."
RECORDED = "Recorded. #{id} is marked done."
SCHEDULED = "On the calendar: {title}."
CANCELLED = "Cancelled."
NEEDS_TITLE = "An idea needs a title."
NEEDS_KIND = "An idea needs a kind: restaurant, outing, trip, show…"
NOT_A_NUMBER = "{label} needs to be a number."
# Boxes an idea form sends every time, so emptying one clears it rather than leaving it be.
IDEA_TEXT = ("description", "location_name", "url")
# Boxes only sent when filled in, because the tool reads a missing one as "leave it alone".
IDEA_NUMBERS = (
    ("duration_min", "The shortest time"),
    ("duration_max", "The longest time"),
    ("lead_time_days", "The booking lead time"),
)


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def run(name: str, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Run one tool as whoever the form said was asking. Returns its result, or what went wrong.

    The tool owns its transaction, so a half-done change is not a thing that can happen here.
    A tool that is not available (no calendar) hands back a reason rather than an error, and it
    is shown as one: not being connected to Google is not a mistake anybody made.
    """
    app = _app()
    with closing(app.connect()) as conn:
        who = _remember(request.form.get("who", ""))
        ctx = ToolContext(
            conn=conn,
            settings=app.settings,
            clock=app.clock,
            member=member_store.find_by_name(conn, who) if who else None,
            calendar=app.calendar,
            weather=app.weather,
            geocoder=app.geocoder,
        )
        result = app.registry.dispatch(name, values, ctx)
    payload = json.loads(result.content)
    if result.is_error:
        return None, payload.get("error", "that did not work")
    if payload.get("available") is False:
        return None, payload.get("reason", "that is not set up yet")
    log.info("%s from the page by %s", name, auth.client_address())
    return payload, None


def _remember(who: str) -> str:
    """Who the form said was asking, kept for the next form and for the chat page."""
    who = who.strip()
    if who:
        session[WHO_KEY] = who
    return who or str(session.get(WHO_KEY, ""))


def _text(form: MultiDict[str, str], key: str) -> str:
    return form.get(key, "").strip()


def _list(form: MultiDict[str, str], key: str) -> list[str]:
    """A comma-separated box as a list, e.g. tags or who it is for."""
    return [part.strip() for part in form.get(key, "").split(",") if part.strip()]


def _numbers(form: MultiDict[str, str]) -> tuple[dict[str, int], str | None]:
    """The idea form's number boxes, or the first one that is not a number."""
    found: dict[str, int] = {}
    for key, label in IDEA_NUMBERS:
        given = _text(form, key)
        if not given:
            continue
        try:
            found[key] = int(given)
        except ValueError:
            return {}, NOT_A_NUMBER.format(label=label)
    return found, None


def idea_fields(form: MultiDict[str, str]) -> tuple[dict[str, Any], str | None]:
    """Everything an idea form says, in the shape `add_idea` and `update_idea` take."""
    title, kind = _text(form, "title"), _text(form, "kind").lower()
    if not title:
        return {}, NEEDS_TITLE
    if not kind:
        return {}, NEEDS_KIND
    numbers, complaint = _numbers(form)
    if complaint:
        return {}, complaint
    values: dict[str, Any] = {
        "title": title,
        "kind": kind,
        "participants": _list(form, "participants"),
        "tags": _list(form, "tags"),
        "seasons": form.getlist("seasons"),
        "setting": _text(form, "setting") or "either",
        "weather": _text(form, "weather") or "any",
        "needs_booking": bool(form.get("needs_booking")),
        **{key: _text(form, key) for key in IDEA_TEXT},
        **numbers,
    }
    cost = _text(form, "cost_level")
    if cost:
        values["cost_level"] = int(cost)  # the form offers a fixed list, so this cannot fail
    return values, None


def _back(target: str, **values: Any) -> Response:
    return redirect(url_for(target, **values))


def _say(message: str) -> None:
    flash(message, NOTICE)


@bp.post("/ideas/new")
def add_idea() -> Response:
    """Save an idea typed into the page, through the same tool chat uses."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.new_idea")
    values, complaint = idea_fields(request.form)
    if complaint:
        _say(complaint)
        return _back("web.new_idea")
    result, complaint = run("add_idea", values)
    if result is None:
        _say(complaint or "")
        return _back("web.new_idea")
    if "duplicate_of" in result:
        _say(DUPLICATE.format(id=result["duplicate_of"]))
        return _back("web.idea", idea_id=result["duplicate_of"])
    _say(SAVED_IDEA.format(id=result["id"], title=result["title"]))
    return _back("web.idea", idea_id=result["id"])


@bp.post("/idea/<int:idea_id>/edit")
def edit_idea(idea_id: int) -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.edit_idea", idea_id=idea_id)
    values, complaint = idea_fields(request.form)
    if complaint:
        _say(complaint)
        return _back("web.edit_idea", idea_id=idea_id)
    status = _text(request.form, "status")
    if status:
        values["status"] = status
    result, complaint = run("update_idea", {**values, "id": idea_id})
    if result is None:
        _say(complaint or "")
        return _back("web.edit_idea", idea_id=idea_id)
    _say(CHANGED_IDEA.format(id=result["id"], title=result["title"]))
    return _back("web.idea", idea_id=idea_id)


@bp.post("/idea/<int:idea_id>/status")
def set_status(idea_id: int) -> Response:
    """Drop an idea, or bring a dropped one back. One button, no form to fill in."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.idea", idea_id=idea_id)
    result, complaint = run("update_idea", {"id": idea_id, "status": _text(request.form, "status")})
    if result is None:
        _say(complaint or "")
    else:
        _say(CHANGED_IDEA.format(id=result["id"], title=result["title"]))
    return _back("web.idea", idea_id=idea_id)


@bp.post("/idea/<int:idea_id>/outcome")
def record_outcome(idea_id: int) -> Response:
    """How it went. The tool marks the idea done and keeps its average up to date."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.idea", idea_id=idea_id)
    form = request.form
    values: dict[str, Any] = {"idea_id": idea_id, "notes": _text(form, "notes") or None}
    if happened := _text(form, "happened_on"):
        values["happened_on"] = happened
    if rating := _text(form, "rating"):
        values["rating"] = int(rating)  # a fixed list of scores, so this cannot fail
    repeat = _text(form, "would_repeat")
    if repeat in {"yes", "no"}:
        values["would_repeat"] = repeat == "yes"
    _, complaint = run("record_outcome", values)
    _say(complaint or RECORDED.format(id=idea_id))
    return _back("web.idea", idea_id=idea_id)


@bp.post("/plans/new")
def add_plan() -> Response:
    """Put something on the shared calendar. Needs Google Calendar connected, and says so."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.plans")
    form = request.form
    idea_id = _text(form, "idea_id")
    back = ("web.idea", {"idea_id": int(idea_id)}) if idea_id else ("web.plans", {})
    all_day = bool(form.get("all_day"))
    start = _text(form, "start")
    values: dict[str, Any] = {
        "title": _text(form, "title"),
        # An all-day plan keeps only the date: the box offers a time whether or not one matters.
        "start": start[:10] if all_day else start,
        "all_day": all_day,
        "location": _text(form, "location") or None,
        "notes": _text(form, "notes") or None,
    }
    if idea_id:
        values["idea_id"] = int(idea_id)
    result, complaint = run("create_event", values)
    if result is None:
        _say(complaint or "")
    else:
        _say(SCHEDULED.format(title=result["plan"]["title"]))
    return _back(back[0], **back[1])


@bp.post("/plan/<int:plan_id>/cancel")
def cancel_plan(plan_id: int) -> Response:
    """Take a plan off the calendar. The idea goes back to being an idea."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.plans")
    _, complaint = run("delete_event", {"plan_id": plan_id})
    _say(complaint or CANCELLED)
    return _back("web.plans")
