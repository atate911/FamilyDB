"""Recipes on the page (docs/RECIPES.md): What should we eat ranks them beside the restaurants,
a recipe's page draws it with her guess to take or drop, and recipes go on the shopping list by
the same tool she calls. Every form is a tool call; no page view is a model call."""

from __future__ import annotations

import json
import re

from familydb.store import lists
from familydb.store import recipes as store
from familydb.tools import ToolContext, build_registry
from tests.test_lists import KIDS, _browser_as, _start, app, sam  # noqa: F401
from tests.test_web_edits import _client, _said
from tests.test_web_logins import _tokens

REGISTRY = build_registry()


def _recipe(conn, settings, clock, member, title, **facts):
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=member)
    result = REGISTRY.dispatch("add_idea", {"title": title, "kind": "recipe", "recipe": facts}, ctx)
    return json.loads(result.content)


def _token(text: str) -> dict[str, str]:
    return dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', text))


def test_eat_ranks_what_to_cook_beside_the_restaurants(settings, clock, conn, family):
    _recipe(conn, settings, clock, family["sam"], "Stir fry", total_minutes=25, serves=4)
    _recipe(conn, settings, clock, family["sam"], "Short ribs", total_minutes=240)
    page = _client(settings, clock).get("/eat").text
    assert "What should we eat?" in page and ">Cook<" in page
    assert "Tonight: Stir fry, 25 min." in page
    cook = page[page.index('id="h-cook"') :]
    assert cook.index("Stir fry") < cook.index("Short ribs")
    assert "looks like weeknight" in cook  # her guess, marked as one
    # Narrowed to quick ones, the slow one is said last and why.
    quick = _client(settings, clock).get("/eat?occasion=weeknight").text
    assert "r--faded" in quick and "too long for a weeknight" in quick


def test_a_recipe_page_draws_it_and_her_guess_is_taken_with_a_tap(settings, clock, conn, family):
    made = _recipe(
        conn,
        settings,
        clock,
        family["sam"],
        "Dal",
        total_minutes=30,
        ingredients=["1 cup red lentils", "1 onion"],
        steps=["Rinse.", "Simmer."],
    )
    browser = _client(settings, clock)
    page = browser.get(f"/idea/{made['id']}").text
    assert "1 cup red lentils" in page and "<li>Simmer.</li>" in page
    assert "Looks like weeknight" in page and "That\u2019s right" in page
    taken = browser.post(
        f"/idea/{made['id']}/occasion",
        data={**_token(page), "occasion": "weeknight", "right": "yes"},
        follow_redirects=True,
    )
    assert f"#{made['id']} is weeknight, then." in _said(taken)
    kept = store.get(conn, made["id"])
    assert kept.occasions == ["weeknight"] and kept.occasions_guessed == []


def test_ticked_recipes_go_on_the_shopping_list_with_their_amounts(settings, clock, conn, family):
    one = _recipe(conn, settings, clock, family["sam"], "Fajitas", ingredients=["2 onions", "salt"])
    two = _recipe(conn, settings, clock, family["sam"], "Soup", ingredients=["1 onion"])
    browser = _client(settings, clock)
    page = browser.get("/eat").text
    assert 'name="idea_ids"' in page and "Grocery list for these" in page
    listed = browser.post(
        "/eat/grocery-list",
        data={**_token(page), "idea_ids": [str(one["id"]), str(two["id"])]},
        follow_redirects=True,
    )
    assert "On the shopping list for Fajitas, Soup: onions." in _said(listed)
    assert "Left off: salt." in _said(listed)
    shown = browser.get("/lists").text
    assert "2 (Fajitas), 1 (Soup)" in shown
    assert [item.text for item in lists.items(conn, lists.find(conn, "shopping"))] == ["onions"]


def test_the_recipe_form_keeps_what_is_typed(settings, clock, conn, family):
    browser = _client(settings, clock)
    form = browser.get("/ideas/new?kind=recipe").text
    assert 'value="recipe"' in form and 'name="ingredients"' in form
    added = browser.post(
        "/ideas/new",
        data={
            **_token(form),
            "title": "Pancakes",
            "kind": "recipe",
            "recipe_shown": "1",
            "total_minutes": "20",
            "serves": "4",
            "occasions": ["kids_cook"],
            "ingredients": "1 cup flour\n2 eggs\n",
            "steps": "Mix.\nFry.",
        },
        follow_redirects=True,
    )
    assert "Saved #" in _said(added)
    idea_id = int(re.search(r"Saved #(\d+)", _said(added)).group(1))
    kept = store.get(conn, idea_id)
    assert kept.serves == 4 and kept.occasions == ["kids_cook"]
    assert [one.item for one in kept.ingredients] == ["flour", "eggs"]
    assert kept.steps == ["Mix.", "Fry."]


def test_a_kid_sees_the_recipes_and_no_boxes(app, sam, conn, settings, clock, family):  # noqa: F811
    _recipe(conn, settings, clock, family["sam"], "Tacos", ingredients=["8 tortillas"])
    kid = _browser_as(app, "the girls", _start(sam, family["girls"].id))
    kid.post("/you", data={**_tokens(kid, "/you"), "new": KIDS, "again": KIDS})
    page = kid.get("/eat").text
    assert "Tacos" in page and 'name="idea_ids"' not in page
