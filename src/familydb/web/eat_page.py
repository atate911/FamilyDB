"""What should we eat? (docs/INTERFACE.md section 4, docs/RECIPES.md): one door for the most
frequent decision, with two answers. The overview names the pick to cook and the pick to eat out
for the next meal, with the first few of each; **Cook** is every recipe ranked for that meal, with
its own chips and the grocery list; **Eat out** is every restaurant, with its own. A household
keeping only one of the two sees that list whole. All by code, no model call."""

from __future__ import annotations

from contextlib import closing
from datetime import date, datetime
from typing import Any

from flask import request, url_for

from familydb import agenda, meals, presents
from familydb.store import ideas as idea_store
from familydb.store import members as member_store
from familydb.store import places as place_store
from familydb.store import recipes as recipe_store
from familydb.suggest import people as who_for
from familydb.web import auth, chat, views
from familydb.web.answers import answer
from familydb.web.pages import bp, familydb_app

RESTAURANT_KIND = "restaurant"
LIST_LIMIT = 200
# About this far, or nearer, is Close.
CLOSE_MINUTES = 20
# How many of each side the overview shows under its pick.
OVERVIEW = 3
SIDES = ("cook", "out")
# The situations asked for at breakfast or for a lunchbox are not dinners.
NOT_DINNER = frozenset({"breakfast", "lunchbox"})


@bp.get("/restaurants")
@bp.get("/eat")
def restaurants() -> str:
    app = familydb_app()
    now = app.clock.now()
    today = app.clock.today()
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
    side = side if side in SIDES else ""
    with closing(app.connect()) as conn:
        cooking = _cook_rows(app, conn, now, today, occasion, kid)
        people = member_store.list_all(conn)
        cards = _restaurant_cards(app, conn, now, today, visitor, who, people, kid)
        chat.page_box(app, conn, people, scope={"label": "Eat", "text": "About what to eat:"})
    # With only one of the two kept, Eat is that list, whole, as it always was.
    if not side and not cooking:
        side = "out"
    elif not side and not cards:
        side = "cook"
    both = bool(cooking) and bool(cards)
    meal = views.meal_words(now.astimezone(app.settings.tzinfo))
    plain = not any(narrow.values()) and not who and not tag and not occasion
    cook_all, out_all = len(cooking), len(cards)
    cook_tags = sorted({one.casefold() for row in cooking for one in row["tags"]})
    # A situation is a chip only when some recipe has it (Quick always: minutes say it).
    cook_occasions = {"weeknight"}.union(*(row["occasions"] for row in cooking))
    out_tags = sorted({one.casefold() for card in cards for one in card["tags"]})
    if side != "out":
        cooking = _cook_narrowed(cooking, people, narrow, who, tag)
    if side != "cook":
        cards = _out_narrowed(cards, people, narrow, who, tag)
    cards.sort(key=lambda card: card["score"])
    cook_pick = cooking[0] if cooking and plain and cooking[0]["verdict"] != "out" else None
    out_pick = cards[0] if cards and plain else None
    for row in (*cooking, *cards):
        row.pop("idea", None)
    if not side:  # the next meal: only what fits it, the first few of each
        cooking = [row for row in cooking if row["verdict"] != "out"][:OVERVIEW]
        cards = cards[:OVERVIEW]
    return answer(
        "eat.html",
        side=side,
        both=both,
        meal=meal,
        tabs=_tabs(side, meal, cook_all, out_all) if both else [],
        cooking=cooking if side != "out" else [],
        cards=cards if side != "cook" else [],
        cook_top=meal if cook_pick is not None and side != "out" else None,
        top=meal if out_pick is not None and side != "cook" else None,
        cook_all=cook_all,
        out_all=out_all,
        summary=_summary(side, cook_pick, out_pick, meal, plain),
        chips=_cook_chips(
            cooking_tags=cook_tags,
            present=cook_occasions,
            occasion=occasion,
            narrow=narrow,
            tag=tag,
        )
        if side == "cook"
        else _out_chips(people, narrow, who, out_tags, tag, kid)
        if side == "out"
        else [],
        can_list=visitor.may("change") and side == "cook",
    )


def _summary(
    side: str,
    cook: dict[str, Any] | None,
    out: dict[str, Any] | None,
    meal: str,
    plain: bool,
) -> str:
    if not plain:
        return ""
    if side == "cook":
        return views.eat_both_summary(cook, None, meal)
    if side == "out":
        return views.eat_both_summary(None, out, meal)
    return views.eat_both_summary(cook, out, meal)


def _tabs(side: str, meal: str, cook: int, out: int) -> list[dict[str, Any]]:
    """The overview, Cook and Eat out, as Plans' List and Month are drawn."""
    return [
        {"label": meal, "href": url_for("web.restaurants"), "on": not side, "n": None},
        {
            "label": "Cook",
            "href": url_for("web.restaurants", side="cook"),
            "on": side == "cook",
            "n": cook,
        },
        {
            "label": "Eat out",
            "href": url_for("web.restaurants", side="out"),
            "on": side == "out",
            "n": out,
        },
    ]


def _restaurant_cards(
    app: Any,
    conn: Any,
    now: datetime,
    today: date,
    visitor: Any,
    who: str,
    people: list[member_store.Member],
    kid: bool,
) -> list[dict[str, Any]]:
    """Every restaurant not dropped, with the one fact that decides and how it ranks."""
    found = idea_store.search(
        conn,
        kind=RESTAURANT_KIND,
        participant=who if who and who not in ("kids", "us") else None,
        limit=LIST_LIMIT,
        exclude_ids=presents.kept_ids(conn, visitor.member),
        newest_first=True,
    )
    slots = views.slot_map(people)
    cards = []
    for idea in found:
        card = views.restaurant_card(
            idea,
            place_store.get(conn, idea.place_id) if idea.place_id else None,
            today,
            now,
            app.settings.place_stale_days,
        )
        card["people"] = views.people_for(idea, slots)
        card["who"] = views.names_text(card["people"])
        card["line"] = views.eat_line(card, idea, kid=kid)
        card["score"] = views.eat_score(card, idea)
        card["idea"] = idea
        cards.append(card)
    return cards


def _cook_rows(
    app: Any, conn: Any, now: datetime, today: date, occasion: str, kid: bool
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
    meal = None if occasion in NOT_DINNER else "dinner"
    if occasion:
        ranked = meals.rank(kept, tonight, meals.Asked(occasion=occasion, meal=meal))
    else:
        best = meals.pick(kept, tonight)
        ranked = meals.rank(kept, tonight, meals.Asked(meal=meal))
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
                "occasions": {*one.recipe.occasions, *one.recipe.occasions_guessed},
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
    if tag:
        kept = [row for row in kept if tag in {one.casefold() for one in row["tags"]}]
    return kept


def _out_narrowed(
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


def _cook_chips(
    *,
    cooking_tags: list[str],
    present: set[str],
    occasion: str,
    narrow: dict[str, bool],
    tag: str,
) -> list[dict[str, Any]]:
    """Cook's own chips: the situations, new to us, with the kids, and the cuisines in the pile."""
    chips = [
        {
            "label": label,
            "href": url_for("web.restaurants", occasion=key),
            "on": occasion == key,
        }
        for key, label in views.COOK_CHIPS
        if key in present or key == occasion
    ]
    chips += [
        {
            "label": "New to us",
            "href": url_for("web.restaurants", side="cook", new="1"),
            "on": narrow["new"],
        },
        {
            "label": "With the kids",
            "href": url_for("web.restaurants", side="cook", who="kids"),
            "on": request.args.get("who") == "kids",
        },
    ]
    chips += [
        {
            "label": one.capitalize(),
            "href": url_for("web.restaurants", side="cook", tag=one),
            "on": tag == one,
        }
        for one in cooking_tags[:8]
    ]
    if any(chip["on"] for chip in chips):
        chips.insert(
            0,
            {"label": "Every recipe", "href": url_for("web.restaurants", side="cook"), "on": False},
        )
    return chips


def _out_chips(
    people: list[member_store.Member],
    narrow: dict[str, bool],
    who: str,
    tags: list[str],
    tag: str,
    kid: bool,
) -> list[dict[str, Any]]:
    """Eat out's own chips, as the restaurants always had them."""
    chips = [
        {"label": "Open today", "href": url_for("web.restaurants", open="1"), "on": narrow["open"]},
        {"label": "Close", "href": url_for("web.restaurants", close="1"), "on": narrow["close"]},
        {
            "label": "New to us",
            "href": url_for("web.restaurants", side="out", new="1"),
            "on": narrow["new"],
        },
    ]
    if not kid:
        chips.append(
            {
                "label": "Just us",
                "href": url_for("web.restaurants", side="out", who="us"),
                "on": who == "us",
            }
        )
        chips.append(
            {
                "label": "With the kids",
                "href": url_for("web.restaurants", side="out", who="kids"),
                "on": who == "kids",
            }
        )
    chips += [
        {
            "label": one.capitalize(),
            "href": url_for("web.restaurants", side="out", tag=one),
            "on": tag == one,
        }
        for one in tags[:8]
    ]
    if not kid:
        chips += [
            {
                "label": person.display_name,
                "href": url_for("web.restaurants", side="out", who=person.display_name),
                "on": who.casefold() == person.display_name.casefold(),
            }
            for person in people
        ]
    if any(chip["on"] for chip in chips):
        chips.insert(
            0, {"label": "Every place", "href": url_for("web.restaurants", side="out"), "on": False}
        )
    return chips
