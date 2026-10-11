"""The pages. Every view reads; nothing here writes to the database."""

from __future__ import annotations

import json
import logging
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    request,
    session,
    url_for,
)

from familydb import agenda, export, happening, health, personas, presents
from familydb.app import App
from familydb.availability import calendar_available, enrichment_available, happening_available
from familydb.base import roles
from familydb.base.dates import utc_iso, weekend_window
from familydb.store import calls
from familydb.store import finds as find_store
from familydb.store import ideas as idea_store
from familydb.store import lists as list_store
from familydb.store import members as member_store
from familydb.store import memories as memory_store
from familydb.store import messages as message_store
from familydb.store import outcomes as outcome_store
from familydb.store import picks as pick_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.store import tasks as task_store
from familydb.store.ideas import KIND_SUGGESTIONS
from familydb.suggest import people as who_for
from familydb.web import (
    auth,
    calendar_view,
    chat,
    map_view,
    now,
    page_rows,
    views,
    wishes_view,
)
from familydb.web import status as status_page
from familydb.web.answers import answer
from familydb.web.chat import WHO_KEY

log = logging.getLogger(__name__)
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
FILTERS = views.IDEA_FILTERS
HOME_AHEAD_DAYS = 60
# A kid's To do page keeps what she ticked off this long, with a way to undo it.
DONE_LATELY_DAYS = 7
HOME_PLANS = 4
HOME_IDEAS = 4
HOME_TASKS = 4
PLANS_AHEAD_DAYS = 90
# The most things near home one page lists: four weeks of a busy city's calendars.
HAPPENING_MOST = 300
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
    """For a monitor or proxy, open before sign-in: "ok", or 503 and what is wrong (the database
    does not answer, or the scheduled jobs went quiet; familydb/health.py)."""
    ok, words = health.check(_app())
    return Response(f"{words}\n", status=200 if ok else 503, mimetype="text/plain")


@bp.get("/sw.js")
def service_worker() -> Response:
    """The service worker that shows "she has a message" (push.py), served from the top so it
    may show for every page. Open before sign-in, like the manifest: it holds nothing but code."""
    folder = Path(current_app.static_folder or "")
    response = Response((folder / "sw.js").read_text("utf-8"), mimetype="text/javascript")
    response.headers["Cache-Control"] = "no-cache"
    return response


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
        # Share a link or some words to it from another app (Android): they wait in the chat's
        # box until Send, so nothing is sent by sharing.
        "share_target": {
            "action": "/chat",
            "method": "GET",
            "params": {"title": "title", "text": "text", "url": "url"},
        },
    }
    return Response(json.dumps(body, sort_keys=True), mimetype="application/manifest+json")


@bp.get("/more")
def more() -> str:
    """The phone's menu: what is not in the tab bar, and signing out. It opens from the picture at
    the top of every page and is not a page on a wide screen, where the sidebar holds all of it."""
    return answer("more.html")


@bp.get("/status")
def status() -> str:
    app = _app()
    with closing(app.connect()) as conn:
        return answer("status.html", **status_page.status(app, conn))


@bp.get("/")
def home() -> Response | str:
    """Now, the first screen (web/now.py): the box, her questions, her picks, today's line."""
    return now.show()


@bp.post("/later")
def later() -> Response:
    """Later on a kid's pitch on Now: off this device for a week (web/now.py)."""
    return now.later()


def _others(coming: list[dict[str, Any]], me: member_store.Member | None) -> str:
    """For a kid's sentence: who else is on her next plan ("with Theo")."""
    if not coming or me is None:
        return ""
    named = [p for p in coming[0]["people"] if p["name"].casefold() != me.display_name.casefold()]
    return views.names_text([p for p in named if p["initial"]])


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
@bp.get("/do")
def ideas() -> str:
    """What could we do? (docs/INTERFACE.md section 4): the saved pile, what fits the next free
    stretch on top, then everything newest first. Restaurants have their own door (Eat)."""
    app = _app()
    settings = app.settings
    today = app.clock.today()
    visitor = auth.visitor()
    grown_up = visitor.may("browse")
    query = request.args.get("q", "").strip()
    kind = request.args.get("kind", "").strip()
    status = request.args.get("status", "").strip()
    who = request.args.get("who", "").strip()
    narrow = {key: request.args.get(key, "") == "1" for key in ("free", "close", "kids", "us")}
    with closing(app.connect()) as conn:
        kept = presents.kept_ids(conn, visitor.member)
        found = idea_store.search(
            conn,
            text=query or None,
            kind=kind or None,
            status=status if status in STATUSES else None,
            participant=who if who and who not in ("kids", "us") else None,
            limit=LIST_LIMIT,
            exclude_ids=kept,
            newest_first=not query,
        )
        listed = [
            idea for idea in idea_store.list_all(conn, include_dropped=True) if idea.id not in kept
        ]
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        hidden = presents.of_presents(conn, found, people)
        away = {
            idea.id: map_view.away_from_home(place_store.get(conn, idea.place_id), settings)
            for idea in found
            if idea.place_id
        }
        picked = _weekend_picks(conn, today) if grown_up else None
        chat.page_box(
            app, conn, people, scope={"label": "Things to do", "text": "About things to do:"}
        )
    if kind != RESTAURANT_KIND:
        found = [idea for idea in found if idea.kind != RESTAURANT_KIND]
    found = _narrowed(found, people, away, narrow)
    names = {m.id: m.display_name for m in people}
    stale = utc_iso(app.clock.now() - timedelta(days=FADE_DAYS))
    resting = utc_iso(app.clock.now() - timedelta(days=STILL_WANT_DAYS))
    asking = grown_up and visitor.may("change")
    rows = []
    for idea in found:
        card = _idea_card(idea, settings, away.get(idea.id), slots, hidden.get(idea.id))
        card["line"] = views.do_line(
            card,
            by=names.get(idea.suggested_by or -1),
            closing=views.closing_words(idea, today),
        )
        card["faded"] = idea.status == "idea" and idea.updated_at < stale
        card["still_want"] = asking and idea.status == "idea" and idea.updated_at < resting
        rows.append(card)
    top = None
    if picked and not (query or kind or status or who or any(narrow.values())):
        rows, top = _lead_with_pick(rows, picked)
    live = [idea for idea in listed if idea.status != "dropped" and idea.kind != RESTAURANT_KIND]
    placed = [(idea, away[idea.id]) for idea in found if away.get(idea.id)]
    filtered = bool(query or kind or status or who or any(narrow.values()))
    return answer(
        "do.html",
        rows=rows,
        top=top,
        summary=views.do_summary(len(live), top, rows[0] if top else None),
        chips=_do_chips(listed, people, kind, who, status, narrow, grown_up),
        on_map=map_view.places_map(placed),
        off_map=len(found) - len(placed),
        looking_up=enrichment_available(settings),
        selected={"q": query, "kind": kind, "status": status, "who": who},
        filtered=filtered,
        limit=LIST_LIMIT,
    )


# An untouched idea goes paler after this long, and after the second asks whether it is still
# wanted, with Keep and Let go (docs/INTERFACE.md section 4).
FADE_DAYS = 42
STILL_WANT_DAYS = 90
# How near "Close" is, in minutes of driving.
CLOSE_MINUTES = 20
KIND_CHIPS = (
    ("outing", "Outing"),
    ("activity", "Activity"),
    ("day_trip", "Day trip"),
    ("trip", "Trip"),
    ("show", "Show"),
    ("event", "Event"),
    ("seasonal", "Seasonal"),
    ("home", "Stay in"),
)


def _weekend_picks(conn: Any, today: date) -> Any:
    """Her weekend set while its days are not over, else whatever set is current."""
    weekend = pick_store.latest(conn, window="weekend")
    if weekend is not None and weekend.window_end >= today.isoformat():
        return weekend
    return pick_store.current(conn, today=today.isoformat())


def _narrowed(
    found: list[Any],
    people: list[member_store.Member],
    away: dict[int, Any],
    narrow: dict[str, bool],
) -> list[Any]:
    """The chips that no search column answers: free, close, with the kids, just us."""
    kept = found
    if narrow["free"]:
        kept = [idea for idea in kept if idea.cost_level == 0]
    if narrow["close"]:
        kept = [
            idea
            for idea in kept
            if away.get(idea.id) is not None and away[idea.id].minutes <= CLOSE_MINUTES
        ]
    if narrow["kids"]:
        kept = [idea for idea in kept if who_for.with_the_kids(idea, people)]
    if narrow["us"]:
        kept = [idea for idea in kept if who_for.just_us(idea, people)]
    return kept


def _do_chips(
    listed: list[Any],
    people: list[member_store.Member],
    kind: str,
    who: str,
    status: str,
    narrow: dict[str, bool],
    grown_up: bool,
) -> list[dict[str, Any]]:
    """Kinds that exist in the pile, who it is for, free, close, each person, and Dropped."""
    kinds = {idea.kind for idea in listed if idea.status != "dropped"}
    chips = [
        {"label": label, "href": url_for("web.ideas", kind=value), "on": kind == value}
        for value, label in KIND_CHIPS
        if value in kinds
    ]
    if grown_up:
        chips.append(
            {"label": "With the kids", "href": url_for("web.ideas", kids="1"), "on": narrow["kids"]}
        )
        chips.append({"label": "Just us", "href": url_for("web.ideas", us="1"), "on": narrow["us"]})
    chips.append({"label": "Free", "href": url_for("web.ideas", free="1"), "on": narrow["free"]})
    chips.append({"label": "Close", "href": url_for("web.ideas", close="1"), "on": narrow["close"]})
    if grown_up:
        chips += [
            {
                "label": person.display_name,
                "href": url_for("web.ideas", who=person.display_name),
                "on": who.casefold() == person.display_name.casefold(),
            }
            for person in people
        ]
        chips.append(
            {
                "label": "Dropped",
                "href": url_for("web.ideas", status="dropped"),
                "on": status == "dropped",
            }
        )
    if any(chip["on"] for chip in chips):
        chips.insert(0, {"label": "Everything", "href": url_for("web.ideas"), "on": False})
    return chips


def _lead_with_pick(
    rows: list[dict[str, Any]], picked: Any
) -> tuple[list[dict[str, Any]], str | None]:
    """Her weekend pick that is in the pile leads it, with when it fits over it."""
    for tile in picked.picks:
        for row in rows:
            if tile.get("idea_id") == row["id"] and row["kind_name"] != "Restaurant":
                rest = [other for other in rows if other is not row]
                when = tile.get("when") or "the weekend"
                return [row, *rest], f"Fits {when}"
    return rows, None


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


@bp.get(f"/place/<int(max={MAX_ID}):idea_id>")
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
        changed = calls.last_change(conn, idea_id=idea_id) if visitor.may("browse") else None
        family = member_store.list_all(conn)
        slots = views.slot_map(family)
        kept = presents.of_presents(conn, [record], family).get(idea_id)
        box = chat.page_box(
            app,
            conn,
            family,
            prompt=chat.ITEM_PROMPT,
            scope={"label": record.title, "text": f"About #{record.id} {record.title}:"},
        )
        box["starters"] = views.idea_starters(record, today)
    away = map_view.away_from_home(place, settings)
    card = _idea_card(record, settings, away, slots, kept)
    by = next((m.display_name for m in family if m.id == record.suggested_by), None)
    return answer(
        "idea.html",
        state=views.idea_state(record, plans, today),
        by=by,
        said_on=views.local_moment(original.received_at, settings.tzinfo) if original else None,
        idea=record,
        original_message=message_store.as_said(original.text) if original else None,
        original_by=views.original_by(original, family, settings.tzinfo) if original else None,
        today=today.isoformat(),
        ratings=RATINGS,
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
        changed=views.changed_line(
            changed, settings.tzinfo, assistant=personas.active(settings).name
        ),
    )


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
    return answer(
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


@bp.get("/lists/<name>")
@bp.get("/lists")
def lists_page(name: str | None = None) -> str:
    """Lists (docs/INTERFACE.md section 4): the list in use, big ticks that need no conversation;
    the other lists are chips, each at its own address (`/lists/costco`). Every tick and add is
    the shopping_list tool (edits.change_list). The shopping list is always there."""
    app = _app()
    wanted = list_store.name_of(name or request.args.get("list", "")) or "shopping"
    with closing(app.connect()) as conn:
        names = list_store.names(conn)
        order = ["shopping", *(other for other in names if other != "shopping")]
        if wanted not in order:
            abort(404)
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        named = {person.id: person.display_name for person in people}
        shown = []
        for name in order:
            ref = list_store.find(conn, name)
            held = list_store.items(conn, ref) if ref is not None else []
            shown.append(
                {
                    "name": name,
                    "title": views.list_title(name),
                    # Each with who put it there, as section 4 has it: "who asked".
                    "to_get": [
                        {
                            "text": item.text,
                            "by": views.person_of(named[item.added_by], slots)
                            if item.added_by in named
                            else None,
                        }
                        for item in held
                        if item.ticked_at is None
                    ],
                    "ticked": [item.text for item in held if item.ticked_at is not None],
                }
            )
        current = next(one for one in shown if one["name"] == wanted)
        chat.page_box(
            app,
            conn,
            people,
            scope={"label": current["title"], "text": f"About the {current['title'].lower()}:"},
        )
    chips = [
        {
            "label": one["title"].removesuffix(" list").capitalize(),
            "href": url_for("web.lists_page", name=one["name"]),
            "on": one["name"] == wanted,
            "n": len(one["to_get"]),
        }
        for one in shown
    ]
    return answer(
        "lists.html",
        shown=current,
        lists=shown,
        chips=chips if len(shown) > 1 else [],
        summary=views.lists_summary(shown),
    )


def _download(text: str, name: str, mimetype: str) -> Response:
    log.info("%s was downloaded by %s", name, auth.client_address())
    response = Response(text, mimetype=mimetype)
    response.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/export/plans.ics")
def export_plans() -> Response:
    """The plans as a calendar file any calendar can open (export.py), for a grown-up."""
    app = _app()
    with closing(app.connect()) as conn:
        text = export.plans_ics(conn, app.settings, app.clock.now())
    return _download(text, "familydb-plans.ics", "text/calendar")


@bp.get("/export/ideas.csv")
def export_ideas() -> Response:
    """The ideas as a spreadsheet, without a present kept from whoever asks (presents.py)."""
    with closing(_app().connect()) as conn:
        text = export.ideas_csv(conn, presents.kept_ids(conn, auth.visitor().member))
    return _download(text, "familydb-ideas.csv", "text/csv")


@bp.get("/export/tasks.csv")
def export_tasks() -> Response:
    """The things to do as a spreadsheet, for a grown-up, who sees everybody's."""
    with closing(_app().connect()) as conn:
        text = export.tasks_csv(conn)
    return _download(text, "familydb-to-dos.csv", "text/csv")


@bp.get("/memory")
def memory() -> str:
    app = _app()
    with closing(app.connect()) as conn:
        everything = memory_store.list_all(conn)
        people = member_store.list_all(conn)
    return answer(
        "memory.html",
        **views.memory_page(everything, people, app.clock.today(), app.settings.tzinfo),
        people=people,
        slots=views.slot_map(people),
        kinds=views.MEMORY_KINDS,
    )


@bp.get("/restaurants")
@bp.get("/eat")
def restaurants() -> str:
    """Where should we eat? (docs/INTERFACE.md section 4): a top pick for the next meal, chosen
    by code, then every saved restaurant with the one fact that decides."""
    app = _app()
    now = app.clock.now()
    today = app.clock.today()
    stale_days = app.settings.place_stale_days
    visitor = auth.visitor()
    kid = not visitor.may("browse")
    who = request.args.get("who", "").strip()
    narrow = {key: request.args.get(key, "") == "1" for key in ("open", "close", "new")}
    tag = request.args.get("tag", "").strip().casefold()
    with closing(app.connect()) as conn:
        kept = presents.kept_ids(conn, visitor.member)
        found = idea_store.search(
            conn,
            kind=RESTAURANT_KIND,
            participant=who if who and who not in ("kids", "us") else None,
            limit=LIST_LIMIT,
            exclude_ids=kept,
            newest_first=True,
        )
        people = member_store.list_all(conn)
        slots = views.slot_map(people)
        cards = []
        for idea in found:
            card = views.restaurant_card(
                idea,
                place_store.get(conn, idea.place_id) if idea.place_id else None,
                today,
                now,
                stale_days,
            )
            card["people"] = views.people_for(idea, slots)
            card["who"] = views.names_text(card["people"])
            card["line"] = views.eat_line(card, idea, kid=kid)
            card["score"] = views.eat_score(card, idea)
            card["idea"] = idea
            cards.append(card)
        tags = sorted({one.casefold() for idea in found for one in idea.tags})
        chat.page_box(app, conn, people, scope={"label": "Eat out", "text": "About eating out:"})
    cards = _eat_narrowed(cards, people, narrow, who, tag)
    cards.sort(key=lambda card: card["score"])
    for card in cards:
        card.pop("idea")
    plain = not any(narrow.values()) and not who and not tag
    top = views.meal_words(now.astimezone(app.settings.tzinfo)) if cards and plain else None
    return answer(
        "eat.html",
        cards=cards,
        top=top,
        summary=views.eat_summary(cards[0] if cards else None, top),
        chips=_eat_chips(people, narrow, who, tags, tag, kid),
    )


def _eat_narrowed(
    cards: list[dict[str, Any]],
    people: list[member_store.Member],
    narrow: dict[str, bool],
    who: str,
    tag: str,
) -> list[dict[str, Any]]:
    kept = cards
    if narrow["open"]:
        kept = [card for card in kept if card["today"] and card["today"].startswith("open")]
    if narrow["close"]:
        kept = [card for card in kept if views.travel_minutes(card["travel"]) <= CLOSE_MINUTES]
    if narrow["new"]:
        kept = [card for card in kept if not card["idea"].times_done]
    if who == "kids":
        kept = [card for card in kept if who_for.with_the_kids(card["idea"], people)]
    elif who == "us":
        kept = [card for card in kept if who_for.just_us(card["idea"], people)]
    if tag:
        kept = [card for card in kept if tag in {one.casefold() for one in card["tags"]}]
    return kept


def _eat_chips(
    people: list[member_store.Member],
    narrow: dict[str, bool],
    who: str,
    tags: list[str],
    tag: str,
    kid: bool,
) -> list[dict[str, Any]]:
    chips = [
        {"label": "Open today", "href": url_for("web.restaurants", open="1"), "on": narrow["open"]},
        {"label": "Close", "href": url_for("web.restaurants", close="1"), "on": narrow["close"]},
        {"label": "New to us", "href": url_for("web.restaurants", new="1"), "on": narrow["new"]},
    ]
    if not kid:
        chips.append(
            {"label": "Just us", "href": url_for("web.restaurants", who="us"), "on": who == "us"}
        )
        chips.append(
            {
                "label": "With the kids",
                "href": url_for("web.restaurants", who="kids"),
                "on": who == "kids",
            }
        )
    chips += [
        {"label": one.capitalize(), "href": url_for("web.restaurants", tag=one), "on": tag == one}
        for one in tags[:8]
    ]
    if not kid:
        chips += [
            {
                "label": person.display_name,
                "href": url_for("web.restaurants", who=person.display_name),
                "on": who.casefold() == person.display_name.casefold(),
            }
            for person in people
        ]
    if any(chip["on"] for chip in chips):
        chips.insert(0, {"label": "Everything", "href": url_for("web.restaurants"), "on": False})
    return chips


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
        on = presents.without(seen.entries, presents.kept_ids(conn, auth.visitor().member))
        people = member_store.list_all(conn)
        rows = page_rows.plan_rows(conn, app, on, today, views.slot_map(people), None, past=True)
        asking = _who(conn)
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
    app = _app()
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
    app = _app()
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
    app = _app()
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
    return answer(
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
@bp.get("/reminder/<int(max=9223372036854775807):task_id>")
def edit_task(task_id: int) -> str:
    """A reminder's own page (docs/INTERFACE.md section 5): when or on what condition, whose,
    how it repeats, where it is sent, in words; and the form to change all of it by hand."""
    app = _app()
    with closing(app.connect()) as conn:
        task = task_store.get(conn, task_id)
        if task is None or not presents.visible_tasks(conn, [task], auth.visitor().member):
            abort(404)
        people = member_store.list_all(conn)
        made_by = task_store.creators(conn, [task.id]).get(task.id)
        changed = calls.last_change(conn, task_id=task.id)
        box = chat.page_box(
            app,
            conn,
            people,
            prompt=chat.ITEM_PROMPT,
            scope={"label": task.title, "text": f"About the reminder {task.title}:"},
        )
    box["starters"] = views.task_starters(task, app.clock.today())
    tz = app.settings.tzinfo
    slots = views.slot_map(people)
    row = views.task_row(task, tz, app.clock.today(), nudging=app.settings.task_nudges)
    row["changed"] = views.changed_line(changed, tz, assistant=personas.active(app.settings).name)
    return answer(
        "task_form.html",
        task=task,
        row=row,
        words=views.todo_row(task, tz, app.clock.today(), slots),
        added=views.day_short(date.fromisoformat(views.local_day(task.created_at, tz))),
        made_by=made_by,
        people=[views.person_of(p.display_name, slots) for p in people],
        owner=views.person_of(task.owner, slots) if task.owner else None,
        zone=app.settings.tz,
        presses=chat.PAGE_BUTTONS,
    )


# -- the kids' wish lists (docs/WISHES.md) --------------------------------------------------------


@bp.get("/kids/<name>")
@bp.get("/wishes")
@bp.get("/kids")
def wishes(name: str | None = None) -> str:
    """The kids (docs/INTERFACE.md section 4): for a parent each kid as a section, what waits
    first; one kid at her own address (`/kids/maya`), with her pitches and her thread to read
    along; a kid's own wish lists, in her order."""
    app = _app()
    today = app.clock.today()
    visitor = auth.visitor()
    wanted = request.args.get("who", "")
    waiting_only = request.args.get("waiting") == "1"
    with closing(app.connect()) as conn:
        if name is not None:
            named = next(
                (
                    kid
                    for kid in wishes_view.kids(conn)
                    if views.slug(kid.display_name) == name.casefold()
                ),
                None,
            )
            me = visitor.member
            mine = me is not None and named is not None and named.id == me.id
            if named is None or not (visitor.may("decide") or mine):
                abort(404)
            wanted = str(named.id) if visitor.may("decide") else ""
        if visitor.may("decide"):
            kids = wishes_view.kids(conn)
            if wanted:
                chosen = next((k for k in kids if str(k.id) == wanted), None)
                if chosen is None:
                    abort(404)
                kids = [chosen]
            shown = [wishes_view.lists(conn, kid, today) for kid in kids]
        elif visitor.member is not None:
            shown = [wishes_view.lists(conn, visitor.member, today)]
        else:
            abort(404)
        people = member_store.list_all(conn)
        everyone = wishes_view.kids(conn) if visitor.may("decide") else []
        pronouns = {
            person.id: {"female": "her", "male": "his"}.get(person.gender or "", "their")
            for person in people
        }
        talk = chat.page_box(  # kept for `talk`: a kid's add form shows only without the box
            app,
            conn,
            people,
            prompt=chat.KID_LIST_PROMPT if not visitor.may("decide") else chat.DEST_PROMPT,
            scope=(
                {"label": "The kids", "text": "About the kids:"}
                if visitor.may("decide")
                else {"label": "My list", "text": "About my list:"}
            ),
        )
    names = {member.id: member.display_name for member in people}
    parents = [m.display_name for m in people if m.active and roles.may(m.role, "decide")]
    if wanted and visitor.may("decide"):
        with closing(app.connect()) as conn:
            pitched = [
                idea
                for idea in idea_store.list_all(conn)
                if idea.suggested_by == shown[0]["id"] and not idea_store.is_gift(idea)
            ]
        shown[0]["pitches"] = [
            {
                "id": idea.id,
                "title": idea.title,
                "state": views.idea_state(idea, [], today),
                "when": views.day_short(
                    date.fromisoformat(views.local_day(idea.created_at, app.settings.tzinfo))
                ),
            }
            for idea in sorted(pitched, key=lambda idea: idea.created_at, reverse=True)[:8]
        ]
        shown[0]["thread"] = url_for("chat.show", **{"with": shown[0]["id"]}, _anchor="latest")
    for kid in shown:
        kid["pronoun"] = pronouns.get(kid["id"], "their")
        kid["turned"] = (
            [row for row in kid["turned"] if row["to_decide"]]
            if visitor.may("decide")
            else kid["turned"]
        )
    waiting = sum(len(kid["turned"]) for kid in shown) if visitor.may("decide") else 0
    if waiting_only:
        shown = [kid for kid in shown if kid["turned"]]
    chips = []
    if visitor.may("decide") and len(everyone) > 1:
        chips = [
            {
                "label": kid.display_name,
                "href": url_for("web.wishes", name=views.slug(kid.display_name)),
                "on": str(kid.id) == wanted,
            }
            for kid in everyone
        ]
        chips.append(
            {
                "label": "Waiting on you",
                "href": url_for("web.wishes", waiting="1"),
                "on": waiting_only,
            }
        )
        if wanted or waiting_only:
            chips.insert(0, {"label": "Everyone", "href": url_for("web.wishes"), "on": False})
    return answer(
        "kids.html",
        talk=not talk.get("no_box"),
        kids=shown,
        names=names,
        parents_text=views.names_text([{"name": name} for name in parents]),
        parent=visitor.may("decide"),
        one=bool(wanted) or not visitor.may("decide"),
        choices=[(value or "everyday", name) for value, name, _ in views.WISH_LISTS],
        chips=chips,
        summary=views.kids_summary(shown, waiting)
        if visitor.may("decide")
        else views.my_list_summary(shown[0]),
    )
