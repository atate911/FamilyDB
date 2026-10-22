"""The ideas pages: What could we do (and its chips), one idea in full, the forms for a new
idea and a change, and Where could we eat."""

from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta
from typing import Any

from flask import (
    abort,
    request,
    session,
    url_for,
)

from familydb import agenda, meals, personas, presents
from familydb.availability import calendar_available, enrichment_available
from familydb.base import roles
from familydb.base.dates import utc_iso
from familydb.store import calls
from familydb.store import finds as find_store
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import messages as message_store
from familydb.store import outcomes as outcome_store
from familydb.store import picks as pick_store
from familydb.store import places as place_store
from familydb.store import plans as plan_store
from familydb.store import recipes as recipe_store
from familydb.store.ideas import KIND_SUGGESTIONS, RECIPE
from familydb.suggest import people as who_for
from familydb.web import (
    auth,
    chat,
    map_view,
    page_rows,
    shell,
    views,
)
from familydb.web.answers import answer
from familydb.web.chat import WHO_KEY
from familydb.web.pages import MAX_ID, bp, familydb_app, who_asks

LIST_LIMIT = 200


STATUSES = ("idea", "planned", "done", "dropped")


SETTINGS = ("either", "indoor", "outdoor")


WEATHERS = ("any", "dry", "warm", "snow")


SEASONS = ("spring", "summer", "autumn", "winter")


COSTS = ((0, "free"), (1, "cheap"), (2, "moderate"), (3, "pricey"), (4, "expensive"))


RATINGS = tuple(range(10, 0, -1))


RESTAURANT_KIND = "restaurant"
# Kinds with a door of their own, Eat's: restaurants and recipes are not on Do.
ELSEWHERE = frozenset({RESTAURANT_KIND, RECIPE})


@bp.get("/ideas")
@bp.get("/do")
def ideas() -> str:
    """What could we do? (docs/INTERFACE.md section 4): the saved pile, what fits the next free
    stretch on top, then everything newest first. Restaurants have their own door (Eat)."""
    app = familydb_app()
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
        # What she found and judged worth putting forward (docs/FINDS.md), never what is for
        # the grown-ups alone where a kid reads.
        new_ideas = [
            views.new_idea_row(one, today)
            for one in find_store.recommended(conn, today=today, limit=NEW_IDEAS_MOST)
            if grown_up or not who_for.grown_ups_only(one.participants, people)
        ]
        chat.page_box(
            app, conn, people, scope={"label": "Things to do", "text": "About things to do:"}
        )
    if kind != RESTAURANT_KIND:
        found = [idea for idea in found if idea.kind not in ELSEWHERE]
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
    live = [idea for idea in listed if idea.status != "dropped" and idea.kind not in ELSEWHERE]
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
        new_ideas=[] if filtered else new_ideas,
        deciding=asking,
    )


# Her finds put forward under New ideas, at most.
NEW_IDEAS_MOST = 5
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
    app = familydb_app()
    settings = app.settings
    now = app.clock.now()
    today = app.clock.today()
    visitor = auth.visitor()
    with closing(app.connect()) as conn:
        record = idea_store.get(conn, idea_id)
        if record is None or presents.is_kept_from(conn, record, visitor.member):
            abort(404)
        if record.kind in ELSEWHERE and visitor.may("browse"):
            shell.belongs_to("eat")
        cooked = recipe_store.get(conn, idea_id) if record.kind == RECIPE else None
        original = (
            message_store.get(conn, record.source_message_id) if record.source_message_id else None
        )
        place = place_store.get(conn, record.place_id) if record.place_id else None
        outcomes = outcome_store.list_for_idea(conn, idea_id)
        plans = plan_store.for_idea(conn, idea_id)
        asking = who_asks(conn)
        looked_up = calls.last_lookup_turn(conn, idea_id) if visitor.may("manage") else None
        changed = calls.last_change(conn, idea_id=idea_id) if visitor.may("browse") else None
        family = member_store.list_all(conn)
        slots = views.slot_map(family)
        kept = presents.of_presents(conn, [record], family).get(idea_id)
        planned = [page_rows.plan_card(conn, app, p, today, slots) for p in reversed(plans)]
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
    place_panel = views.place_panel(place, now, settings.place_stale_days, today)
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
        facts=views.idea_facts(record, card, place_panel, grown_up=visitor.may("browse")),
        place=place_panel,
        recipe=views.recipe_panel(cooked, settings.tzinfo, grown_up=visitor.may("browse")),
        outcomes=[views.outcome_row(o) for o in reversed(outcomes)],
        plans=planned,
        changed=views.changed_line(
            changed, settings.tzinfo, assistant=personas.active(settings).name
        ),
    )


def _idea_form(record: Any = None) -> str:
    app = familydb_app()
    kind_given = request.args.get("kind", "").strip().casefold()[:40] if record is None else ""
    with closing(app.connect()) as conn:
        cooked = recipe_store.get(conn, record.id) if record is not None else None
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
        kind_given=kind_given,
        recipe=cooked,
        occasions=views.occasion_choices(),
    )


@bp.get("/ideas/new")
def new_idea() -> str:
    return _idea_form()


@bp.get(f"/idea/<int(max={MAX_ID}):idea_id>/edit")
def edit_idea(idea_id: int) -> str:
    with closing(familydb_app().connect()) as conn:
        record = idea_store.get(conn, idea_id)
    if record is None:
        abort(404)
    return _idea_form(record)


@bp.get("/restaurants")
@bp.get("/eat")
def restaurants() -> str:
    """What should we eat? (docs/INTERFACE.md section 4, docs/RECIPES.md): the pick to cook and
    the pick to eat out for the next meal, both chosen by code, then the recipes ranked for it
    and every saved restaurant with the one fact that decides."""
    app = familydb_app()
    now = app.clock.now()
    today = app.clock.today()
    stale_days = app.settings.place_stale_days
    visitor = auth.visitor()
    kid = not visitor.may("browse")
    who = request.args.get("who", "").strip()
    narrow = {key: request.args.get(key, "") == "1" for key in ("open", "close", "new")}
    tag = request.args.get("tag", "").strip().casefold()
    side = request.args.get("side", "")
    occasion = request.args.get("occasion", "")
    occasion = occasion if occasion in {key for key, _ in views.COOK_CHIPS} else ""
    if narrow["open"] or narrow["close"]:
        side = "out"  # open and close are a restaurant's
    elif occasion:
        side = "cook"
    with closing(app.connect()) as conn:
        cooking = _cook_rows(app, conn, now, today, occasion, kid) if side != "out" else []
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
        chat.page_box(app, conn, people, scope={"label": "Eat", "text": "About what to eat:"})
    cards = _eat_narrowed(cards, people, narrow, who, tag) if side != "cook" else []
    cards.sort(key=lambda card: card["score"])
    for card in cards:
        card.pop("idea")
    cooking = _cook_narrowed(cooking, people, narrow, who, tag)
    plain = not any(narrow.values()) and not who and not tag and not side and not occasion
    meal = views.meal_words(now.astimezone(app.settings.tzinfo))
    top = meal if cards and plain else None
    cook_top = meal if cooking and plain and cooking[0]["verdict"] != "out" else None
    for row in cooking:
        row.pop("idea")
    tags = sorted(set(tags) | {one for row in cooking for one in row["tags"]})
    return answer(
        "eat.html",
        cards=cards,
        top=top,
        cooking=cooking,
        cook_top=cook_top,
        side=side,
        summary=views.eat_both_summary(
            cooking[0] if cook_top else None, cards[0] if top else None, meal
        )
        if plain
        else views.eat_summary(cards[0] if cards else None, None),
        chips=_eat_chips(people, narrow, who, tags, tag, kid, side, occasion),
        can_list=visitor.may("change"),
    )


def _cook_rows(
    app: Any, conn: Any, now: Any, today: date, occasion: str, kid: bool
) -> list[dict[str, Any]]:
    """The family's recipes ranked for the next meal by code (familydb/meals.py): tonight's plans
    as the page reads them, the family's rest for recipes, and the situation asked for."""
    kept = recipe_store.live(conn)
    if not kept:
        return []
    seen = agenda.read(app, conn, today, today)
    tonight = meals.situation(
        now.astimezone(app.settings.tzinfo),
        agenda.on(seen, today),
        rest=meals.rest_days(conn, today),
    )
    if occasion:
        ranked = meals.rank(kept, tonight, meals.Asked(occasion=occasion, meal="dinner"))
    else:
        best = meals.pick(kept, tonight)
        ranked = meals.rank(kept, tonight, meals.Asked(meal="dinner"))
        if best is not None:
            ranked = [best, *(one for one in ranked if one.idea.id != best.idea.id)]
    rows = []
    for one in ranked:
        short = [r for r in one.reasons if r[:1].isdigit()][:1]
        rows.append(
            {
                "id": one.idea.id,
                "title": one.idea.title,
                "line": views.cook_line(one),
                "short": short[0] if short else one.reasons[0] if one.reasons else "",
                "verdict": one.verdict,
                "tags": one.idea.tags,
                "people": [],
                "who": views.participants_text(one.idea),
                "idea": one.idea,
                "shoppable": bool(one.recipe.ingredients) and not kid,
            }
        )
    return rows


def _cook_narrowed(
    rows: list[dict[str, Any]],
    people: list[member_store.Member],
    narrow: dict[str, bool],
    who: str,
    tag: str,
) -> list[dict[str, Any]]:
    kept = rows
    if narrow["new"]:
        kept = [row for row in kept if not row["idea"].times_done]
    if who == "kids":
        kept = [row for row in kept if who_for.with_the_kids(row["idea"], people)]
    elif who == "us":
        kept = [row for row in kept if who_for.just_us(row["idea"], people)]
    elif who:
        named = who.casefold()
        kept = [
            row
            for row in kept
            if any(named in part.casefold() for part in row["idea"].participants)
            or (row["idea"].suggested_by_name and row["idea"].suggested_by_name.casefold() == named)
        ]
    if tag:
        kept = [row for row in kept if tag in {one.casefold() for one in row["tags"]}]
    return kept


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
    side: str = "",
    occasion: str = "",
) -> list[dict[str, Any]]:
    chips = [
        {
            "label": "Cook",
            "href": url_for("web.restaurants", side="cook"),
            "on": side == "cook" and not occasion,
        },
        {"label": "Eat out", "href": url_for("web.restaurants", side="out"), "on": side == "out"},
        *(
            {
                "label": label,
                "href": url_for("web.restaurants", occasion=key),
                "on": occasion == key,
            }
            for key, label in views.COOK_CHIPS
        ),
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
