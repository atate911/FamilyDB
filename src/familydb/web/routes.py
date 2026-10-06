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

from familydb import agenda, personas, roles
from familydb.app import App
from familydb.availability import calendar_available, enrichment_available
from familydb.dates import next_birthday
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
MAX_ID = 2**63 - 1  # beyond this SQLite raises rather than simply finding nothing
STATUSES = ("idea", "planned", "done", "dropped")
SETTINGS = ("either", "indoor", "outdoor")
WEATHERS = ("any", "dry", "warm", "snow")
SEASONS = ("spring", "summer", "autumn", "winter")
COSTS = ((0, "free"), (1, "cheap"), (2, "moderate"), (3, "pricey"), (4, "expensive"))
RATINGS = tuple(range(10, 0, -1))
RESTAURANT_KIND = "restaurant"
FILTERS = ("q", "kind", "status", "who")
HOME_AHEAD_DAYS = 60
HOME_PLANS = 4
HOME_IDEAS = 4
HOME_TASKS = 4
PLANS_AHEAD_DAYS = 90
PLANS_BEHIND_DAYS = 30
# The page's charcoal: `--bg` in style.css and the theme colour in base.html.
CHARCOAL = "#0b0e0d"


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
    small, large = (
        url_for("static", filename="icon-192.png"),
        url_for("static", filename="icon-512.png"),
    )
    icons = [
        {"src": small, "sizes": "192x192"},
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
        "background_color": CHARCOAL,
        "theme_color": CHARCOAL,
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
        return render_template("status.html", **status_page.status(app, conn))


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
        on = _no_gifts(conn, seen.entries)
        everything = idea_store.list_all(conn)
        if _gifts_hidden():
            everything = [idea for idea in everything if not idea_store.is_gift(idea)]
        unfinished = status_page.setup_steps(app, conn) if manages else []
        people = member_store.list_all(conn)
        todo = task_store.list_all(conn, status="open", owner_id=_own_only())
        talk = chat.glance(app, conn) if talks else None
        wished = wish_glance(conn, today)
        slots = views.slot_map(people)
        coming = _plan_rows(conn, app, on, today, slots, visitor.member if not browsing else None)
        rating = _to_rate(conn, today) if visitor.may("change") else None
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
        plans_href=url_for("web.plans"),
        todo_href=url_for("web.tasks"),
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
) -> list[dict[str, Any]]:
    """What is coming, with whom it is for and how far it is. A kid's are the ones that name her,
    or nobody (so everybody)."""
    rows = []
    for entry in entries:
        if entry.days()[-1] < today:
            continue
        idea = idea_store.get(conn, entry.idea_id) if entry.idea_id else None
        people = views.people_for(idea, slots)
        if only_for is not None and not views.names_in(people, only_for):
            continue
        place = place_store.get(conn, idea.place_id) if idea and idea.place_id else None
        away = views.away_from_home(place, app.settings)
        rows.append(views.entry_row(entry, today, people=people, away=away))
    return rows


def _others(coming: list[dict[str, Any]], me: member_store.Member | None) -> str:
    """For a kid's sentence: who else is on her next plan ("with Theo")."""
    if not coming or me is None:
        return ""
    named = [p for p in coming[0]["people"] if p["name"].casefold() != me.display_name.casefold()]
    return views.names_text([p for p in named if p["initial"]])


def _to_rate(conn: Any, today: date) -> dict[str, Any] | None:
    """The oldest plan nobody has said how it went, for Home's three faces, and how many more."""
    waiting = plan_store.unrated(
        conn,
        today=today.isoformat(),
        since=(today - timedelta(days=shell.RATE_DAYS)).isoformat(),
    )
    if not waiting:
        return None
    plan = waiting[0]
    return {
        "plan_id": plan.id,
        "idea_id": plan.idea_id,
        "title": plan.title,
        "day": plan.start[:10],
        "when": views.day_short(date.fromisoformat(plan.start[:10])),
        "more": len(waiting) - 1,
    }


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
        waiting = sum(1 for row in wished["waiting"] if row["id"] == kid["id"])
        pronoun = {"female": "her", "male": "his"}.get(person.gender or "", "their")
        cards.append(
            {
                **kid,
                "slot": person.slot or 0 if person else 0,
                "initial": kid["name"][:1].upper(),
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
            without_gifts=_gifts_hidden(),
        )
        listed = idea_store.list_all(conn, include_dropped=True)
        if _gifts_hidden():
            listed = [idea for idea in listed if not idea_store.is_gift(idea)]
        kinds, people = _choices(listed)
        capture_people = member_store.list_all(conn)
        away = {
            idea.id: views.away_from_home(place_store.get(conn, idea.place_id), settings)
            for idea in found
            if idea.place_id
        }
    filtered = bool(query or kind or status or who)
    rows = []
    for idea in found:
        spot = away.get(idea.id)
        rows.append({**views.idea_row(idea, settings.tzinfo), "away": spot.text if spot else None})
    return render_template(
        "ideas.html",
        capture_people=capture_people,
        rows=rows,
        on_radar=views.places_radar([(i, away[i.id]) for i in found if away.get(i.id)]),
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
        if record is None or (_gifts_hidden() and idea_store.is_gift(record)):
            abort(404)
        original = (
            message_store.get(conn, record.source_message_id) if record.source_message_id else None
        )
        place = place_store.get(conn, record.place_id) if record.place_id else None
        outcomes = outcome_store.list_for_idea(conn, idea_id)
        plans = plan_store.for_idea(conn, idea_id)
        asking = _who(conn)
        looked_up = calls.last_lookup_turn(conn, idea_id) if auth.visitor().may("manage") else None
    return render_template(
        "idea.html",
        idea=record,
        original_message=message_store.as_said(original.text) if original else None,
        today=today.isoformat(),
        ratings=RATINGS,
        can_schedule=calendar_available(settings),
        can_look_up=enrichment_available(settings) and record.status != "dropped",
        looked_up=looked_up,
        lookups=views.lookups_when(settings),
        **asking,
        row=views.idea_row(record, settings.tzinfo),
        setting=views.SETTINGS.get(record.setting, record.setting),
        weather=views.WEATHER.get(record.weather),
        place=views.place_panel(place, now, settings.place_stale_days),
        outcomes=[views.outcome_row(o) for o in reversed(outcomes)],
        plans=[views.plan_row(p, today) for p in reversed(plans)],
    )


def _idea_form(record: Any = None) -> str:
    app = _app()
    with closing(app.connect()) as conn:
        kinds = sorted({row.kind for row in idea_store.list_all(conn, include_dropped=True)})
        family = [member.display_name for member in member_store.list_all(conn)]
    return render_template(
        "idea_form.html",
        idea=record,
        revision=idea_store.revision(record) if record else None,
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
        kinds=views.MEMORY_KINDS,
    )


@bp.get("/restaurants")
def restaurants() -> str:
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


@bp.get("/plans")
def plans() -> str:
    app = _app()
    today = app.clock.today()
    with closing(app.connect()) as conn:
        seen = agenda.read(
            app,
            conn,
            today - timedelta(days=PLANS_BEHIND_DAYS),
            today + timedelta(days=PLANS_AHEAD_DAYS),
        )
        on = _no_gifts(conn, seen.entries)
        titles = {row.id: row.title for row in idea_store.list_all(conn, include_dropped=True)}
        asking = _who(conn)
    upcoming = [entry for entry in on if entry.days()[-1] >= today]
    recent = [entry for entry in on if entry.days()[-1] < today]
    return render_template(
        "plans.html",
        upcoming=[views.entry_row(entry, today) for entry in upcoming],
        recent=[views.entry_row(entry, today) for entry in reversed(recent)],
        titles=titles,
        ahead=PLANS_AHEAD_DAYS,
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
        today=today.isoformat(),
        can_schedule=calendar_available(app.settings),
        **asking,
    )


@bp.get("/plans/month")
def plans_month() -> str:
    """One month as a calendar, or a list of busy days on a narrow screen."""
    app = _app()
    today = app.clock.today()
    first = _month(request.args.get("month"), today)
    weeks_first = first - timedelta(days=first.weekday())
    last_day = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    weeks_last = last_day + timedelta(days=6 - last_day.weekday())
    with closing(app.connect()) as conn:
        seen = agenda.read(app, conn, weeks_first, weeks_last)
        on = _no_gifts(conn, seen.entries)
    previous = (first - timedelta(days=1)).replace(day=1)
    following = last_day + timedelta(days=1)
    weeks = views.month_weeks(on, first, today)
    return render_template(
        "plans_month.html",
        month=f"{first:%B %Y}",
        weeks=weeks,
        busy_days=[day for week in weeks for day in week if day["current"] and day["entries"]],
        previous=f"{previous:%Y-%m}",
        following=f"{following:%Y-%m}",
        this_month=first == today.replace(day=1),
        source=seen.source,
        source_note=views.AGENDA_NOTES[seen.source],
    )


def _gifts_hidden() -> bool:
    """Presents are kept from anybody who may not decide what the kids get (docs/WISHES.md)."""
    return not auth.visitor().may("decide")


def _no_gifts(conn: Any, entries: list[agenda.Entry]) -> list[agenda.Entry]:
    """What is on, without plans made from a present, where presents are kept."""
    if not _gifts_hidden():
        return entries
    gifts = {i.id for i in idea_store.list_all(conn, include_dropped=True) if idea_store.is_gift(i)}
    return [entry for entry in entries if entry.idea_id not in gifts]


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
    with closing(app.connect()) as conn:
        rows = task_store.list_all(
            conn,
            status=status,
            query="" if simple else request.args.get("q", ""),
            owner_id=_own_only(),
        )
        people = member_store.list_all(conn)
    today = app.clock.today()
    return render_template(
        "tasks.html",
        simple=simple,
        briefs=[views.task_brief(task, app.settings.tzinfo, today) for task in rows]
        if simple
        else [],
        rows=[
            views.task_row(task, app.settings.tzinfo, nudging=app.settings.task_nudges)
            for task in rows
        ],
        repeat_options=views.REPEATS,
        people=people,
        status=status,
        zone=app.settings.tz,
        query=request.args.get("q", ""),
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
            {"kid": kid["name"], "id": kid["id"], **row}
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
        family = [member.display_name for member in member_store.list_all(conn)]
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
        parent=visitor.may("decide"),
        one=bool(wanted) or not visitor.may("decide"),
        choices=[(value or "everyday", name) for value, name, _ in views.WISH_LISTS],
    )
