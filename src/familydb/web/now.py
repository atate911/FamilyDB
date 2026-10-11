"""Now, the first screen (docs/INTERFACE.md section 3): the box, one line of context, then what
needs this person (her questions), her picks for this moment, and today's line. Nothing here is a
model call: the picks are made ahead (familydb/picks.py, read from the store), the questions and
the day's line are read from the tables and worded by code. This module only reads; the forms it
draws post to the edit pages and the chat."""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import date, datetime, timedelta
from typing import Any

from flask import Response, abort, current_app, redirect, request, session, url_for

from familydb import agenda, personas, presents
from familydb.app import App
from familydb.base import roles
from familydb.base.dates import clock_time, utc_iso
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import picks as pick_store
from familydb.store import plans as plan_store
from familydb.store import tasks as task_store
from familydb.store.members import Member
from familydb.web import auth, chat, shell, views
from familydb.web import status as status_page
from familydb.web.answers import answer

log = logging.getLogger(__name__)

# How far ahead today's line looks: today and tomorrow.
DAYS_AHEAD = 1
# A kid's pitch (an idea she suggested that nobody has planned or dropped) is asked about this long.
PITCH_DAYS = 14
# "Later" on a pitch keeps it off this device's Now for a week (the session cookie, no write).
LATER_KEY = "later"
LATER_DAYS = 7
# The most questions Now asks at once: the rest wait for the next visit.
MOST_QUESTIONS = 3
QUIET = "Nothing needs you."
QUIET_KID = "Nothing waiting on you."
# What "Different ones" sends her: a message, so it costs what a message costs.
DIFFERENT = "What else could we do? Different ones, please."
# How a question from her names where it came from.
ASKED_ON = "{who}, {when}"
# The first day: the box's question, and her one line.
FIRST_PROMPT = "A place your family would happily go back to…"
FIRST_DAY = (
    "Hi, I'm {name}. Tell me a place your family would happily go back to, or something you've "
    "been meaning to try, and I'll have ideas for you by tomorrow."
)


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def show() -> Response | str:
    """Draw Now for whoever is looking. An admin is sent to setup until the bot can answer."""
    if any(request.args.get(key) for key in views.IDEA_FILTERS):
        # The old Home took a search; an old bookmark's goes on to the ideas list.
        return redirect(url_for("web.ideas", **request.args))
    app = _app()
    now = app.clock.now()
    today = app.clock.today()
    tz = app.settings.tzinfo
    visitor = auth.visitor()
    grown_up = visitor.may("browse")
    kid = chat.is_kid()
    with closing(app.connect()) as conn:
        progress = status_page.setup_progress(app, conn)
        if visitor.manages and not status_page.ready_to_answer(progress):
            return redirect(url_for("setup.overview"))
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        kept = presents.kept_ids(conn, visitor.member)
        seen = agenda.read(app, conn, today, today + timedelta(days=DAYS_AHEAD))
        on = presents.without(seen.entries, kept)
        rows = _rows(conn, on, visitor.member if not grown_up else None, today, slots)
        questions = _questions(conn, app, visitor, today, slots, people)[:MOST_QUESTIONS]
        todo = _todo(conn, app, visitor, today, slots, grown_up)
        picks = _picks(conn, app, visitor, kept, today)
        setup = status_page.setup_steps(app, conn) if visitor.manages else []
        my_list = _my_list(conn, visitor, today) if kid else None
        # The first day (docs/INTERFACE.md section 10): nothing saved and nothing on, so the box
        # asks for a place they would go back to and she says who she is; nothing empty-with-chrome.
        first_day = (
            grown_up
            and not picks
            and not rows
            and not idea_store.list_all(conn, include_dropped=True)
        )
        prompt = chat.KID_HOME_PROMPT if kid else chat.HOME_PROMPT
        chat.page_box(app, conn, people, prompt=FIRST_PROMPT if first_day else prompt)
        left = chat.messages_left(app, conn, visitor.member)
        readers = chat.readers(people) if kid else ""
    fact = picks["header"] if picks else None
    if kid and readers:  # her context line says who can read her chat, never a forecast
        fact = f"{readers} can read this"
    return answer(
        "now.html",
        context=views.context_line(now.astimezone(tz), fact),
        left=left,
        questions=questions,
        plate=todo,
        my_list=my_list,
        picks=picks,
        days=_days(rows, today, grown_up),
        quiet=QUIET if grown_up else QUIET_KID,
        setup=setup,
        different=DIFFERENT,
        first_day=FIRST_DAY.format(name=personas.active(app.settings).name) if first_day else None,
    )


def _rows(
    conn: Any,
    entries: list[agenda.Entry],
    only_for: Member | None,
    today: date,
    slots: dict[str, int],
) -> list[dict[str, Any]]:
    """What is on, as rows, without the days gone; for a kid, the ones that name her or nobody."""
    rows = []
    for entry in entries:
        if entry.days()[-1] < today or entry.status == "cancelled":
            continue
        idea = idea_store.get(conn, entry.idea_id) if entry.idea_id else None
        if only_for is not None and not views.names_in(views.people_for(idea, slots), only_for):
            continue
        rows.append(
            {
                "title": entry.title,
                "day": entry.days()[0].isoformat(),
                "end": entry.days()[-1].isoformat(),
                "time": None if entry.all_day else clock_time(entry.start),
                "all_day": entry.all_day,
                "status": entry.status,
                "idea_id": entry.idea_id,
            }
        )
    return rows


def _days(rows: list[dict[str, Any]], today: date, grown_up: bool) -> list[dict[str, Any]]:
    """Today's and tomorrow's lines: what is on each, in a sentence, or that nothing is."""
    lines = []
    for offset, label in ((0, "Today"), (1, "Tomorrow")):
        day = today + timedelta(days=offset)
        on = [row for row in rows if row["day"] <= day.isoformat() <= row["end"]]
        lines.append(
            {"label": label, "parts": views.day_line(on, url_for("go.day", day=day.isoformat()))}
        )
    return lines


def _todo(
    conn: Any,
    app: App,
    visitor: auth.Visitor,
    today: date,
    slots: dict[str, int],
    grown_up: bool,
) -> list[dict[str, Any]]:
    """What waits on this person today: a kid's own to-dos, all of them, which she ticks off here;
    a grown-up's that are late or due today (the rest are on the week's plate)."""
    if not grown_up and visitor.member is None:
        return []
    own = None if grown_up else visitor.member.id
    found = presents.visible_tasks(
        conn, task_store.list_all(conn, status="open", owner_id=own), visitor.member
    )
    tz = app.settings.tzinfo
    rows = [views.todo_row(task, tz, today, slots, kid=not grown_up) for task in found]
    if grown_up:
        rows = [
            row
            for row, task in zip(rows, found, strict=True)
            if row["late"]
            or (task.due_at and views.local_day(task.due_at, tz) == today.isoformat())
        ]
    return rows


def _my_list(conn: Any, visitor: auth.Visitor, today: date) -> dict[str, Any] | None:
    """A kid's own list on her Now: what a parent said lately, her top three, and how far off the
    days are (docs/WISHES.md). The lists page's own reading of it, so the two never disagree."""
    from familydb.web import routes  # not at the top: routes draws Now

    if visitor.member is None or not visitor.may("wish"):
        return None
    mine = routes.wish_glance(conn, today)
    if not mine or mine.get("parent"):
        return None
    lists = mine["mine"]
    return {
        "top": lists["lists"][0]["rows"][: mine["top"]],
        "open": lists["open"],
        "answered": sorted(lists["answered"], key=lambda row: row["status"], reverse=True)[:2],
        "soon": [each for each in lists["lists"] if each["countdown"]],
    }


# -- her questions ---------------------------------------------------------------------------------


def _questions(
    conn: Any,
    app: App,
    visitor: auth.Visitor,
    today: date,
    slots: dict[str, int],
    people: list[Member],
) -> list[dict[str, Any]]:
    """What waits on this person, oldest first: a plan to say how it went, a kid's request to
    answer, a kid's pitch to look at. A kid is asked nothing here: her questions reach her chat."""
    if not visitor.may("change"):
        return []
    tz = app.settings.tzinfo
    asked: list[dict[str, Any]] = []
    for row in _unrated(conn, today, slots, visitor.member):
        asked.append(
            {
                "kind": "rate",
                "text": f"How did {row['title']} go?",
                "origin": row["when"],
                "sort": row["day"],
                **row,
            }
        )
    if visitor.may("decide"):
        names = {person.id: person for person in people}
        glance = shell.wishes_waiting(conn, today)
        for row in glance:
            kid = names.get(row["kid_id"])
            asked.append(
                {
                    "kind": "wish",
                    "wish_id": row["id"],
                    "kid_id": row["kid_id"],
                    "kid_slug": views.slug(row["kid"]),
                    "text": f"{row['kid']} asked for {row['title']}."
                    + (f" {row['concern']}." if row.get("concern") else ""),
                    "origin": ASKED_ON.format(
                        who=row["kid"], when=views.day_words(row["asked_at"], today)
                    )
                    if row.get("asked_at")
                    else row["kid"],
                    "sort": (row.get("asked_at") or "")[:10],
                    "slot": kid.slot if kid else 0,
                }
            )
        asked.extend(_pitches(conn, app, today, people, tz))
    asked.sort(key=lambda q: q["sort"])
    return asked


def _unrated(
    conn: Any, today: date, slots: dict[str, int], who: Member | None
) -> list[dict[str, Any]]:
    """Every plan of the last two weeks nobody has said how it went, oldest first, without the
    ones made from a present kept from `who`."""
    waiting = presents.without(
        plan_store.unrated(
            conn,
            today=today.isoformat(),
            since=(today - timedelta(days=shell.RATE_DAYS)).isoformat(),
        ),
        presents.kept_ids(conn, who),
    )
    found = []
    for plan in waiting:
        idea = idea_store.get(conn, plan.idea_id) if plan.idea_id else None
        day = date.fromisoformat(plan.start[:10])
        found.append(
            {
                "plan_id": plan.id,
                "idea_id": plan.idea_id,
                "title": plan.title,
                "day": plan.start[:10],
                "when": views.day_short(day),
                "people": views.people_for(idea, slots),
            }
        )
    return found


def _pitches(
    conn: Any, app: App, today: date, people: list[Member], tz: Any
) -> list[dict[str, Any]]:
    """A kid's ideas of the last two weeks that nobody has planned, dropped or put off ("Later" on
    this device), each as her pitch."""
    kids = {
        p.id: p for p in people if roles.may(p.role, "wish") and not roles.may(p.role, "decide")
    }
    if not kids:
        return []
    since = utc_iso(datetime.combine(today - timedelta(days=PITCH_DAYS), datetime.min.time(), tz))
    put_off = _later()
    found = []
    for idea in idea_store.list_all(conn):
        kid = kids.get(idea.suggested_by or -1)
        if kid is None or idea.status != "idea" or idea.created_at < since:
            continue
        if idea_store.is_gift(idea) or str(idea.id) in put_off:
            continue
        found.append(
            {
                "kind": "pitch",
                "idea_id": idea.id,
                "text": f"{kid.display_name} suggested {idea.title}.",
                "origin": ASKED_ON.format(
                    who=kid.display_name,
                    when=views.day_words(views.local_day(idea.created_at, tz), today),
                ),
                "sort": views.local_day(idea.created_at, tz),
                "slot": kid.slot or 0,
            }
        )
    return found


def _later() -> dict[str, str]:
    """The pitches put off on this device, with when each comes back, the gone ones dropped."""
    kept = session.get(LATER_KEY)
    if not isinstance(kept, dict):
        return {}
    now = utc_iso(_app().clock.now())
    live = {key: until for key, until in kept.items() if isinstance(until, str) and until > now}
    if live != kept:
        session[LATER_KEY] = live
    return live


def later() -> Response:
    """Later on a kid's pitch: off this device's Now for a week. The session cookie, no write."""
    if auth.refused() is not None:
        abort(400)
    idea = request.form.get("idea", "")
    if not (idea.isascii() and idea.isdigit() and len(idea) < 18):
        abort(400)
    kept = _later()
    kept[idea] = utc_iso(_app().clock.now() + timedelta(days=LATER_DAYS))
    session[LATER_KEY] = kept
    return redirect(url_for("go.board" if request.form.get("back") == "board" else "web.home"))


# -- her picks -------------------------------------------------------------------------------------


def _picks(
    conn: Any, app: App, visitor: auth.Visitor, kept: set[int], today: date
) -> dict[str, Any] | None:
    """The set made for this moment (familydb/picks.py), as tiles: one of each kind, with its
    reason, never a present kept from this person. None when there is no set yet."""
    mine = visitor.member.id if chat.is_kid() and visitor.member else None
    found = pick_store.current(conn, member_id=mine, today=today.isoformat())
    return pick_set(app, found, kept) if found is not None else None


def pick_set(app: App, found: pick_store.PickSet, kept: set[int]) -> dict[str, Any] | None:
    """A made-ahead set as Now and What about draw it: its tiles, never a present kept from this
    person, the line that drove it and when it was chosen. None when nothing in it is left."""
    tiles = []
    for pick in found.picks:
        if pick.get("idea_id") in kept:
            continue
        if pick.get("idea_id"):
            href = url_for("web.idea", idea_id=pick["idea_id"])
        elif pick.get("find_id"):
            href = url_for("web.find", find_id=pick["find_id"])
        else:
            href = url_for("web.happening_page")
        tiles.append(
            {
                "kind": pick.get("kind", ""),
                "when": pick.get("when", ""),
                "title": pick["title"],
                "why": pick.get("why", ""),
                "href": href,
            }
        )
    if not tiles:
        return None
    return {
        "window": found.window,
        "tiles": tiles,
        "header": found.header,
        "made": views.made_words(found.made_at, app.clock.now(), app.settings.tzinfo),
    }
