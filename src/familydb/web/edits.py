"""The forms that change an idea, an outcome, a plan, a task, a memory or a wish. Each is one
call to the tool the model would call (`run`), so the same checks, transaction and unavailable
reasons apply, and nothing here reaches a table.

What the tools cannot do the forms cannot: a set number (a cost level, a duration) can be changed
but not unset, because `update_idea` reads a missing field as "leave it alone". Text boxes can be
emptied, since an empty box is sent as an empty value."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from contextlib import closing
from typing import Any

from flask import Blueprint, Response, current_app, flash, redirect, request, session, url_for
from werkzeug.datastructures import MultiDict

from familydb import buttons, presents
from familydb.app import App
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import outcomes as outcome_store
from familydb.tools import ToolContext
from familydb.web import auth, views
from familydb.web.chat import WHO_KEY
from familydb.web.once import once

log = logging.getLogger(__name__)

bp = Blueprint("edits", __name__)

# The flash category, apart from the settings page's.
NOTICE = "edit"
SAVED_IDEA = "Saved #{id} {title}."
# Several ideas at once, one a line (add_ideas).
MOST_AT_ONCE = 20
ADDED_SEVERAL = "Added {ideas}."
ALREADY_THERE = "Already there: {ideas}."
NOT_ADDED = "Not added: {ideas}."
NEEDS_LINES = "Write one idea a line, and the kind they all are."
CHANGED_IDEA = "Changed #{id} {title}."
DUPLICATE = "There is already an idea called that: #{id}. Nothing was added."
STALE_IDEA = (
    "#{id} was changed since you opened it, so nothing was saved. Here it is as it is now; "
    "make your change again."
)
RECORDED = "Recorded. #{id} is marked done."
# "How did it go?" on Home: three faces, kept as the same 1 to 10 rating the longer form takes.
FACES = {"loved": 9, "ok": 6, "not-great": 3}
RATED = "Thanks. That goes into the next suggestions."
SCHEDULED = "On the calendar: {title}."
PLANNED_HERE = "Added to the plans: {title}. Google Calendar isn't connected, so it is not on it."
MOVED = "Moved to {when}."
CANCELLED = "Canceled."
TICKED = "Done: {title}."
# For a kid: no numbers, which are the workings.
TICKED_PLAIN = "Done: {title}!"
REOPENED = "Back on your list: {title}."
# Beside the notice after a change that can be taken back: the call to undo (undo.py).
UNDO_NOTICE = "undo"
UNDONE = "Undone: {what}."
NOTHING_TO_UNDO = "There is nothing here to undo."
SNOOZED = "#{id} {title} comes back at {when}."
SNOOZED_PLAIN = "{title} comes back at {when}."
NOT_A_SNOOZE = "Choose In an hour or Tomorrow."
LOOKING = "Looking {what} up now: within a few minutes."
NOTHING_WAITING = "Nothing is waiting to be looked up."
REMEMBERED = {"saved": "Remembered: {fact}.", "already remembered": "Already remembered: {fact}."}
FORGOTTEN = "Forgotten: {fact}. It will not come back from what was said before."
NEEDS_FACT = "Say what to remember."
NOT_A_REASON = "Choose one of the reasons on the page."
# What a reason chip becomes in her memory: about the family, in their terms.
MADE_IT_GOOD = "What made {title} good: {reason}"
TICK_PAGES = {
    "home": "web.home",
    "tasks": "web.tasks",
    "chat": "chat.show",
    "week": "go.week",
    "board": "go.board",
}
NEEDS_TITLE = "An idea needs a title."
NEEDS_KIND = "An idea needs a kind: restaurant, outing, trip, show…"
NOT_A_NUMBER = "{label} needs to be a number."
NOT_A_REPEAT = "Choose how often it repeats from the list."
# Sent every time, so emptying one clears it.
IDEA_TEXT = ("description", "location_name", "url")
# Sent only when filled in: the tool reads a missing one as "leave it alone".
IDEA_NUMBERS = (
    ("duration_min", "The shortest time"),
    ("duration_max", "The longest time"),
    ("lead_time_days", "The booking lead time"),
    ("min_age", "The youngest age"),
    ("max_age", "The oldest age"),
)


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def run(
    name: str,
    values: dict[str, Any],
    *,
    hidden_from: list[int] | None = None,
    undo_target: int | None = None,
    offer_undo: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    """Run one tool as whoever is signed in, or, under the shared password, whoever the form said.
    Returns its result, or what went wrong (an unavailable tool's reason included). A change that
    can be taken back leaves an Undo beside the notice the page shows next."""
    app = _app()
    with closing(app.connect()) as conn:
        who = auth.visitor().name or _remember(request.form.get("who", ""))
        ctx = ToolContext(
            conn=conn,
            settings=app.settings,
            clock=app.clock,
            member=member_store.find_by_name(conn, who) if who else None,
            calendar=app.calendar,
            weather=app.weather,
            geocoder=app.geocoder,
            operation_id=(
                "web:"
                + hashlib.sha256(
                    f"{session.get(auth.CSRF_KEY, '')}:{request.form['once']}".encode()
                ).hexdigest()
                if name in {"create_event", "add_task"} and request.form.get("once")
                else None
            ),
            resume_scope=(
                "web-session:"
                + hashlib.sha256(str(session.get(auth.CSRF_KEY, "")).encode()).hexdigest()
                if name == "create_event" and session.get(auth.CSRF_KEY)
                else None
            ),
            idea_revision=request.form.get("revision") if name == "update_idea" else None,
            task_revision=_task_revision(request.form) if name == "update_task" else None,
            hidden_from=hidden_from,
            source="page",
            undo_target=undo_target,
        )
        result = app.registry.dispatch(name, values, ctx)
    payload = json.loads(result.content)
    if result.is_error:
        return None, payload.get("error", "that did not work")
    if payload.get("available") is False:
        return None, payload.get("reason", "that is not set up yet")
    if result.undoable and offer_undo:
        flash(str(result.call_id), UNDO_NOTICE)
    log.info("%s from the page by %s", name, auth.client_address())
    return payload, None


def _task_revision(form: MultiDict[str, str]) -> int | None:
    """The task revision the form was drawn at, or None."""
    given = _text(form, "revision")
    return int(given) if given.isascii() and given.isdigit() and len(given) <= 18 else None


def _remember(who: str) -> str:
    who = who.strip()
    if who:
        session[WHO_KEY] = who
    return who or str(session.get(WHO_KEY, ""))


def _text(form: MultiDict[str, str], key: str) -> str:
    return form.get(key, "").strip()


def _list(form: MultiDict[str, str], key: str) -> list[str]:
    """A comma-separated box as a list."""
    return [part.strip() for part in form.get(key, "").split(",") if part.strip()]


def _numbers(form: MultiDict[str, str]) -> tuple[dict[str, int], str | None]:
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
    """An idea form in the shape `add_idea` and `update_idea` take."""
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
    # Sent every time, so emptying the boxes clears them.
    first, time = _text(form, "happens_from"), _text(form, "happens_time")
    values["happens_from"] = f"{first}T{time}" if first and time else first
    values["happens_until"] = _text(form, "happens_until")
    return values, None


def _back(target: str, **values: Any) -> Response:
    return redirect(url_for(target, **values))


def _back_here(target: str, **values: Any) -> Response:
    """Back to the page the form named in `back` when it is a path on this site (Did, an outing,
    a happening), else to `target`. Never somewhere else a form could be made to send a person."""
    back = request.form.get("back", "")
    if back.startswith("/") and not back.startswith("//") and "\\" not in back:
        return redirect(back)
    return _back(target, **values)


def _tick_back(task_id: int) -> Response:
    """Where a tick, a snooze or a reopening returns: the page its form named (TICK_PAGES), the
    reminder's own page for `reminder`, else the list."""
    back = request.form.get("back", "")
    if back == "reminder":
        return _back("web.edit_task", task_id=task_id)
    return _back(TICK_PAGES.get(back, "web.tasks"))


def _say(message: str) -> None:
    flash(message, NOTICE)


def _kept_note(idea_id: int) -> str:
    """For a present, whom it is kept from, so saving one says who will not see it."""
    with closing(_app().connect()) as conn:
        idea = idea_store.get(conn, idea_id)
        if idea is None or not idea_store.is_gift(idea):
            return ""
        kept = presents.of_presents(conn, [idea], member_store.list_all(conn))[idea_id]
    return f" {kept.label}." if kept.words else ""


def _hidden_from(form: Any) -> list[int] | None:
    """Whom the idea form's "Hidden from" boxes kept a present from. None where the form did not
    ask (a form without the boxes) or, on a new idea, nobody was ticked: nobody chose, so the
    present is kept from whom it is for."""
    if not form.get("hidden_shown"):
        return None
    ticked = [int(one) for one in form.getlist("hidden_from") if one.isdigit()]
    if not ticked and not form.get("revision"):
        return None
    return ticked


@bp.post("/ideas/new")
@once
def add_idea() -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.new_idea")
    values, complaint = idea_fields(request.form)
    if complaint:
        _say(complaint)
        return _back("web.new_idea")
    result, complaint = run("add_idea", values, hidden_from=_hidden_from(request.form))
    if result is None:
        _say(complaint or "")
        return _back("web.new_idea")
    if "duplicate_of" in result:
        _say(DUPLICATE.format(id=result["duplicate_of"]))
        return _back("web.idea", idea_id=result["duplicate_of"])
    _say(SAVED_IDEA.format(id=result["id"], title=result["title"]) + _kept_note(result["id"]))
    return _back("web.idea", idea_id=result["id"])


@bp.post("/ideas/several")
@once
def add_ideas() -> Response:
    """Several ideas at once, one a line and one kind for them all: `add_idea` for each, no model
    call, and a notice of what was added and what was there already."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.new_idea")
    kind = _text(request.form, "kind")
    lines = [line.strip() for line in request.form.get("titles", "").splitlines()]
    titles = list(dict.fromkeys(line for line in lines if line))[:MOST_AT_ONCE]
    if not titles or not kind:
        _say(NEEDS_LINES)
        return _back("web.new_idea")
    added: list[str] = []
    there: list[str] = []
    refused: list[str] = []
    for title in titles:
        # Each its own call, kept as such; one Undo would take back only the last, so none.
        result, complaint = run("add_idea", {"title": title, "kind": kind}, offer_undo=False)
        if result is None:
            refused.append(f"{title} ({complaint})")
        elif "duplicate_of" in result:
            there.append(f"#{result['duplicate_of']} {title}")
        else:
            added.append(f"#{result['id']} {result['title']}")
    said = [
        words.format(ideas=", ".join(found))
        for words, found in ((ADDED_SEVERAL, added), (ALREADY_THERE, there), (NOT_ADDED, refused))
        if found
    ]
    _say(" ".join(said))
    return _back("web.ideas")


@bp.post("/idea/<int:idea_id>/edit")
@once
def edit_idea(idea_id: int) -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.edit_idea", idea_id=idea_id)
    if not _text(request.form, "revision"):
        _say(STALE_IDEA.format(id=idea_id))
        return _back("web.edit_idea", idea_id=idea_id)
    values, complaint = idea_fields(request.form)
    if complaint:
        _say(complaint)
        return _back("web.edit_idea", idea_id=idea_id)
    status = _text(request.form, "status")
    if status:
        values["status"] = status
    result, complaint = run(
        "update_idea", {**values, "id": idea_id}, hidden_from=_hidden_from(request.form)
    )
    if result is None:
        _say(complaint or "")
        return _back("web.edit_idea", idea_id=idea_id)
    _say(CHANGED_IDEA.format(id=result["id"], title=result["title"]) + _kept_note(idea_id))
    return _back("web.idea", idea_id=idea_id)


@bp.post("/idea/<int:idea_id>/status")
@once
def set_status(idea_id: int) -> Response:
    """Drop an idea, or bring a dropped one back."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.idea", idea_id=idea_id)
    result, complaint = run("update_idea", {"id": idea_id, "status": _text(request.form, "status")})
    if result is None:
        _say(complaint or "")
    else:
        _say(CHANGED_IDEA.format(id=result["id"], title=result["title"]))
    return _back_here("web.idea", idea_id=idea_id)


@bp.post("/idea/<int:idea_id>/lookup")
@once
def look_up(idea_id: int) -> Response:
    """Look one idea up now rather than with the evening's lookups."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.idea", idea_id=idea_id)
    result, complaint = run("look_up_now", {"idea_ids": [idea_id]})
    _say(LOOKING.format(what="it") if result is not None else complaint or "")
    return _back("web.idea", idea_id=idea_id)


@bp.post("/lookups/now")
@once
def look_up_waiting() -> Response:
    """Every idea waiting, looked up now."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.status")
    result, complaint = run("look_up_now", {})
    if result is None:
        _say(complaint or "")
    elif not result["asked"]:
        _say(NOTHING_WAITING)
    else:
        count = len(result["asked"])
        _say(LOOKING.format(what="1 idea" if count == 1 else f"{count} ideas"))
    return _back("web.status")


@bp.post("/idea/<int:idea_id>/outcome")
@once
def record_outcome(idea_id: int) -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.idea", idea_id=idea_id)
    form = request.form
    values: dict[str, Any] = {"idea_id": idea_id, "notes": _text(form, "notes") or None}
    if happened := _text(form, "happened_on"):
        values["happened_on"] = happened
    if rating := _text(form, "rating"):
        values["rating"] = int(rating)  # a fixed list of scores, so this cannot fail
    went = _text(form, "went")
    if went in FACES:
        values["rating"] = FACES[went]
    if plan_id := _text(form, "plan_id"):
        values["plan_id"] = int(plan_id) if plan_id.isdigit() else None
    repeat = _text(form, "would_repeat")
    if repeat in {"yes", "no"}:
        values["would_repeat"] = repeat == "yes"
    _, complaint = run("record_outcome", values)
    _say(complaint or (RATED if went in FACES else RECORDED.format(id=idea_id)))
    if _text(form, "back") == "home":  # asked on Home: back there for the next one
        return _back("web.home")
    if _text(form, "back") == "board":  # asked on the kitchen tablet
        return _back("go.board")
    if _text(form, "back") == "plans":  # asked on the month: back to what is still to rate
        return _back("web.plans_month", month=_text(form, "month") or None, _anchor="rate")
    if _text(form, "back") == "did":  # asked on What we did or a day of the week
        return _back("go.did")
    if _text(form, "back") == "plan" and plan_id and plan_id.isdigit():  # on the plan's page
        return _back("go.plan", plan_id=int(plan_id))
    return _back("web.idea", idea_id=idea_id)


@bp.post("/plans/new")
@once
def add_plan() -> Response:
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
        # An all-day plan keeps only the date.
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
        words = SCHEDULED if result.get("event") else PLANNED_HERE
        _say(words.format(title=result["plan"]["title"]))
    return _back_here(back[0], **back[1])


@bp.post("/plan/<int:plan_id>/move")
@once
def move_plan(plan_id: int) -> Response:
    """Change when a plan is, keeping its link and notes."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.plans")
    all_day = bool(request.form.get("all_day"))
    start = _text(request.form, "start")
    result, complaint = run(
        "update_event",
        {"plan_id": plan_id, "start": start[:10] if all_day else start, "all_day": all_day},
    )
    if result is None:
        _say(complaint or "")
    else:
        _say(MOVED.format(when=views.day_text(result["plan"]["start"])))
    if request.form.get("back") == "plan":
        return _back("go.plan", plan_id=plan_id)
    return _back("web.plans")


@bp.post("/plan/<int:plan_id>/cancel")
@once
def cancel_plan(plan_id: int) -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.plans")
    _, complaint = run("delete_event", {"plan_id": plan_id})
    _say(complaint or CANCELLED)
    if request.form.get("back") == "plan":
        return _back("go.week")
    return _back("web.plans")


def task_fields() -> dict[str, Any]:
    return {
        "title": _text(request.form, "title"),
        "notes": _text(request.form, "notes"),
        "owner": _text(request.form, "owner") or None,
        "due_at": _text(request.form, "due_at") or None,
        "preferred_window": _text(request.form, "preferred_window"),
        "remind_at": _text(request.form, "remind_at") or None,
    }


# "every:unit", as the form sends it.
REPEAT_CHOICE = re.compile(r"(\d{1,3}):(day|week|month|year)")


def repeat_chosen(form: MultiDict[str, str]) -> str:
    """The repeat the form asks for, "every:unit:from", or "" for none."""
    choice = _text(form, "repeat")
    if not choice:
        return ""
    return f"{choice}:{'done' if form.get('repeat_after_done') else 'schedule'}"


def repeat_fields(chosen: str) -> dict[str, Any] | None:
    """The tool's repeat fields for a choice; None when it is not one the page offers."""
    every_unit, _, start = chosen.rpartition(":")
    found = REPEAT_CHOICE.fullmatch(every_unit)
    if found is None or start not in ("schedule", "done"):
        return None
    return {"repeat_every": int(found[1]), "repeat_unit": found[2], "repeat_from": start}


@bp.post("/tasks/new")
@once
def add_task() -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
    elif not request.form.get("once"):
        _say("Reload the form before saving.")
    elif (chosen := repeat_chosen(request.form)) and repeat_fields(chosen) is None:
        _say(NOT_A_REPEAT)
    else:
        values = task_fields()
        if chosen:
            values.update(repeat_fields(chosen) or {})
        result, complaint = run("add_task", values)
        _say(complaint or views.task_saved(result))
    return _back("web.tasks")


@bp.post("/task/<int(max=9223372036854775807):task_id>/edit")
@once
def edit_task(task_id: int) -> Response:
    """Save a to-do's own page. A complaint keeps you on it (with the words); a save goes back to
    the list."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
    elif _task_revision(request.form) is None:
        _say("Reload this to-do before changing it.")
    elif (chosen := repeat_chosen(request.form)) and repeat_fields(chosen) is None:
        _say(NOT_A_REPEAT)
    else:
        values = task_fields()
        values.update(
            task_id=task_id,
            status=_text(request.form, "status"),
            clear_due=not bool(values["due_at"]),
            clear_reminder=bool(request.form.get("clear_reminder")),
        )
        # Sent only when changed: as it was, it would move the schedule to where a snooze left it.
        if chosen != _text(request.form, "repeat_was"):
            if chosen:
                values.update(repeat_fields(chosen) or {})
            else:
                values["stop_repeating"] = True
        result, complaint = run("update_task", values)
        _say(complaint or f"Saved your changes to {result['task']['title']}.")
        if complaint is None:
            return _back("web.tasks")
    return _back("web.edit_task", task_id=task_id)


@bp.post("/task/<int(max=9223372036854775807):task_id>/done")
@once
def finish_task(task_id: int) -> Response:
    """The tick beside a task: sends only the status, which `update_task` reads as "leave the rest
    alone" (the edit form sends every box, so an empty one clears). Its revision keeps a task
    changed meanwhile from being ticked unseen."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
    elif _task_revision(request.form) is None:
        _say("Reload this task before ticking it off.")
    else:
        result, complaint = run("update_task", {"task_id": task_id, "status": "done"})
        said = TICKED if auth.visitor().may("browse") else TICKED_PLAIN
        _say(complaint or said.format(id=task_id, title=result["task"]["title"]))
    return _tick_back(task_id)


@bp.post("/task/<int(max=9223372036854775807):task_id>/reopen")
@once
def reopen_task(task_id: int) -> Response:
    """Undo a tick: the to-do is open again. Only the status is sent, as for the tick."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
    else:
        result, complaint = run("update_task", {"task_id": task_id, "status": "open"})
        _say(complaint or REOPENED.format(title=result["task"]["title"]))
    return _tick_back(task_id)


@bp.post("/task/<int(max=9223372036854775807):task_id>/snooze")
@once
def snooze_task(task_id: int) -> Response:
    """In an hour or Tomorrow under a reminder in the chat, as the buttons under it on Telegram:
    a new reminder through `update_task`, at the time a tap there would set
    (`buttons.snoozed_until`), at the revision the reminder was drawn at."""
    action = request.form.get("when", "")
    if (complaint := auth.refused()) is not None:
        _say(complaint)
    elif _task_revision(request.form) is None:
        _say("Reload this task before snoozing it.")
    elif action not in buttons.SNOOZES:
        _say(NOT_A_SNOOZE)
    else:
        clock = _app().clock
        moment = buttons.snoozed_until(action, clock.now())
        values = {"task_id": task_id, "remind_at": moment.strftime("%Y-%m-%dT%H:%M")}
        result, complaint = run("update_task", values)
        said = SNOOZED if auth.visitor().may("browse") else SNOOZED_PLAIN
        when = buttons.when_text(moment, clock.today())
        _say(complaint or said.format(id=task_id, title=result["task"]["title"], when=when))
    return _tick_back(task_id)


@bp.post("/undo")
@once
def undo() -> Response:
    """Undo beside a form's notice, and under her reply in the chat: the undo tool for the one
    change the button names (ToolContext.undo_target, never the tool's input), as whoever is
    signed in; it says who may. Back to the page the button was on."""
    target = request.form.get("target", "")
    if (complaint := auth.refused()) is not None:
        _say(complaint)
    elif not (target.isascii() and target.isdigit() and len(target) <= 18):
        _say(NOTHING_TO_UNDO)
    else:
        result, complaint = run("undo", {}, undo_target=int(target))
        _say(complaint or UNDONE.format(what=result["undone"]))
    back = request.form.get("back", "")
    # Only a path on this page: never somewhere else a form could be made to send a person.
    if not back.startswith("/") or back.startswith("//") or "\\" in back:
        back = url_for("web.home")
    return redirect(back)


LIST_ACTIONS = frozenset(views.LIST_SAID)


@bp.post("/lists/change")
@once
def change_list() -> Response:
    """A list's box, ticks and clearing: shopping_list, as she would call it, as whoever is signed
    in (a kid may not, until the family decides)."""
    action = request.form.get("action", "")
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.lists_page")
    if action not in LIST_ACTIONS:
        return _back("web.lists_page")
    name = _text(request.form, "name") or "shopping"
    things = [line.strip() for line in request.form.get("items", "").splitlines() if line.strip()]
    result, complaint = run("shopping_list", {"action": action, "items": things, "name": name})
    if result is None:
        _say(complaint or "")
        return _back("web.lists_page")
    title = views.list_title(result["list"]).lower()
    said = []
    if done := result.get(action):
        said.append(views.LIST_SAID[action].format(list=title, items=", ".join(done)))
    elif action == "clear_ticked":
        said.append(views.LIST_SAID[action].format(list=title, items=""))
    if already := result.get("already"):
        said.append(views.LIST_ALREADY.format(items=", ".join(already)))
    _say(" ".join(said))
    if _text(request.form, "back") == "board":  # ticked on the kitchen tablet
        return _back("go.board")
    return _back("web.lists_page", name=_text(request.form, "back") or None)


@bp.post("/memory/new")
@once
def add_memory() -> Response:
    """Something to remember, typed in: `remember` takes back a forgotten thing only from a person,
    never from a conversation."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.memory")
    fact = _text(request.form, "fact")
    if not fact:
        _say(NEEDS_FACT)
        return _back("web.memory")
    change = {
        "action": "add",
        "fact": fact,
        "about": _text(request.form, "about") or "family",
        "category": _text(request.form, "category") or "other",
        "firm": bool(request.form.get("firm")),
        "until": _text(request.form, "until") or None,
    }
    result, complaint = run("remember", {"changes": [change]})
    if complaint is None and result is not None:
        done = result["remembered"][0]
        complaint = REMEMBERED.get(done["result"], "{fact}").format(fact=done["fact"])
    _say(complaint or "")
    return _back("web.memory")


@bp.post("/did/<int(max=9223372036854775807):outcome_id>/good")
@once
def made_it_good(outcome_id: int) -> Response:
    """What made an outing good, one chip on its page: `remember` keeps it about the family, so
    she leans that way next time (docs/INTERFACE.md section 4, What we did)."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("go.outing", outcome_id=outcome_id)
    reason = _text(request.form, "reason")
    if reason not in views.GOOD_REASONS:
        _say(NOT_A_REASON)
        return _back("go.outing", outcome_id=outcome_id)
    with closing(_app().connect()) as conn:
        outing = outcome_store.get(conn, outcome_id)
        idea = idea_store.get(conn, outing.idea_id) if outing and outing.idea_id else None
        kept = idea is not None and presents.is_kept_from(conn, idea, auth.visitor().member)
    if idea is None or kept:
        _say(NOT_A_REASON)
        return _back("go.did")
    change = {
        "action": "add",
        "fact": MADE_IT_GOOD.format(title=idea.title, reason=reason.lower()),
        "about": "family",
        "category": "food" if idea.kind == "restaurant" else "activities",
    }
    result, complaint = run("remember", {"changes": [change]})
    if complaint is None and result is not None:
        done = result["remembered"][0]
        complaint = REMEMBERED.get(done["result"], "{fact}").format(fact=done["fact"])
    _say(complaint or "")
    return _back("go.outing", outcome_id=outcome_id)


@bp.post("/memory/<int(max=9223372036854775807):memory_id>/forget")
@once
def forget_memory(memory_id: int) -> Response:
    """Forget one: kept, marked, so the same thing is never saved again."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _back("web.memory")
    result, complaint = run("remember", {"changes": [{"action": "forget", "id": memory_id}]})
    if complaint is None and result is not None:
        complaint = FORGOTTEN.format(fact=result["remembered"][0]["fact"])
    _say(complaint or "")
    return _back("web.memory")


# -- the kids' wish lists (docs/WISHES.md) --------------------------------------------------------

LISTS = {"everyday", "christmas", "birthday"}


def _to_wishes() -> Response:
    """Back to the lists the form came from (one kid's, for a parent looking at hers), or to Now
    when the question was asked there."""
    if request.form.get("back") == "home":
        return _back("web.home")
    if request.form.get("back") == "board":
        return _back("go.board")
    kid = request.form.get("kid", "")
    return _back("web.wishes", **({"who": kid} if kid.isdigit() else {}))


def _wish_id(value: Any) -> int | None:
    text = str(value or "")
    return int(text) if text.isdigit() and len(text) < 18 else None


@bp.post("/wishes")
@once
def add_wish() -> Response:
    """A wish typed into her list, held to the tool's rules: lockouts, daily count, duplicates."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _to_wishes()
    title = request.form.get("title", "").strip()
    chosen = request.form.get("list", "everyday")
    values: dict[str, Any] = {
        "title": title,
        "topic": title,
        "list": chosen if chosen in LISTS else "everyday",
    }
    for_whom = request.form.get("for_whom", "").strip()
    if for_whom:
        values["for_whom"] = for_whom
    result, complaint = run("add_wish", values)
    if complaint:
        _say(complaint)
    else:
        wish = result.get("wish") or {}
        again = views.day_words(result.get("locked_until"), _app().clock.today())
        _say(views.WISH_SAID[result["result"]].format(title=wish.get("title", title), again=again))
    return _to_wishes()


@bp.post("/wish/<int(max=9223372036854775807):wish_id>/move")
@once
def move_wish(wish_id: int) -> Response:
    """Up, down, to the top, or to another list: free, never a lockout."""
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _to_wishes()
    values: dict[str, Any] = {"wish_id": wish_id}
    position = _wish_id(request.form.get("position"))
    if position is not None:
        values["position"] = max(1, position)
    chosen = request.form.get("list", "")
    if chosen in LISTS:
        values["list"] = chosen
    _, complaint = run("update_wish", values)
    _say(complaint or views.WISH_MOVED)
    return _to_wishes()


@bp.post("/wish/<int(max=9223372036854775807):wish_id>/withdraw")
@once
def withdraw_wish(wish_id: int) -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _to_wishes()
    _, complaint = run("update_wish", {"wish_id": wish_id, "status": "withdrawn"})
    _say(complaint or views.WISH_WITHDRAWN)
    return _to_wishes()


@bp.post("/wish/<int(max=9223372036854775807):wish_id>/answer")
@once
def answer_wish(wish_id: int) -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _to_wishes()
    status = request.form.get("status", "")
    if status not in ("granted", "declined"):
        _say("Choose yes or not this time.")
        return _to_wishes()
    values: dict[str, Any] = {"wish_id": wish_id, "status": status}
    note = request.form.get("note", "").strip()
    if note:
        values["answer_note"] = note
    result, complaint = run("update_wish", values)
    if complaint:
        _say(complaint)
    else:
        _say(views.WISH_ANSWERED[status].format(title=result["wish"]["title"]))
    return _to_wishes()


@bp.post("/wish/<int(max=9223372036854775807):wish_id>/ask")
@once
def ask_parent(wish_id: int) -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return _to_wishes()
    _, complaint = run("update_wish", {"wish_id": wish_id, "ask_parent": True})
    _say(complaint or views.ASKED_A_PARENT)
    return _to_wishes()
