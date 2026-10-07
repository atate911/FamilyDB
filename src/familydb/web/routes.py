"""The pages. Every view reads; nothing here writes to the database."""

from __future__ import annotations

import json
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

from familydb import agenda, personas, presents, roles
from familydb.app import App
from familydb.availability import calendar_available, enrichment_available
from familydb.dates import next_birthday, utc_iso
from familydb.store import calls
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import memories as memory_store
from familydb.store import messages as message_store
from familydb.store import outcomes as outcome_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.store import tasks as task_store
from familydb.store import wishes as wish_store
from familydb.store.ideas import KIND_SUGGESTIONS
from familydb.web import auth, chat, shell, views
from familydb.web import status as status_page
from familydb.web.chat import WHO_KEY

bp = Blueprint("web", __name__)

LIST_LIMIT = 200
# Ideas shown to a page, and the orders the list can be put in.
IDEAS_PAGE = 24
SORTS = {"new": "Newest first", "near": "Nearest first", "az": "A to Z"}
MAX_ID = 2**63 - 1  # beyond this SQLite raises rather than simply finding nothing
STATUSES = ("idea", "planned", "done", "dropped")
SETTINGS = ("either", "indoor", "outdoor")
WEATHERS = ("any", "dry", "warm", "snow")
SEASONS = ("spring", "summer", "autumn", "winter")
COSTS = ((0, "free"), (1, "cheap"), (2, "moderate"), (3, "pricey"), (4, "expensive"))
RESTAURANT_KIND = "restaurant"
FILTERS = ("q", "kind", "status", "who")
HOME_AHEAD_DAYS = 60
# A kid's To do page keeps what she ticked off this long, with a way to undo it.
DONE_LATELY_DAYS = 7
HOME_PLANS = 4
HOME_IDEAS = 4
HOME_TASKS = 4
PLANS_AHEAD_DAYS = 90
PLANS_BEHIND_DAYS = 30
# The home-screen icon's ground (static/brand/icon-512.png), which the manifest's colours match so
# opening the app is one colour from the icon to the splash.
ICON_GROUND = "#0e1312"


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _who(conn: Any) -> dict[str, Any]:
    """What every form needs to say who is doing this."""
    return {
        "family": [member.display_name for member in member_store.list_all(conn)],
        "who": session.get(WHO_KEY),
    }


def _choices(rows: list[Any]) -> tuple[list[str], list[str]]:
    """The kinds and participants in use, for the filters."""
    kinds = sorted({row.kind for row in rows})
    people = sorted({name for row in rows for name in row.participants})
    return kinds, people


@bp.get("/healthz")
def healthz() -> Response:
    """A liveness check for a monitor or proxy, open before sign-in."""
    return Response("ok\n", mimetype="text/plain")


@bp.get("/manifest.webmanifest")
def manifest() -> Response:
    """The home-screen manifest. Open before sign-in: a phone asks without the cookie, and it says
    nothing the sign-in page does not."""
    title = _app().settings.web_title
    large = url_for("static", filename="brand/icon-512.png")
    icons = [
        {"src": url_for("static", filename="brand/apple-touch-icon.png"), "sizes": "180x180"},
        {"src": large, "sizes": "512x512"},
        {"src": large, "sizes": "512x512", "purpose": "maskable"},
    ]
    body = {
        "name": title,
        "short_name": title,
        "id": "/",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": ICON_GROUND,
        "theme_color": ICON_GROUND,
        "icons": [{**icon, "type": "image/png"} for icon in icons],
    }
    return Response(json.dumps(body, sort_keys=True), mimetype="application/manifest+json")


@bp.get("/more")
def more() -> str:
    """The phone's menu: what is not in the tab bar, and signing out. It opens from the picture at
    the top of every page and is not a page on a wide screen, where the sidebar holds all of it."""
    return render_template("more.html")


@bp.get("/status")
def status() -> str:
    app = _app()
    with closing(app.connect()) as conn:
        admins = [
            one.display_name
            for one in member_store.list_all(conn)
            if one.role == "admin" and one.active
        ]
        # A grown-up who isn't an admin reads the page as information: who can act on it.
        who_can = "" if auth.visitor().manages else views.who_can_change(admins)
        return render_template("status.html", who_can=who_can, **status_page.status(app, conn))


@bp.get("/")
def home() -> Response | str:
    """The box (the chat's own, posting to it) around what is coming up, to do and new. No model
    call. An admin is sent to setup until the bot can answer anyone."""
    if any(request.args.get(key) for key in FILTERS):
        # Home takes no search; an old bookmark's goes on to the ideas list.
        return redirect(url_for("web.ideas", **request.args))
    app = _app()
    now = app.clock.now()
    today = app.clock.today()
    tz = app.settings.tzinfo
    visitor = auth.visitor()
    manages = visitor.manages
    # The box is the chat's, so only for a role that may chat.
    talks = visitor.may("chat")
    kid = chat.is_kid()
    # For somebody who does not browse the household (a kid): only what is hers (docs/STYLE.md).
    browsing = visitor.may("browse")
    with closing(app.connect()) as conn:
        progress = status_page.setup_progress(app, conn)
        if manages and not status_page.ready_to_answer(progress):
            return redirect(url_for("setup.overview"))
        seen = agenda.read(app, conn, today, today + timedelta(days=HOME_AHEAD_DAYS))
        kept = presents.kept_ids(conn, visitor.member)
        on = _no_gifts(seen.entries, kept)
        everything = [idea for idea in idea_store.list_all(conn) if idea.id not in kept]
        unfinished = status_page.setup_steps(app, conn) if manages else []
        people = member_store.list_all(conn)
        todo = presents.visible_tasks(
            conn, task_store.list_all(conn, status="open", owner_id=_own_only()), visitor.member
        )
        me = visitor.member.id if visitor.member else None
        todo = views.todo_order(todo, app.settings.tzinfo, today, me)
        talk = chat.glance(app, conn) if talks else None
        wished = wish_glance(conn, today)
        slots = views.slot_map(people)
        coming = _plan_rows(conn, app, on, today, slots, visitor.member if not browsing else None)
        rating = _to_rate(conn, today, slots) if visitor.may("change") else None
        newest = sorted(everything, key=lambda idea: idea.created_at, reverse=True)[:HOME_IDEAS]
        mini = [_idea_mini(conn, app, idea) for idea in newest]
        today_card = status_page.vera_today(app, conn) if browsing else None
        left = chat.messages_left(app, conn, visitor.member)
    late = sum(views.is_late(task, tz, today) for task in todo)
    family = [member.display_name for member in people]
    yes = _latest_yes(wished, people) if wished and not wished["parent"] else None
    line = views.home_line(
        coming,
        late,
        plans_href=url_for("web.plans_month" if browsing else "web.plans"),
        todo_href=url_for("web.tasks"),
        list_href=url_for("web.wishes"),
        kid=not browsing,
        others=_others(coming, visitor.member),
        yes=yes,
    )
    return render_template(
        "home.html",
        hello=views.greeting(now.astimezone(tz).hour, visitor.name),
        today=views.day_text(today.isoformat()),
        line=line,
        coming=coming[:HOME_PLANS],
        more_plans=max(0, len(coming) - HOME_PLANS),
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
        ideas=mini,
        idea_count=len(everything),
        restaurant_count=sum(1 for idea in everything if idea.kind == RESTAURANT_KIND),
        tasks=[views.todo_row(t, tz, today, slots, kid=not browsing) for t in todo[:HOME_TASKS]],
        task_count=len(todo),
        late_count=late,
        setup=unfinished,
        talk=talk,
        wishes=wished,
        kids=_kids_card(wished, people),
        rating=rating,
        vera=today_card,
        left=left,
        readers=views.names_text(
            [{"name": p.display_name} for p in people if roles.may(p.role, "decide")]
        ),
        busy=bool(talk and talk["state"] == "thinking"),
        **chat.box(family, prompt=chat.KID_HOME_PROMPT if kid else chat.HOME_PROMPT),
        typed=chat.asked(),
    )


def _plan_rows(
    conn: Any,
    app: App,
    entries: list[agenda.Entry],
    today: date,
    slots: dict[str, int],
    only_for: member_store.Member | None,
    *,
    past: bool = False,
) -> list[dict[str, Any]]:
    """What is on, with whom it is for and how far it is: what is coming, and what was too when
    `past`. With `only_for` (a kid), the ones that name her, or nobody (so everybody)."""
    rows = []
    for entry in entries:
        if entry.days()[-1] < today and not past:
            continue
        idea = idea_store.get(conn, entry.idea_id) if entry.idea_id else None
        people = views.people_for(idea, slots)
        if only_for is not None and not views.names_in(people, only_for):
            continue
        place = place_store.get(conn, idea.place_id) if idea and idea.place_id else None
        away = views.away_from_home(place, app.settings)
        row = views.entry_row(entry, today, people=people, away=away)
        # A plan whose idea has since gone is still a plan, with no page to link to.
        row["linked"] = idea is not None
        rows.append(row)
    seen: set[str] = set()
    for row in rows:  # the first plan of a day is what a link to that day lands on
        row["anchor"] = row["day"] not in seen
        seen.add(row["day"])
    return rows


def _others(coming: list[dict[str, Any]], me: member_store.Member | None) -> str:
    """For a kid's sentence: who else is on her next plan ("with Theo")."""
    if not coming or me is None:
        return ""
    named = [p for p in coming[0]["people"] if p["name"].casefold() != me.display_name.casefold()]
    return views.names_text([p for p in named if p["initial"]])


def _unrated(conn: Any, today: date, slots: dict[str, int]) -> list[dict[str, Any]]:
    """Every plan of the last two weeks nobody has said how it went, oldest first."""
    waiting = plan_store.unrated(
        conn,
        today=today.isoformat(),
        since=(today - timedelta(days=shell.RATE_DAYS)).isoformat(),
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
                "glyph": views.glyph_for(idea.kind if idea else None),
            }
        )
    return found


def _to_rate(conn: Any, today: date, slots: dict[str, int]) -> dict[str, Any] | None:
    """The oldest plan nobody has said how it went, for Home's three faces, and how many more."""
    waiting = _unrated(conn, today, slots)
    return {**waiting[0], "more": len(waiting) - 1} if waiting else None


def _idea_mini(conn: Any, app: App, idea: Any) -> dict[str, Any]:
    """A new idea as Home's small row: its picture, its title, and how far it is or that it has
    not been looked up."""
    place = place_store.get(conn, idea.place_id) if idea.place_id else None
    away = views.away_from_home(place, app.settings)
    row = views.idea_row(idea, app.settings.tzinfo)
    return {
        **row,
        "glyph": views.glyph_for(idea.kind, gift=idea_store.is_gift(idea)),
        "away": away.words if away else None,
    }


def _kids_card(wished: dict[str, Any] | None, people: list[member_store.Member]) -> list[Any]:
    """For a parent's Home: each kid with their colour, how much is on their list and what waits."""
    if not wished or not wished["parent"]:
        return []
    by_id = {person.id: person for person in people}
    cards = []
    for kid in wished["kids"]:
        person = by_id.get(kid["id"])
        waiting = sum(1 for row in wished["waiting"] if row["kid_id"] == kid["id"])
        pronoun = {"female": "her", "male": "his"}.get(person.gender or "", "their")
        cards.append(
            {
                **kid,
                "slot": person.slot or 0 if person else 0,
                "initial": views.initial_for(kid["name"], [p.display_name for p in people]),
                "waiting": waiting,
                "pronoun": pronoun,
                "top": [row["title"] for row in kid["lists"][0]["rows"][: wished["top"]]],
            }
        )
    return cards


def _latest_yes(
    wished: dict[str, Any], people: list[member_store.Member]
) -> tuple[str, str] | None:
    """A kid's latest yes: (who said it, the wish), for her sentence on Home."""
    yeses = [row for row in wished["mine"]["answered"] if row["status"] == "granted"]
    if not yeses:
        return None
    latest = max(yeses, key=lambda row: row["answered_at"] or "")
    who = next((p.display_name for p in people if p.id == latest["answered_by"]), "A grown-up")
    return who, latest["title"]


@bp.get("/ideas")
def ideas() -> str:
    app = _app()
    settings = app.settings
    visitor = auth.visitor()
    query = request.args.get("q", "").strip()
    kind = request.args.get("kind", "").strip()
    status = request.args.get("status", "").strip()
    who = request.args.get("who", "").strip()
    sort = request.args.get("sort", "new") if request.args.get("sort") in SORTS else "new"
    number = request.args.get("page", "1")
    page = int(number) if number.isdigit() and 0 < int(number) < 1000 else 1
    with closing(app.connect()) as conn:
        kept = presents.kept_ids(conn, visitor.member)
        found = idea_store.search(
            conn,
            text=query or None,
            kind=kind or None,
            status=status if status in STATUSES else None,
            participant=who or None,
            limit=LIST_LIMIT,
            exclude_ids=kept,
            newest_first=not query,
        )
        listed = [
            idea for idea in idea_store.list_all(conn, include_dropped=True) if idea.id not in kept
        ]
        kinds, people = _choices(listed)
        capture_people = member_store.list_all(conn)
        slots = views.slot_map(capture_people)
        hidden = presents.of_presents(conn, found, capture_people)
        away = {
            idea.id: views.away_from_home(place_store.get(conn, idea.place_id), settings)
            for idea in found
            if idea.place_id
        }
    filtered = bool(query or kind or status or who)
    if sort == "near":  # ideas with a drive time first, nearest first; the rest as they were
        found = sorted(
            found, key=lambda idea: (idea.id not in away, getattr(away.get(idea.id), "minutes", 0))
        )
    elif sort == "az":
        found = sorted(found, key=lambda idea: idea.title.casefold())
    pages = max(1, -(-len(found) // IDEAS_PAGE))
    page = min(page, pages)
    shown = found[(page - 1) * IDEAS_PAGE : page * IDEAS_PAGE]
    rows = [
        _idea_card(idea, settings, away.get(idea.id), slots, hidden.get(idea.id)) for idea in shown
    ]
    here = {k: v for k, v in (("q", query), ("kind", kind), ("status", status), ("who", who)) if v}
    if sort != "new":
        here["sort"] = sort
    placed = [(idea, away[idea.id]) for idea in found if away.get(idea.id)]
    live = [idea for idea in listed if idea.status != "dropped"]
    return render_template(
        "ideas.html",
        capture_people=capture_people,
        rows=rows,
        total=len(live),
        restaurant_count=sum(1 for idea in live if idea.kind == RESTAURANT_KIND),
        on_map=views.places_map(placed),
        off_map=len(found) - len(placed),
        looking_up=enrichment_available(settings),
        kinds=kinds,
        people=people,
        statuses=STATUSES,
        status_words=views.STATUS_WORDS,
        selected={"q": query, "kind": kind, "status": status, "who": who},
        filter_words=views.filter_words(kind, who, status),
        filtered=filtered,
        limit=LIST_LIMIT,
        found_count=len(found),
        sort=sort,
        sorts=SORTS,
        page_size=IDEAS_PAGE,
        page=page,
        pages=pages,
        earlier=url_for("web.ideas", **here, page=page - 1) if page > 1 else None,
        later=url_for("web.ideas", **here, page=page + 1) if page < pages else None,
    )


def _idea_card(
    idea: Any,
    settings: Any,
    away: Any,
    slots: dict[str, int],
    kept: presents.Kept | None,
) -> dict[str, Any]:
    """An idea as the cards draw it: its words, its picture, whom it is for, how far it is, and
    whom it is hidden from if it is a present."""
    people = views.people_for(idea, slots)
    return {
        **views.idea_row(idea, settings.tzinfo, hidden=kept.words if kept else None),
        "glyph": views.glyph_for(idea.kind, gift=idea_store.is_gift(idea)),
        "people": people,
        "who": views.names_text(people),
        "away": away.words if away else None,
        "went": views.went_text(idea),
    }


@bp.get(f"/idea/<int(max={MAX_ID}):idea_id>")
def idea(idea_id: int) -> str:
    app = _app()
    settings = app.settings
    now = app.clock.now()
    today = app.clock.today()
    visitor = auth.visitor()
    with closing(app.connect()) as conn:
        record = idea_store.get(conn, idea_id)
        if record is None or presents.is_kept_from(conn, record, visitor.member):
            abort(404)
        original = (
            message_store.get(conn, record.source_message_id) if record.source_message_id else None
        )
        place = place_store.get(conn, record.place_id) if record.place_id else None
        outcomes = outcome_store.list_for_idea(conn, idea_id)
        plans = plan_store.for_idea(conn, idea_id)
        asking = _who(conn)
        looked_up = calls.last_lookup_turn(conn, idea_id) if visitor.may("manage") else None
        family = member_store.list_all(conn)
        slots = views.slot_map(family)
        kept = presents.of_presents(conn, [record], family).get(idea_id)
    away = views.away_from_home(place, settings)
    card = _idea_card(record, settings, away, slots, kept)
    return render_template(
        "idea.html",
        idea=record,
        original_message=message_store.as_said(original.text) if original else None,
        original_by=views.original_by(original, family, settings.tzinfo) if original else None,
        today=today.isoformat(),
        can_schedule=True,  # FamilyDB keeps its own plans, and copies them to Google when it can
        on_google=calendar_available(settings),
        can_look_up=enrichment_available(settings) and record.status != "dropped",
        looked_up=looked_up,
        lookups=views.lookups_when(settings),
        **asking,
        row=card,
        setting=views.SETTINGS.get(record.setting, record.setting),
        weather=views.WEATHER.get(record.weather),
        place=views.place_panel(place, now, settings.place_stale_days, today),
        outcomes=[views.outcome_row(o) for o in reversed(outcomes)],
        plans=[views.plan_row(p, today) for p in reversed(plans)],
        plan_state=_plan_state(plans, today),
        mine=bool(visitor.member and record.suggested_by == visitor.member.id),
    )


def _plan_state(plans: list[Any], today: date) -> str:
    """Where an idea's plans stand: "ahead" (one to come), "past" (only done ones) or "none"."""
    live = [plan for plan in plans if plan.status != "cancelled"]
    if any((plan.end or plan.start)[:10] >= today.isoformat() for plan in live):
        return "ahead"
    return "past" if live else "none"


def _idea_form(record: Any = None) -> str:
    app = _app()
    with closing(app.connect()) as conn:
        everything = idea_store.list_all(conn, include_dropped=True)
        visitor = auth.visitor()
        if record is not None and presents.is_kept_from(conn, record, visitor.member):
            abort(404)
        kinds = sorted({row.kind for row in everything})
        people = member_store.list_all(conn)
        kept = presents.of_presents(conn, [record], people).get(record.id) if record else None
        by = (
            next((m.display_name for m in people if m.id == record.suggested_by), None)
            if record
            else None
        )
    family = [member.display_name for member in people]
    return render_template(
        "idea_form.html",
        idea=record,
        revision=idea_store.revision(record) if record else None,
        kinds=sorted(set(kinds) | set(KIND_SUGGESTIONS)),
        statuses=STATUSES,
        status_words=views.STATUS_WORDS,
        settings=SETTINGS,
        weathers=WEATHERS,
        seasons=SEASONS,
        costs=COSTS,
        family=family,
        keepable=[
            member for member in people if member.active and roles.may(member.role, "decide")
        ],
        kept_ids=sorted(kept.ids) if kept else [],
        suggested_by=by,
        added=views.day_short(
            date.fromisoformat(views.local_day(record.created_at, app.settings.tzinfo))
        )
        if record
        else None,
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


@bp.get("/memory")
def memory() -> str:
    app = _app()
    with closing(app.connect()) as conn:
        everything = memory_store.list_all(conn)
        people = member_store.list_all(conn)
    return render_template(
        "memory.html",
        **views.memory_page(everything, people, app.clock.today(), app.settings.tzinfo),
        people=people,
        slots=views.slot_map(people),
        kinds=views.MEMORY_KINDS,
    )


@bp.get("/restaurants")
def restaurants() -> str:
    app = _app()
    now = app.clock.now()
    today = app.clock.today()
    stale_days = app.settings.place_stale_days
    with closing(app.connect()) as conn:
        kept = presents.kept_ids(conn, auth.visitor().member)
        found = idea_store.search(
            conn, kind=RESTAURANT_KIND, limit=LIST_LIMIT, exclude_ids=kept, newest_first=True
        )
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        cards = [
            {
                **views.restaurant_card(
                    idea,
                    place_store.get(conn, idea.place_id) if idea.place_id else None,
                    today,
                    now,
                    stale_days,
                ),
                "people": views.people_for(idea, slots),
            }
            for idea in found
        ]
        total = len([idea for idea in idea_store.list_all(conn) if idea.id not in kept])
    for card in cards:
        card["who"] = views.names_text(card["people"])
    return render_template("restaurants.html", cards=cards, total=total)


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
    app = _app()
    today = app.clock.today()
    with closing(app.connect()) as conn:
        seen = agenda.read(
            app,
            conn,
            today - timedelta(days=PLANS_BEHIND_DAYS),
            today + timedelta(days=PLANS_AHEAD_DAYS),
        )
        on = _no_gifts(seen.entries, presents.kept_ids(conn, auth.visitor().member))
        people = member_store.list_all(conn)
        rows = _plan_rows(conn, app, on, today, views.slot_map(people), None, past=True)
        asking = _who(conn)
    horizon = today.isoformat()
    upcoming = [row for row in rows if row["end"] >= horizon]
    recent = [row for row in rows if row["end"] < horizon][::-1]
    return render_template(
        "plans.html",
        months=_months(upcoming, today),
        upcoming=upcoming,
        recent=recent,
        ahead=PLANS_AHEAD_DAYS,
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
        today=today.isoformat(),
        can_schedule=True,
        on_google=calendar_available(app.settings),
        **asking,
    )


@bp.get("/plans/month")
def plans_month() -> str:
    """One month as a calendar, with what is coming in it and what is waiting to be rated."""
    app = _app()
    today = app.clock.today()
    first = _month(request.args.get("month"), today)
    weeks_first = first - timedelta(days=first.weekday())
    last_day = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    weeks_last = last_day + timedelta(days=6 - last_day.weekday())
    with closing(app.connect()) as conn:
        seen = agenda.read(app, conn, weeks_first, weeks_last)
        on = _no_gifts(seen.entries, presents.kept_ids(conn, auth.visitor().member))
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        rows = _plan_rows(conn, app, on, today, slots, None, past=True)
        rate = _unrated(conn, today, slots) if auth.visitor().may("change") else []
    previous = (first - timedelta(days=1)).replace(day=1)
    following = last_day + timedelta(days=1)
    weeks = views.month_calendar(rows, first, today, {row["plan_id"] for row in rate})
    start = max(today, first).isoformat()
    coming = [
        row
        for row in rows
        if row["end"] >= start
        and row["day"] <= last_day.isoformat()
        and row["end"] >= first.isoformat()
    ]
    return render_template(
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


def _no_gifts(entries: list[agenda.Entry], kept: set[int]) -> list[agenda.Entry]:
    """What is on, without plans made from a present that is hidden from the one looking."""
    return [entry for entry in entries if entry.idea_id not in kept]


def _own_only() -> int | None:
    """Whose tasks this visitor sees: their own, unless they may browse the household's."""
    visitor = auth.visitor()
    if visitor.may("browse") or visitor.member is None:
        return None
    return visitor.member.id


@bp.get("/tasks")
def tasks() -> str:
    app = _app()
    status = request.args.get("status", "open")
    if status not in {"open", "done", "cancelled", "all"}:
        abort(400)
    # A kid gets a plain checklist of her own open ones (docs/STYLE.md, "A kid's screen").
    simple = not auth.visitor().may("browse")
    if simple:
        status = "open"
    visitor = auth.visitor()
    with closing(app.connect()) as conn:
        rows = presents.visible_tasks(
            conn,
            task_store.list_all(
                conn,
                status=status,
                query="" if simple else request.args.get("q", ""),
                owner_id=_own_only(),
            ),
            visitor.member,
        )
        if status == "open":
            me = visitor.member.id if visitor.member else None
            rows = views.todo_order(rows, app.settings.tzinfo, app.clock.today(), me)
        open_count = (
            len(rows) if status == "open" and not request.args.get("q") else _open_count(conn)
        )
        people = member_store.list_all(conn)
        creators = task_store.creators(conn, [task.id for task in rows]) if simple else {}
        done_lately = (
            presents.visible_tasks(
                conn,
                task_store.list_all(conn, status="done", owner_id=_own_only()),
                visitor.member,
            )
            if simple
            else []
        )
    today = app.clock.today()
    tz = app.settings.tzinfo
    slots = views.slot_map(people)
    shown = [
        views.todo_page_row(
            task,
            tz,
            today,
            slots,
            kid=simple,
            nudging=app.settings.task_nudges,
            creator=creators.get(task.id),
            me=visitor.name,
        )
        for task in rows
    ]
    groups = _todo_groups(shown) if status == "open" and not simple else []
    since = utc_iso(app.clock.now() - timedelta(days=DONE_LATELY_DAYS))
    lately = [
        views.todo_page_row(task, tz, today, slots, kid=True, me=visitor.name)
        for task in done_lately
        if task.updated_at >= since
    ]
    return render_template(
        "tasks.html",
        simple=simple,
        rows=shown,
        lately=lately,
        groups=groups,
        open_count=open_count,
        late_count=sum(1 for row in shown if row["late"]) if status == "open" else None,
        repeat_options=views.REPEATS,
        people=[views.person_of(p.display_name, slots) for p in people],
        me=visitor.name,
        status=status,
        zone=app.settings.tz,
        query=request.args.get("q", ""),
    )


def _open_count(conn: Any) -> int:
    found = task_store.list_all(conn, status="open", owner_id=_own_only())
    return len(presents.visible_tasks(conn, found, auth.visitor().member))


def _todo_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Open to-dos in the order a person works through them: what is late, what has a day, what
    has none."""
    parts = (
        ("Overdue", "late", [row for row in rows if row["late"]]),
        ("Coming up", "", [row for row in rows if row["dated"] and not row["late"]]),
        ("No date", "", [row for row in rows if not row["dated"]]),
    )
    return [{"title": title, "tone": tone, "rows": found} for title, tone, found in parts if found]


@bp.get("/task/<int(max=9223372036854775807):task_id>/edit")
def edit_task(task_id: int) -> str:
    """A to-do's own page to change: all its boxes at once, with a way back to the list."""
    app = _app()
    with closing(app.connect()) as conn:
        task = task_store.get(conn, task_id)
        if task is None or not presents.visible_tasks(conn, [task], auth.visitor().member):
            abort(404)
        people = member_store.list_all(conn)
        made_by = task_store.creators(conn, [task.id]).get(task.id)
    tz = app.settings.tzinfo
    slots = views.slot_map(people)
    row = views.task_row(task, tz, nudging=app.settings.task_nudges)
    return render_template(
        "task_form.html",
        task=task,
        row=row,
        words=views.todo_row(task, tz, app.clock.today(), slots),
        added=views.day_short(date.fromisoformat(views.local_day(task.created_at, tz))),
        made_by=made_by,
        people=[views.person_of(p.display_name, slots) for p in people],
        owner=views.person_of(task.owner, slots) if task.owner else None,
        zone=app.settings.tz,
    )


# -- the kids' wish lists (docs/WISHES.md) --------------------------------------------------------

ANSWERED_DAYS = 30
TOP_WISHES = 3


def _is_kid(member: member_store.Member) -> bool:
    """A kid, by roles.py: keeps a wish list and decides on nobody's."""
    return roles.may(member.role, "wish") and not roles.may(member.role, "decide")


def _lists(conn: Any, kid: member_store.Member, today: date) -> dict[str, Any]:
    """A kid's three lists in her order, what was answered lately, and the countdowns."""
    christmas = date(today.year, 12, 25)
    if christmas < today:
        christmas = date(today.year + 1, 12, 25)
    birthday = next_birthday(kid.birth_date, today)
    days = {
        "christmas": (christmas - today).days,
        "birthday": (birthday - today).days if birthday else None,
    }
    lists = [
        {
            "occasion": occasion,
            "value": occasion or "everyday",
            "name": name,
            "lede": lede,
            "countdown": views.countdown(days.get(occasion)) if occasion else None,
            "rows": [
                views.wish_row(wish, today) for wish in wish_store.open_list(conn, kid.id, occasion)
            ],
        }
        for occasion, name, lede in views.WISH_LISTS
    ]
    since = (today - timedelta(days=ANSWERED_DAYS)).isoformat()
    everything = wish_store.for_member(conn, kid.id)
    answered = [
        views.wish_row(wish, today)
        for wish in everything
        if wish.status in ("granted", "declined") and (wish.answered_at or "") >= since
    ]
    turned = [
        views.wish_row(wish, today)
        for wish in everything
        if wish.status == "turned_away" and wish.created_at >= since
    ]
    return {
        "id": kid.id,
        "name": kid.display_name,
        "slot": kid.slot or 0,
        "initial": views.initial_for(
            kid.display_name, [m.display_name for m in member_store.list_all(conn)]
        ),
        "lists": lists,
        "answered": answered,
        "turned": turned,
        "open": sum(len(each["rows"]) for each in lists),
    }


def _kids(conn: Any) -> list[member_store.Member]:
    return [m for m in member_store.list_all(conn) if _is_kid(m)]


def wish_glance(conn: Any, today: date) -> dict[str, Any] | None:
    """For Home: a kid's own lists, or for a parent each kid's and what waits on them."""
    visitor = auth.visitor()
    if visitor.may("decide"):
        kids = [_lists(conn, kid, today) for kid in _kids(conn)]
        if not kids:
            return None
        waiting = [
            {**row, "kid": kid["name"], "kid_id": kid["id"]}
            for kid in kids
            for row in kid["turned"]
            if row["review"] == "asked" or row["concern"] == views.CONCERN_WORDS["inappropriate"]
        ]
        return {"parent": True, "kids": kids, "waiting": waiting, "top": TOP_WISHES}
    if visitor.member is not None and visitor.may("wish"):
        return {"parent": False, "mine": _lists(conn, visitor.member, today), "top": TOP_WISHES}
    return None


@bp.get("/wishes")
def wishes() -> str:
    """A kid's own wish lists; for a parent, every kid's, or one kid's with ?who=."""
    app = _app()
    today = app.clock.today()
    visitor = auth.visitor()
    wanted = request.args.get("who", "")
    with closing(app.connect()) as conn:
        if visitor.may("decide"):
            kids = _kids(conn)
            if wanted:
                chosen = next((k for k in kids if str(k.id) == wanted), None)
                if chosen is None:
                    abort(404)
                kids = [chosen]
            shown = [_lists(conn, kid, today) for kid in kids]
        elif visitor.member is not None:
            shown = [_lists(conn, visitor.member, today)]
        else:
            abort(404)
        people = member_store.list_all(conn)
        family = [member.display_name for member in people]
    names = {member.id: member.display_name for member in people}
    parents = [m.display_name for m in people if m.active and roles.may(m.role, "decide")]
    talk = (
        {}
        if visitor.may("decide") or not visitor.may("chat")
        else chat.box(family, prompt=chat.KID_LIST_PROMPT)
    )
    return render_template(
        "wishes.html",
        talk=bool(talk),
        ask_label=chat.KID_LIST_LABEL.format(name=personas.active(app.settings).name),
        **talk,
        kids=shown,
        names=names,
        parents_text=views.names_text([{"name": name} for name in parents]),
        parents_or=views.join_or(parents) or "a parent",
        parent=visitor.may("decide"),
        one=bool(wanted) or not visitor.may("decide"),
        choices=[(value or "everyday", name) for value, name, _ in views.WISH_LISTS],
    )
