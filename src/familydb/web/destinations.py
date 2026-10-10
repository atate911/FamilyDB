"""Destinations and items that are new with the frame (docs/INTERFACE.md sections 4 and 5): What
about (`/about`), This week (`/week`, and a day of it at `/week/<date>`), a plan (`/plan/<id>`),
What we did (`/did`) and one outing of it (`/did/<id>`). Reading only, worded by code; the forms
they draw post to the edit pages. Eat, Do, Kids, Soon and Lists are the older pages redrawn on
the frame (web/routes.py)."""

from __future__ import annotations

import logging
from contextlib import closing
from datetime import date, timedelta
from typing import Any

from flask import Blueprint, abort, current_app, render_template, request, url_for

from familydb import agenda, personas, presents, roles
from familydb.app import App
from familydb.availability import calendar_available, weather_available
from familydb.dates import utc_iso
from familydb.store import ideas as idea_store
from familydb.store import lists as list_store
from familydb.store import members as member_store
from familydb.store import outcomes as outcome_store
from familydb.store import picks as pick_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.store import tasks as task_store
from familydb.store.members import Member
from familydb.suggest.types import DAY_END, DAY_START
from familydb.tools.weather import forecast_days
from familydb.web import auth, chat, now, routes, views

log = logging.getLogger(__name__)

bp = Blueprint("go", __name__)

WEEK_DAYS = 7
# What we did looks back this far.
DID_DAYS = 180
# A timed plan with no end is taken to last this long on the week, as the evening check does.
ASSUMED_MINUTES = 120
# A face for a rating, on the same scale the three faces record (edits.FACES).
LOVED_FROM = 8
OK_FROM = 5
FACE_WORDS = {"loved": "Loved it", "ok": "OK", "not-great": "Not great"}


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _day_arg(name: str) -> date | None:
    """A date in the address, or None; anything that is not one is a missing page."""
    given = request.args.get(name, "")
    if not given:
        return None
    try:
        when = date.fromisoformat(given)
    except ValueError:
        abort(404)
    if not 2000 <= when.year <= 2100:
        abort(404)
    return when


# -- This week -------------------------------------------------------------------------------------


@bp.get("/week")
def week() -> str:
    """Today and the week around it: what is on each day, the free time, the forecast, the
    reminders due; and, for a grown-up, the plate of what has no day yet or is late."""
    app = _app()
    today = app.clock.today()
    start = _day_arg("from") or today
    return render_template("week.html", **_days(app, start, start + timedelta(days=WEEK_DAYS - 1)))


@bp.get("/week/<day>")
def day(day: str) -> str:
    """One day: everything on it, the free stretches, the reminders, and after it how it went."""
    app = _app()
    try:
        when = date.fromisoformat(day)
    except ValueError:
        abort(404)
    if not 2000 <= when.year <= 2100:
        abort(404)
    shown = _days(app, when, when)
    return render_template("week.html", one=shown["days"][0], **shown)


def _days(app: App, first: date, last: date) -> dict[str, Any]:
    today = app.clock.today()
    tz = app.settings.tzinfo
    visitor = auth.visitor()
    grown_up = visitor.may("browse")
    only_for = None if grown_up else visitor.member
    who = request.args.get("who", "").strip()
    with closing(app.connect()) as conn:
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        kept = presents.kept_ids(conn, visitor.member)
        seen = agenda.read(app, conn, first, last)
        on = presents.without(seen.entries, kept)
        rows = routes._plan_rows(conn, app, on, today, slots, only_for, past=True)
        if who:
            rows = [row for row in rows if views.names_in(row["people"], _named(people, who))]
        due = _due(conn, visitor, first, last, tz, today, slots, grown_up)
        plate = (
            _plate(conn, visitor, today, tz, slots) if grown_up and first <= today <= last else []
        )
        pencil = _pencil(conn, kept, first, last, today) if grown_up else None
        went = _went(conn, first, last, slots) if last < today or first == last else []
        rate = routes._unrated(conn, today, slots, visitor.member) if visitor.may("change") else []
        chat.page_box(app, conn, people, scope={"label": "This week", "text": "About this week:"})
    forecasts = _forecasts(app, first, last, today)
    days = []
    for offset in range((last - first).days + 1):
        when = first + timedelta(days=offset)
        iso = when.isoformat()
        todays = [row for row in rows if row["day"] <= iso <= row["end"]]
        free = _free(todays, when, iso)
        forecast = forecasts.get(when)
        days.append(
            {
                "iso": iso,
                "label": views.day_label(when, today),
                "today": when == today,
                "weekend": when.weekday() >= 5,
                "past": when < today,
                "rows": todays,
                "free": views.free_words(free, whole=not todays),
                "due": [row for row in due if row["day"] == iso],
                "forecast": views.forecast_words(forecast, app.settings) if forecast else None,
                "pencil": pencil if pencil and pencil["day"] == iso and free else None,
                "went": [row for row in went if row["day"] == iso],
                "rate": [row for row in rate if row["day"] == iso],
                "href": url_for("go.day", day=iso),
            }
        )
    people_chips = [
        {
            "label": person.display_name,
            "href": url_for("go.week", **_keep(who=person.display_name)),
            "on": who.casefold() == person.display_name.casefold(),
        }
        for person in people
        if grown_up
    ]
    if who and grown_up:
        people_chips.insert(
            0, {"label": "Everyone", "href": url_for("go.week", **_keep(who="")), "on": False}
        )
    return {
        "days": days,
        "plate": plate,
        "summary": views.week_summary(days, plate, grown_up),
        "chips": people_chips,
        "source": seen.source,
        "source_note": views.AGENDA_NOTES[seen.source],
        "earlier": url_for("go.week", **{"from": (first - timedelta(days=WEEK_DAYS)).isoformat()}),
        "later": url_for("go.week", **{"from": (last + timedelta(days=1)).isoformat()}),
        "this_week": url_for("go.week") if first != today else None,
        "on_google": calendar_available(app.settings),
    }


def _keep(**values: str) -> dict[str, str]:
    """The address's own arguments, with these changed; an empty value drops one."""
    kept = {key: value for key, value in request.args.items() if key in ("from",)}
    kept.update({key: value for key, value in values.items() if value})
    return kept


def _named(people: list[Member], name: str) -> Member | None:
    return next((p for p in people if p.display_name.casefold() == name.casefold()), None)


def _free(rows: list[dict[str, Any]], when: date, iso: str) -> list[tuple[int, int]]:
    """The free stretches of a day between the day's bounds, the plans on it taken out: a
    timed plan takes its own time (two hours when it has no end), an all-day one the day."""
    if any(row["all_day"] and row["status"] != "cancelled" for row in rows):
        return []
    busy = []
    for row in rows:
        if row["all_day"] or row["status"] == "cancelled":
            continue
        # A plan over several days takes this one from its start, or from midnight, to its end,
        # or to midnight.
        start = _minutes(row["start_value"]) if row["start_value"][:10] == iso else 0
        if row.get("end_value"):
            end = _minutes(row["end_value"]) if row["end_value"][:10] == iso else 24 * 60
        else:
            end = start + ASSUMED_MINUTES
        busy.append((start, min(end, 24 * 60)))
    spans: list[tuple[int, int]] = []
    cursor = DAY_START
    for left, right in sorted(busy):
        if left > cursor:
            spans.append((cursor, min(left, DAY_END)))
        cursor = max(cursor, right)
        if cursor >= DAY_END:
            break
    if cursor < DAY_END:
        spans.append((cursor, DAY_END))
    return [(a, b) for a, b in spans if b - a >= 30]


def _minutes(value: str) -> int:
    """Minutes after midnight of a "YYYY-MM-DDTHH:MM" value."""
    return int(value[11:13]) * 60 + int(value[14:16])


def _due(
    conn: Any,
    visitor: auth.Visitor,
    first: date,
    last: date,
    tz: Any,
    today: date,
    slots: dict[str, int],
    grown_up: bool,
) -> list[dict[str, Any]]:
    """The to-dos due on the days shown, as small marks on their day."""
    if not (visitor.may("change") or visitor.may("own_tasks")):
        return []
    own = None if grown_up else visitor.member.id if visitor.member else None
    if own is None and not grown_up:
        return []
    found = presents.visible_tasks(
        conn, task_store.list_all(conn, status="open", owner_id=own), visitor.member
    )
    rows = []
    for task in found:
        if not task.due_at:
            continue
        day = views.local_day(task.due_at, tz)
        if first.isoformat() <= day <= last.isoformat():
            rows.append({**views.todo_row(task, tz, today, slots, kid=not grown_up), "day": day})
    return rows


def _plate(
    conn: Any, visitor: auth.Visitor, today: date, tz: Any, slots: dict[str, int]
) -> list[dict[str, Any]]:
    """On your plate: what has no day yet, and what is late, whatever week is showing."""
    found = presents.visible_tasks(
        conn, task_store.list_all(conn, status="open", owner_id=None), visitor.member
    )
    rows = [views.todo_row(task, tz, today, slots) for task in found]
    return [
        row
        for row, task in zip(rows, found, strict=True)
        if not task.due_at or row["late"] or (task.preferred_window and not task.due_at)
    ]


def _pencil(
    conn: Any, kept: set[int], first: date, last: date, today: date
) -> dict[str, Any] | None:
    """At most one of her own picks, in pencil on a free weekend stretch (docs/INTERFACE.md):
    the weekend set's first pick with a day inside the week, never a present kept from this
    person, never on a day gone."""
    found = pick_store.current(conn, today=today.isoformat())
    if found is None or found.window != "weekend":
        return None
    for tile in found.picks:
        if not tile.get("idea_id") or tile["idea_id"] in kept:
            continue
        when = tile.get("when", "")
        day = _weekend_day(when, first, last, today)
        if day is None:
            continue
        return {
            "day": day.isoformat(),
            "title": tile["title"],
            "why": tile.get("why", ""),
            "href": url_for("web.idea", idea_id=tile["idea_id"]),
        }
    return None


def _weekend_day(when: str, first: date, last: date, today: date) -> date | None:
    """The first weekend day inside the week that a pick's "Sat", "Sun" or "Sat or Sun" names."""
    wanted = {name[:3].casefold() for name in when.replace(" or ", " ").split()}
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        if day >= today and day.weekday() >= 5 and f"{day:%a}".casefold() in wanted:
            return day
    return None


def _went(conn: Any, first: date, last: date, slots: dict[str, int]) -> list[dict[str, Any]]:
    """How the outings on these days went, with the idea each was."""
    rows = []
    for outcome in outcome_store.recent(conn, since=first.isoformat()):
        if outcome.happened_on > last.isoformat():
            continue
        idea = idea_store.get(conn, outcome.idea_id) if outcome.idea_id else None
        rows.append(_memory(outcome, idea, slots))
    return rows


# -- The kitchen tablet ---------------------------------------------------------------------------

# Ideas on the board's edge: the newest few in full, the rest smaller, fading as they rest.
BOARD_FRESH = 4
BOARD_IDEAS = 12
BOARD_LIST = 12
# From Thursday the weekend's picks lead the board (docs/INTERFACE.md section 8).
WEEKEND_FROM = 3


@bp.get("/board")
def board() -> str:
    """The kitchen tablet (docs/INTERFACE.md section 8): Now drawn as one surface for the family
    at the wall. A large box with faces along the top; today and tomorrow in the middle, largest;
    anything waiting on a person and the shopping list in places of their own; her picks, the
    weekend's from Thursday; the saved ideas along the bottom, the untouched ones fading. Costs
    and the back office never appear. Read like Now, no model call."""
    app = _app()
    today = app.clock.today()
    visitor = auth.visitor()
    shown = _days(app, today, today + timedelta(days=1))
    with closing(app.connect()) as conn:
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        kept = presents.kept_ids(conn, visitor.member)
        questions = now._questions(conn, app, visitor, today, slots, people)[: now.MOST_QUESTIONS]
        mine = visitor.member.id if chat.is_kid() and visitor.member else None
        window = "weekend" if today.weekday() >= WEEKEND_FROM else "now"
        found = pick_store.latest(conn, window=window, member_id=mine)
        if found is None or found.window_end < today.isoformat():
            found = pick_store.current(conn, member_id=mine, today=today.isoformat())
        picks = now.pick_set(app, found, kept) if found is not None else None
        shopping = _shopping(conn) if visitor.may("change") else None
        stale = utc_iso(app.clock.now() - timedelta(days=routes.FADE_DAYS))
        saved = sorted(
            (
                idea
                for idea in idea_store.list_all(conn)
                if idea.id not in kept and idea.status == "idea" and not idea_store.is_gift(idea)
            ),
            key=lambda idea: idea.updated_at,
            reverse=True,
        )[:BOARD_IDEAS]
        chat.page_box(app, conn, people, prompt=views.BOARD_PROMPT, faces=True)
    return render_template(
        "board.html",
        days=shown["days"],
        questions=questions,
        picks=picks,
        shopping=shopping,
        someday=[
            {
                "title": idea.title,
                "href": url_for("web.idea", idea_id=idea.id),
                "fresh": number < BOARD_FRESH,
                "resting": idea.updated_at < stale,
            }
            for number, idea in enumerate(saved)
        ],
    )


def _shopping(conn: Any) -> dict[str, Any]:
    """The shopping list, which always hangs on the board: what is still to get."""
    ref = list_store.find(conn, "shopping")
    held = list_store.items(conn, ref) if ref is not None else []
    waiting = [item.text for item in held if item.ticked_at is None]
    return {"items": waiting[:BOARD_LIST], "more": max(0, len(waiting) - BOARD_LIST)}


# -- What about ----------------------------------------------------------------------------------


@bp.get("/about")
def about() -> str:
    """What about… (docs/INTERFACE.md section 4): her picks as a destination of their own, the
    set for the next few hours and the weekend's, each with the line that drove it and when it was
    chosen. Made ahead by the picks job (familydb/picks.py); the page only reads them. A kid sees
    the set made for her."""
    app = _app()
    today = app.clock.today()
    visitor = auth.visitor()
    mine = visitor.member.id if chat.is_kid() and visitor.member else None
    with closing(app.connect()) as conn:
        kept = presents.kept_ids(conn, visitor.member)
        sets = []
        for window in pick_store.WINDOWS:
            found = pick_store.latest(conn, window=window, member_id=mine)
            if found is None or found.window_end < today.isoformat():
                continue
            shown = now.pick_set(app, found, kept)
            if shown is not None:
                sets.append({**shown, "title": views.PICK_WINDOWS[window]})
        first_day = not idea_store.list_all(conn, include_dropped=True)
        people = member_store.list_all(conn)
        chat.page_box(app, conn, people, scope={"label": "What about", "text": "About your picks:"})
    if not app.settings.picks:
        empty = views.PICKS_OFF
    elif first_day:
        empty = views.FIRST_PICKS.format(name=personas.active(app.settings).name)
    else:
        empty = views.NO_PICKS_YET
    return render_template(
        "about.html",
        sets=sets,
        summary=next((one["header"] for one in sets if one["header"]), None)
        or (views.PICKS_SUMMARY if sets else None),
        empty=empty,
        different=now.DIFFERENT,
    )


def _memory(outcome: Any, idea: Any, slots: dict[str, int]) -> dict[str, Any]:
    face = None
    if outcome.rating is not None:
        face = (
            "loved"
            if outcome.rating >= LOVED_FROM
            else "ok"
            if outcome.rating >= OK_FROM
            else "not-great"
        )
    people = views.people_for(idea, slots)
    return {
        "id": outcome.id,
        "idea_id": idea.id if idea else None,
        "title": idea.title if idea else "Something",
        "day": outcome.happened_on,
        "when": views.day_short(date.fromisoformat(outcome.happened_on)),
        "people": people,
        "who": views.names_text(people),
        "face": face,
        "face_words": FACE_WORDS.get(face or "", ""),
        "again": outcome.would_repeat,
        "notes": outcome.notes,
        "rating": outcome.rating,
        "status": idea.status if idea else None,
        "kind": idea.kind if idea else None,
    }


def _forecasts(app: App, first: date, last: date, today: date) -> dict[date, Any]:
    """The forecast for the days shown, when home is set; a failure is a week without one."""
    if not weather_available(app.settings):
        return {}
    try:
        return {f.date: f for f in forecast_days(app.weather, first, last, today)}
    except Exception as exc:  # the page must not fail for the weather
        log.warning("no forecast for the week page: %s", exc)
        return {}


# -- A plan ----------------------------------------------------------------------------------------


@bp.get("/plan/<int(max=9223372036854775807):plan_id>")
def plan(plan_id: int) -> str:
    """A plan's own page (docs/INTERFACE.md section 5): when, the leave-by, who, where, what it
    is a plan of, and after the day how it went. Moving and taking it off are its forms."""
    app = _app()
    today = app.clock.today()
    tz = app.settings.tzinfo
    visitor = auth.visitor()
    with closing(app.connect()) as conn:
        found = plan_store.get(conn, plan_id)
        idea = idea_store.get(conn, found.idea_id) if found and found.idea_id else None
        if found is None or presents.is_kept_from(conn, idea, visitor.member):
            abort(404)
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        place = place_store.get(conn, idea.place_id) if idea and idea.place_id else None
        went = (
            [
                _memory(outcome, idea, slots)
                for outcome in outcome_store.list_for_idea(conn, idea.id)
                if outcome.plan_id == found.id or outcome.happened_on == found.start[:10]
            ]
            if idea
            else []
        )
        rate = (
            [
                r
                for r in routes._unrated(conn, today, slots, visitor.member)
                if r["plan_id"] == plan_id
            ]
            if visitor.may("change")
            else []
        )
        chat.page_box(
            app,
            conn,
            people,
            prompt=chat.ITEM_PROMPT,
            scope={
                "label": found.title,
                "text": f"About the plan {found.title} ({found.start[:10]}):",
            },
        )
    row = views.plan_row(found, today)
    away = views.away_from_home(place, app.settings)
    who = views.people_for(idea, slots)
    return render_template(
        "plan.html",
        plan=found,
        row=row,
        idea=idea,
        state=views.plan_state(found, today, tz),
        leave_by=views.leave_by(found, away, tz),
        away=away.words if away else None,
        people=who,
        people_words=views.names_text(who),
        place=views.place_panel(place, app.clock.now(), app.settings.place_stale_days, today)
        if place
        else None,
        went=went,
        rate=rate,
        day_href=url_for("go.day", day=found.start[:10]),
        on_google=calendar_available(app.settings),
    )


# -- What we did -----------------------------------------------------------------------------------


@bp.get("/did")
def did() -> str:
    """Recent outings, newest first, with the face each got; what is still to rate first. The
    chips narrow to the loved ones, to this time last year, to the favorites (one row a place
    loved on average), or to one person's."""
    app = _app()
    today = app.clock.today()
    visitor = auth.visitor()
    grown_up = visitor.may("browse")
    loved_only = request.args.get("loved") == "1"
    last_year = request.args.get("year") == "1"
    favorites = request.args.get("fav") == "1"
    who = request.args.get("who", "").strip()
    a_year_ago = _a_year_before(today)
    around = (
        (a_year_ago - timedelta(days=AROUND_DAYS)).isoformat(),
        (a_year_ago + timedelta(days=AROUND_DAYS)).isoformat(),
    )
    with closing(app.connect()) as conn:
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        kept = presents.kept_ids(conn, visitor.member)
        back = FAVORITE_DAYS if favorites else (DID_DAYS if not last_year else 400)
        since = (today - timedelta(days=back)).isoformat()
        rows = []
        for outcome in outcome_store.recent(conn, since=since):
            if outcome.idea_id in kept:
                continue
            if last_year and not around[0] <= outcome.happened_on <= around[1]:
                continue
            idea = idea_store.get(conn, outcome.idea_id) if outcome.idea_id else None
            row = _memory(outcome, idea, slots)
            if (
                not grown_up
                and visitor.member
                and not views.names_in(row["people"], visitor.member)
            ):
                continue
            if loved_only and row["face"] != "loved":
                continue
            if who and not views.names_in(row["people"], _named(people, who)):
                continue
            rows.append(row)
        if favorites:
            rows = _favorites(rows)
        rate = routes._unrated(conn, today, slots, visitor.member) if visitor.may("change") else []
        chat.page_box(
            app, conn, people, scope={"label": "What we did", "text": "About what we did:"}
        )
    chips = [
        {"label": "Loved", "href": url_for("go.did", loved="1"), "on": loved_only},
        {"label": "Favorites", "href": url_for("go.did", fav="1"), "on": favorites},
        {"label": "This time last year", "href": url_for("go.did", year="1"), "on": last_year},
    ]
    if grown_up:
        chips += [
            {
                "label": person.display_name,
                "href": url_for("go.did", who=person.display_name),
                "on": who.casefold() == person.display_name.casefold(),
            }
            for person in people
        ]
    narrowed = loved_only or favorites or last_year or bool(who)
    if narrowed:
        chips.insert(0, {"label": "Everything", "href": url_for("go.did"), "on": False})
    return render_template(
        "did.html",
        rows=rows,
        rate=[] if narrowed else rate,
        chips=chips,
        summary=views.did_summary(rows, [] if narrowed else rate),
        narrowed=narrowed,
        last_year=last_year,
        favorites=favorites,
    )


# What "this time last year" takes in, either side of the day a year ago.
AROUND_DAYS = 31
# How far back the favorites look, and what makes one: loved on average.
FAVORITE_DAYS = 730


def _a_year_before(day: date) -> date:
    try:
        return day.replace(year=day.year - 1)
    except ValueError:  # the 29th of February
        return day.replace(year=day.year - 1, day=28)


def _favorites(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row a place the family loved on average, its latest outing, the most loved first."""
    by_idea: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        if row["idea_id"] is not None and row["rating"] is not None:
            by_idea.setdefault(row["idea_id"], []).append(row)
    found = []
    for outings in by_idea.values():
        average = sum(row["rating"] for row in outings) / len(outings)
        if average < LOVED_FROM:
            continue
        times = len(outings)
        found.append(
            {
                **outings[0],  # the latest, as `recent` gives them newest first
                "face": "loved",
                "face_words": "Loved it" if times == 1 else f"Loved it, {times} times",
                "average": average,
            }
        )
    found.sort(key=lambda row: (-row["average"], row["title"].casefold()))
    return found


@bp.get("/did/<int(max=9223372036854775807):outcome_id>")
def outing(outcome_id: int) -> str:
    """One outing (a memory, docs/INTERFACE.md section 5): what, when, who went, the face it got,
    what was said about it, the times before; Again? and What made it good? as forms. A kid sees
    an outing she went on, never one of a present kept from her."""
    app = _app()
    today = app.clock.today()
    visitor = auth.visitor()
    with closing(app.connect()) as conn:
        found = outcome_store.get(conn, outcome_id)
        if found is None:
            abort(404)
        idea = idea_store.get(conn, found.idea_id) if found.idea_id else None
        if presents.is_kept_from(conn, idea, visitor.member):
            abort(404)
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        row = _memory(found, idea, slots)
        if not visitor.may("browse") and not (
            visitor.member and views.names_in(row["people"], visitor.member)
        ):
            abort(404)
        plan = plan_store.get(conn, found.plan_id) if found.plan_id else None
        before = (
            [
                _memory(other, idea, slots)
                for other in outcome_store.list_for_idea(conn, idea.id)
                if other.id != found.id
            ]
            if idea
            else []
        )
        names = {person.id: person.display_name for person in people}
        chat.page_box(
            app,
            conn,
            people,
            prompt=chat.ITEM_PROMPT,
            scope={
                "label": row["title"],
                "text": f"About {row['title']} on {found.happened_on}:",
            },
        )
    box = chat.current_box()
    box["starters"] = views.outing_starters(row)
    return render_template(
        "did_one.html",
        m=row,
        idea=idea,
        plan=plan,
        day_words=views.day_text(found.happened_on),
        before=sorted(before, key=lambda one: one["day"], reverse=True)[:6],
        by=names.get(found.recorded_by or -1),
        reasons=views.GOOD_REASONS,
        today=today,
    )


def kid_may_see(member: Member | None) -> bool:
    """A kid sees what she went to (docs/INTERFACE.md section 4)."""
    return member is not None and roles.may(member.role, "sign_in")
