"""The plans pages: what is coming and what just happened, the month, and what is on near
home (named once, in happening.py) with one find in full."""

from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta
from typing import Any

from flask import (
    abort,
    request,
    url_for,
)

from familydb import agenda, happening, presents
from familydb.availability import calendar_available, happening_available
from familydb.base.dates import weekend_window
from familydb.store import finds as find_store
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.web import (
    auth,
    calendar_view,
    chat,
    page_rows,
    views,
)
from familydb.web.answers import answer
from familydb.web.pages import MAX_ID, bp, familydb_app, who_asks

PLANS_AHEAD_DAYS = 90


# The most things near home one page lists: four weeks of a busy city's calendars.
HAPPENING_MOST = 300


PLANS_BEHIND_DAYS = 30


def _month(asked: str | None, today: date) -> date:
    """The first of the month asked for as YYYY-MM, or of this one; anything else is a 404."""
    if not asked:
        return today.replace(day=1)
    try:
        first = date.fromisoformat(f"{asked}-01")
    except ValueError:
        abort(404)
    if not 2000 <= first.year <= 2100:
        abort(404)
    return first


def _months(rows: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plans under the month they begin in ("October", and the year when it is not this one)."""
    groups: list[dict[str, Any]] = []
    for row in rows:
        day = date.fromisoformat(row["day"])
        title = f"{day:%B}" + (f" {day.year}" if day.year != today.year else "")
        if not groups or groups[-1]["title"] != title:
            groups.append({"title": title, "rows": []})
        groups[-1]["rows"].append(row)
    return groups


@bp.get("/plans")
def plans() -> str:
    """What is coming, by month, and what was lately; for a kid, one list of what is next."""
    app = familydb_app()
    today = app.clock.today()
    with closing(app.connect()) as conn:
        seen = agenda.read(
            app,
            conn,
            today - timedelta(days=PLANS_BEHIND_DAYS),
            today + timedelta(days=PLANS_AHEAD_DAYS),
        )
        on = presents.without(seen.entries, presents.kept_ids(conn, auth.visitor().member))
        people = member_store.list_all(conn)
        rows = page_rows.plan_rows(conn, app, on, today, views.slot_map(people), None, past=True)
        asking = who_asks(conn)
    horizon = today.isoformat()
    upcoming = [row for row in rows if row["end"] >= horizon]
    recent = [row for row in rows if row["end"] < horizon][::-1]
    return answer(
        "plans.html",
        months=_months(upcoming, today),
        upcoming=upcoming,
        recent=recent,
        ahead=PLANS_AHEAD_DAYS,
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
        today=today.isoformat(),
        on_google=calendar_available(app.settings),
        **asking,
    )


@bp.get("/happening")
@bp.get("/soon")
def happening_page() -> str:
    """Happening soon (docs/INTERFACE.md section 4): what is on near home in the weeks ahead, as
    the family's sources list it, and the family's own things with a closing date, by day."""
    app = familydb_app()
    today = app.clock.today()
    visitor = auth.visitor()
    weekend_only = request.args.get("when") == "weekend"
    free_only = request.args.get("free") == "1"
    source = request.args.get("source", "").strip()
    with closing(app.connect()) as conn:
        found = find_store.upcoming(
            conn,
            start=today,
            end=today + timedelta(days=happening.HORIZON_DAYS),
            limit=HAPPENING_MOST,
        )
        troubled = [one for one in find_store.sources(conn) if not one.ok]
        kept = presents.kept_ids(conn, visitor.member)
        ending = [
            idea
            for idea in idea_store.ending_between(
                conn,
                today.isoformat(),
                (today + timedelta(days=happening.HORIZON_DAYS)).isoformat(),
            )
            if idea.id not in kept
        ]
        people = member_store.list_all(conn)
        chat.page_box(
            app,
            conn,
            people,
            scope={"label": "Happening soon", "text": "About what is on near home:"},
        )
    sources = sorted({views.find_row(one, today)["who"] for one in found})
    if source:
        found = [one for one in found if views.find_row(one, today)["who"] == source]
    days = views.happening_days(found, today, own=ending, kid=not visitor.may("browse"))
    if weekend_only:
        saturday, sunday = weekend_window(today)
        days = [day for day in days if saturday.isoformat() <= day["iso"] <= sunday.isoformat()]
    if free_only:
        days = [{**day, "rows": [row for row in day["rows"] if row["free"]]} for day in days]
        days = [day for day in days if day["rows"]]
    chips = [
        {
            "label": "This weekend",
            "href": url_for("web.happening_page", when="weekend"),
            "on": weekend_only,
        },
        {"label": "Free", "href": url_for("web.happening_page", free="1"), "on": free_only},
    ]
    if visitor.may("browse"):
        chips += [
            {"label": one, "href": url_for("web.happening_page", source=one), "on": source == one}
            for one in sources[:8]
        ]
    if any(chip["on"] for chip in chips):
        chips.insert(0, {"label": "Everything", "href": url_for("web.happening_page"), "on": False})
    return answer(
        "soon.html",
        name=happening.NAME,
        days=days,
        chips=chips,
        summary=views.soon_summary(days, today),
        ahead=happening.HORIZON_DAYS,
        reading=happening_available(app.settings),
        trouble=[views.find_source_row(one, app.settings.tzinfo) for one in troubled]
        if visitor.may("browse")
        else [],
    )


@bp.get(f"/soon/<int(max={MAX_ID}):find_id>")
def find(find_id: int) -> str:
    """A happening (docs/INTERFACE.md section 5): what a source listed near home, when and where,
    the listing in its own words; Save it (`add_idea`) and Put it on the calendar
    (`create_event`) as forms, for whoever may change things. A kid sees it without its source."""
    app = familydb_app()
    today = app.clock.today()
    visitor = auth.visitor()
    with closing(app.connect()) as conn:
        found = find_store.get(conn, find_id)
        if found is None:
            abort(404)
        people = member_store.list_all(conn)
        box = chat.page_box(
            app,
            conn,
            people,
            prompt=chat.ITEM_PROMPT,
            scope={
                "label": found.title,
                "text": f"About {found.title} ({found.starts_at[:10]}), listed near home:",
            },
        )
    box["starters"] = views.find_starters(found, today)
    row = views.find_row(found, today)
    first = found.starts_at[:10]
    last = found.ends_at[:10] if found.ends_at else first
    return answer(
        "find.html",
        find=found,
        row=row,
        state=views.find_state(found, today),
        over=last < today.isoformat(),
        kid=not visitor.may("browse"),
        first=first,
        time=found.starts_at[11:16] if "T" in found.starts_at else "",
        last=last if last != first else "",
        where=", ".join(part for part in (found.venue, found.address) if part),
        on_google=calendar_available(app.settings),
    )


@bp.get("/plans/month")
def plans_month() -> str:
    """One month as a calendar, with what is coming in it and what is waiting to be rated."""
    app = familydb_app()
    today = app.clock.today()
    first = _month(request.args.get("month"), today)
    weeks_first = first - timedelta(days=first.weekday())
    last_day = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    weeks_last = last_day + timedelta(days=6 - last_day.weekday())
    with closing(app.connect()) as conn:
        seen = agenda.read(app, conn, weeks_first, weeks_last)
        on = presents.without(seen.entries, presents.kept_ids(conn, auth.visitor().member))
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        rows = page_rows.plan_rows(conn, app, on, today, slots, None, past=True)
        rate = (
            page_rows.unrated(conn, today, slots, auth.visitor().member)
            if auth.visitor().may("change")
            else []
        )
    previous = (first - timedelta(days=1)).replace(day=1)
    following = last_day + timedelta(days=1)
    weeks = calendar_view.month_calendar(rows, first, today, {row["plan_id"] for row in rate})
    start = max(today, first).isoformat()
    coming = [
        row
        for row in rows
        if row["end"] >= start
        and row["day"] <= last_day.isoformat()
        and row["end"] >= first.isoformat()
    ]
    return answer(
        "plans_month.html",
        month=f"{first:%B %Y}",
        weeks=weeks,
        coming=coming,
        rate=rate,
        key_people=[views.person_of(p.display_name, slots) for p in people],
        previous=f"{previous:%Y-%m}",
        following=f"{following:%Y-%m}",
        previous_name=f"{previous:%B %Y}",
        following_name=f"{following:%B %Y}",
        this_month=first == today.replace(day=1),
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
    )
