"""Recipes (docs/RECIPES.md): kept as ideas of kind recipe with their own facts, situations the
family said standing and the ones read from the facts kept as a guess, out of the cached prompt,
ranked by code for a meal, and put on the shopping list by code."""

from __future__ import annotations

import json
from datetime import date, datetime

import pytest

from familydb import meals
from familydb.agent.prompt import build_system_blocks
from familydb.store import db, ideas, lists, messages, plans
from familydb.store import recipes as store
from familydb.tools import ToolContext, build_registry
from tests.conftest import NOW_ISO, TZ

REGISTRY = build_registry()
LINK = "https://www.seriouseats.com/sheet-pan-chicken-fajitas-recipe"


def _as(conn, settings, clock, member, message_id=None):
    return ToolContext(
        conn=conn, settings=settings, clock=clock, member=member, message_id=message_id
    )


def _call(ctx, name, **args):
    result = REGISTRY.dispatch(name, args, ctx)
    return result, json.loads(result.content)


def _said(conn, member, text, update):
    with db.transaction(conn):
        return messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id=update,
            chat_id="42",
            member_id=member.id,
            text=text,
            now=NOW_ISO,
        )


def _recipe(ctx, title, **facts):
    _, made = _call(ctx, "add_idea", title=title, kind="recipe", recipe=facts)
    return made


def test_a_recipe_said_keeps_its_facts_and_guesses_what_nobody_said(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    made = _recipe(
        us,
        "Sheet-pan fajitas",
        total_minutes=25,
        serves=4,
        ingredients=["2 cups chopped onion", "1 lb chicken thighs", "salt to taste"],
    )
    assert made["kind"] == "recipe"
    assert made["recipe"]["occasions_guessed"] == ["weeknight"]
    assert "occasions" not in made["recipe"] or made["recipe"]["occasions"] == []
    kept = store.get(conn, made["id"])
    assert [one.item for one in kept.ingredients] == ["onion", "chicken thighs", "salt"]
    assert kept.ingredients[0].amount == "2 cups"
    # A recipe typed with no link has nothing to read, so it waits for no lookup.
    assert ideas.get(conn, made["id"]).enrichment == "skipped"


def test_any_way_of_saying_a_dish_is_a_recipe(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _, made = _call(us, "add_idea", title="Mum's lasagne", kind="Meal")
    assert made["kind"] == "recipe"


def test_a_situation_the_family_names_is_theirs_and_no_longer_a_guess(
    settings, clock, conn, family
):
    us = _as(conn, settings, clock, family["sam"])
    made = _recipe(us, "Chili", total_minutes=240, occasions_guessed=["freezer"])
    assert made["recipe"]["occasions_guessed"] == ["slow", "freezer"]
    _, changed = _call(us, "update_idea", id=made["id"], recipe={"occasions": ["slow"]})
    assert changed["recipe"]["occasions"] == ["slow"]
    assert changed["recipe"]["occasions_guessed"] == ["freezer"]


def test_a_link_alone_is_kept_once_and_waits_to_be_read(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _, made = _call(
        us, "add_idea", title="Sheet pan chicken fajitas", kind="recipe", url=LINK + "  "
    )
    kept = store.get(conn, made["id"])
    assert kept.source_url == LINK and kept.source_site == "seriouseats.com"
    assert kept.name_wanted  # the title is only the link's words, so the page's name may replace it
    assert ideas.get(conn, made["id"]).enrichment == "pending"
    assert store.links_to_read(conn, 5) == [made["id"]]
    _, again = _call(us, "add_idea", title="Those fajitas", kind="recipe", url=LINK)
    assert again["duplicate_of"] == made["id"]


def test_a_title_of_their_own_is_kept_when_the_page_is_read(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _, made = _call(us, "add_idea", title="Jo's fajitas", kind="recipe", url=LINK)
    assert not store.get(conn, made["id"]).name_wanted


def test_recipe_facts_on_an_outing_are_refused(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    refused, said = _call(us, "add_idea", title="Zoo", kind="outing", recipe={"total_minutes": 30})
    assert refused.is_error and "kind recipe" in said["error"]


def test_a_kid_may_add_a_recipe_and_ask_for_dinner(settings, clock, conn, family):
    kid = _as(conn, settings, clock, family["girls"])
    made = _recipe(kid, "Pancakes", total_minutes=20, occasions=["kids_cook"])
    _, found = _call(kid, "find_recipes")
    assert [one["id"] for one in found["recipes"]] == [made["id"]]


def test_a_change_to_a_recipe_is_taken_back(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    made = _recipe(us, "Soup", serves=4)
    asked = _said(conn, family["sam"], "it serves six", "u1")
    _call(
        _as(conn, settings, clock, family["sam"], asked.id),
        "update_idea",
        id=made["id"],
        recipe={"serves": 6},
    )
    assert store.get(conn, made["id"]).serves == 6
    undo = _said(conn, family["sam"], "undo that", "u2")
    undone = REGISTRY.dispatch("undo", {}, _as(conn, settings, clock, family["sam"], undo.id))
    assert not undone.is_error, undone.content
    assert store.get(conn, made["id"]).serves == 4


def test_describe_idea_reads_a_recipe_out(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    made = _recipe(us, "Dal", steps=["Rinse the lentils.", "Simmer 30 minutes."])
    _, told = _call(us, "describe_idea", id=made["id"])
    assert told["recipe"]["steps"] == ["Rinse the lentils.", "Simmer 30 minutes."]


def test_recipes_stay_out_of_the_cached_prompt(settings, clock, conn, family):
    before = build_system_blocks(conn, settings)
    _recipe(_as(conn, settings, clock, family["sam"]), "Sheet-pan fajitas", total_minutes=35)
    after = build_system_blocks(conn, settings)
    assert [block.text for block in before] == [block.text for block in after]
    assert "find_recipes" in before[0].text  # the spec says where they are


def test_the_engine_never_offers_a_recipe_to_go_and_do(env):
    made = _recipe(env.ctx, "Sheet-pan fajitas", total_minutes=35)
    result = env.registry.dispatch(
        "suggest",
        {"window": "this_weekend", "question": "what should we do?", "discover": False},
        env.ctx,
    )
    assert f'"idea_id": {made["id"]}' not in result.content


# -- ranking -------------------------------------------------------------------------------------


def test_find_recipes_rules_out_what_takes_too_long_and_says_why(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    quick = _recipe(us, "Quesadillas", total_minutes=15)
    slow = _recipe(us, "Short ribs", total_minutes=200)
    unknown = _recipe(us, "Mystery bake")
    _, found = _call(us, "find_recipes", most_minutes=30)
    listed = {one["id"]: one for one in found["recipes"]}
    assert listed[quick["id"]]["verdict"] == "good"
    assert listed[unknown["id"]]["verdict"] == "maybe"
    assert found["ruled_out"][0]["id"] == slow["id"]
    assert "3.3 h" in found["ruled_out"][0]["why"] or "takes" in found["ruled_out"][0]["why"]
    assert found["recipes"][0]["id"] == quick["id"]


def test_find_recipes_finds_by_ingredient(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _recipe(us, "Chana masala", ingredients=["2 cans chickpeas", "1 onion"])
    _recipe(us, "Pasta", ingredients=["1 lb spaghetti"])
    _, found = _call(us, "find_recipes", text="chickpeas")
    assert [one["title"] for one in found["recipes"]] == ["Chana masala"]


def test_a_plan_tonight_leaves_less_time_to_cook(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _recipe(us, "Roast chicken", total_minutes=90)
    _recipe(us, "Omelettes", total_minutes=15)
    with db.transaction(conn):
        plans.insert(
            conn,
            title="Recital",
            start="2026-09-20T18:30:00-07:00",
            end="2026-09-20T20:00:00-07:00",
            all_day=False,
            now=NOW_ISO,
        )
    _, found = _call(us, "find_recipes")
    assert [one["title"] for one in found["recipes"]] == ["Omelettes"]
    assert found["ruled_out"][0]["title"] == "Roast chicken"
    assert "Recital" in found["ruled_out"][0]["why"]


def test_made_lately_rests_and_a_favourite_does_not(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    tacos = _recipe(us, "Tacos", total_minutes=30)
    _recipe(us, "Curry", total_minutes=40)
    done, said = _call(
        us, "record_outcome", idea_id=tacos["id"], happened_on="2026-09-17", rating=9
    )
    assert not done.is_error, said
    _, found = _call(us, "find_recipes")
    assert found["recipes"][0]["title"] == "Curry"
    resting = next(one for one in found["recipes"] if one["title"] == "Tacos")
    assert resting["verdict"] == "maybe" and "3 days ago" in resting["why"]
    _, loved = _call(us, "find_recipes", favorites=True)
    assert loved["recipes"][0]["title"] == "Tacos"


@pytest.mark.parametrize(
    ("facts", "guessed"),
    [
        ({"total_minutes": 20}, ["weeknight"]),
        ({"total_minutes": 300}, ["slow"]),
        ({"prep_note": "Marinate the night before"}, ["prep_ahead"]),
        ({"serves": 8}, ["family_dinner", "guests"]),
        ({"steps": ["Cool, then freeze for up to 3 months."]}, ["freezer"]),
        ({"total_minutes": 60, "serves": 4}, []),
        ({"total_minutes": 5, "name": "Overnight oats"}, ["prep_ahead", "breakfast"]),
        ({"total_minutes": 15, "name": "Pancakes"}, ["breakfast"]),
    ],
)
def test_situations_are_read_from_the_facts(facts, guessed):
    assert meals.guess_occasions(store.Recipe(idea_id=1, **facts)) == guessed


def test_tonight_is_read_from_the_plans_that_cut_it_short():
    class Plan:
        def __init__(self, start, title="Game", all_day=False):
            self.start, self.title, self.all_day = start, title, all_day

    now = datetime(2026, 10, 21, 16, 0, tzinfo=TZ)
    tonight = meals.situation(
        now, [Plan("2026-10-21T19:00:00-07:00"), Plan("2026-10-21", "x", True)]
    )
    assert tonight.minutes_free == 90 and tonight.plan == "Game" and not tonight.weekend
    assert meals.situation(now).minutes_free is None
    assert meals.situation(datetime(2026, 10, 24, 12, 0, tzinfo=TZ)).weekend


def test_the_page_pick_on_a_weeknight_is_a_weeknight_one(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _recipe(us, "Lasagne", total_minutes=120)
    _recipe(us, "Stir fry", total_minutes=25)
    weeknight = meals.situation(datetime(2026, 10, 21, 16, 0, tzinfo=TZ))
    best = meals.pick(store.live(conn), weeknight)
    assert best is not None and best.idea.title == "Stir fry"


def test_a_breakfast_is_not_offered_for_dinner(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _recipe(us, "Overnight oats", total_minutes=5, occasions=["breakfast", "prep_ahead"])
    _recipe(us, "Stir fry", total_minutes=25)
    _, found = _call(us, "find_recipes")
    assert [one["title"] for one in found["recipes"]] == ["Stir fry"]
    assert "not a dinner" in found["ruled_out"][0]["why"]
    _, mornings = _call(us, "find_recipes", occasion="breakfast")
    assert mornings["recipes"][0]["title"] == "Overnight oats"


def test_a_family_rest_for_recipes_is_held(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    _call(
        us,
        "remember",
        changes=[
            {
                "action": "add",
                "fact": "no repeat dinners within two weeks",
                "rule": {"rest_days": 14, "rest_kind": "recipe"},
            }
        ],
    )
    assert meals.rest_days(conn, date(2026, 9, 20)) == 14


# -- the grocery list ----------------------------------------------------------------------------


def test_recipes_go_on_the_list_with_their_amounts_and_without_the_staples(
    settings, clock, conn, family
):
    us = _as(conn, settings, clock, family["sam"])
    fajitas = _recipe(
        us,
        "Sheet-pan fajitas",
        ingredients=["2 onions, sliced", "1 lb chicken thighs", "Salt and pepper to taste"],
    )
    soup = _recipe(us, "Tortilla soup", ingredients=["1 onion", "4 cups broth", "2 tbsp olive oil"])
    _call(us, "shopping_list", action="add", items=["broth"])
    _, said = _call(
        us, "shopping_list", action="from_recipes", idea_ids=[fajitas["id"], soup["id"]]
    )
    assert said["added"] == ["onions", "chicken thighs"]
    assert said["already"] == ["broth"]
    assert said["left_out_staples"] == ["salt and pepper", "olive oil"]
    on_list = {item.text: item for item in lists.items(conn, lists.find(conn, "shopping"))}
    assert on_list["onions"].note == "2 (Sheet-pan fajitas), 1 (Tortilla soup)"
    assert on_list["broth"].note == "4 cups (Tortilla soup)"


def test_a_grocery_list_is_the_grown_ups_and_is_taken_back(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    made = _recipe(us, "Dal", ingredients=["1 cup red lentils", "1 onion"])
    refused, said = _call(
        _as(conn, settings, clock, family["girls"]),
        "shopping_list",
        action="from_recipes",
        idea_ids=[made["id"]],
    )
    assert refused.is_error and "ask a parent" in said["error"]
    asked = _said(conn, family["sam"], "put the dal on the list", "u1")
    _call(
        _as(conn, settings, clock, family["sam"], asked.id),
        "shopping_list",
        action="from_recipes",
        idea_ids=[made["id"]],
    )
    undo = _said(conn, family["sam"], "undo that", "u2")
    REGISTRY.dispatch("undo", {}, _as(conn, settings, clock, family["sam"], undo.id))
    assert lists.items(conn, lists.find(conn, "shopping")) == []


def test_a_recipe_with_no_ingredients_yet_says_so(settings, clock, conn, family):
    us = _as(conn, settings, clock, family["sam"])
    made = _recipe(us, "Something")
    refused, said = _call(us, "shopping_list", action="from_recipes", idea_ids=[made["id"]])
    assert refused.is_error and "no ingredients kept" in said["error"]
    outing = _call(us, "add_idea", title="Zoo", kind="outing")[1]
    refused, said = _call(us, "shopping_list", action="from_recipes", idea_ids=[outing["id"]])
    assert refused.is_error and "not a recipe" in said["error"]
