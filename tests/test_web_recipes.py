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
    result = REGISTRY.dispatch("recipe", {"action": "save", "title": title, **facts}, ctx)
    return json.loads(result.content)


def _token(text: str) -> dict[str, str]:
    return dict(re.findall(r'name="(csrf|once)" value="([^"]+)"', text))


def test_eat_ranks_what_to_cook_beside_the_restaurants(settings, clock, conn, family):
    _recipe(conn, settings, clock, family["sam"], "Stir fry", total_minutes=25, serves=4)
    _recipe(conn, settings, clock, family["sam"], "Short ribs", total_minutes=240)
    page = _client(settings, clock).get("/eat").text
    assert "What should we eat?" in page and "Tonight: Stir fry, 25 min." in page
    assert 'aria-label="Cook or eat out"' not in page  # only recipes kept: no tabs, the list whole
    cook = page[page.index('id="h-cook"') :]
    assert cook.index("Stir fry") < cook.index("Short ribs")
    assert "looks like" not in cook  # her guesses are on a recipe's page, not in its row
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
    assert "guess: weeknight" in page and "That\u2019s right" in page
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
    page = browser.get("/eat?side=cook").text
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


def test_now_names_a_recipe_to_cook_in_the_afternoon(settings, clock, conn, family):
    made = _recipe(conn, settings, clock, family["sam"], "Stir fry", total_minutes=25)
    page = _client(settings, clock).get("/").text  # Sunday, 2:03 pm
    assert "To cook" in page and f'href="/idea/{made["id"]}">Stir fry</a>, 25 min' in page


def test_dinner_in_plain_words_is_answered_by_code(settings, clock, conn, family):
    from familydb import commands
    from familydb.app import App
    from familydb.channels.base import IncomingMessage

    running = App(settings, clock)
    asked = commands.in_words(
        running, conn, IncomingMessage("telegram", "1", "1001", "1001", "What's for dinner?")
    )
    assert asked is not None and asked.text.startswith("No recipes saved yet.")
    _recipe(conn, settings, clock, family["sam"], "Stir fry", total_minutes=25, serves=4)
    _recipe(conn, settings, clock, family["sam"], "Dal", total_minutes=40)
    asked = commands.answer(running, IncomingMessage("telegram", "2", "1001", "1001", "/dinner"))
    lines = asked.text.splitlines()
    assert lines[0] == "For dinner tonight, from your recipes:"
    assert lines[1].startswith("#1 Stir fry: 25 min, serves 4")
    assert conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0] == 0


def test_with_both_kept_eat_has_tabs_and_each_its_own_chips(settings, clock, conn, family):
    from tests.test_web import _idea

    for title in ("Stir fry", "Dal", "Tacos", "Soup"):
        _recipe(conn, settings, clock, family["sam"], title, total_minutes=25)
    _idea(conn, "Ramen place", kind="restaurant")
    browser = _client(settings, clock)
    page = browser.get("/eat").text
    assert 'aria-label="Cook or eat out"' in page and '>Cook <span class="n">4</span>' in page
    assert "To cook" in page and "To eat out" in page and "All 4" in page
    assert page.count('class="r__t"') == 3 + 1  # the first three of each
    assert 'aria-label="Narrow it"' not in page  # chips belong to a tab
    cook = browser.get("/eat?side=cook").text
    assert "Quick" in cook and "Open today" not in cook and cook.count('class="r__t"') == 4
    out = browser.get("/eat?side=out").text
    assert "Open today" in out and "Quick" not in out and "Stir fry" not in out


def test_the_kitchen_board_names_a_recipe_to_cook(settings, clock, conn, family):
    _recipe(conn, settings, clock, family["sam"], "Stir fry", total_minutes=25)
    board = _client(settings, clock).get("/board").text
    assert "To cook:" in board and ">Stir fry</a>, 25 min" in board


def test_a_recipe_page_reads_as_a_recipe(settings, clock, conn, family):
    made = _recipe(
        conn, settings, clock, family["sam"], "Dal", total_minutes=30, ingredients=["1 onion"]
    )
    page = _client(settings, clock).get(f"/idea/{made['id']}").text
    assert "Not made yet" in page and "An idea" not in page
    assert "Takes" in page and "Plan it for a night" in page
    assert page.index("Put the ingredients on the list") < page.index("Plan it for a night")
    assert "What goes with it?" in page  # her quick sentences are a recipe's


def test_one_undo_never_takes_back_half_an_edit(settings, clock, conn, family):
    made = _recipe(conn, settings, clock, family["sam"], "Soup", serves=4, ingredients=["1 onion"])
    browser = _client(settings, clock)
    form = browser.get(f"/idea/{made['id']}/edit").text
    fields = dict(re.findall(r'name="(csrf|once|revision)" value="([^"]+)"', form))
    base = {
        **fields,
        "title": "Soup",
        "kind": "recipe",
        "recipe_shown": "1",
        "ingredients": "1 onion",
        "steps": "",
    }
    changed = browser.post(
        f"/idea/{made['id']}/edit", data={**base, "serves": "6"}, follow_redirects=True
    )
    assert "Undo" in changed.text  # only a fact moved: its Undo is all of it
    form = browser.get(f"/idea/{made['id']}/edit").text
    fields = dict(re.findall(r'name="(csrf|once|revision)" value="([^"]+)"', form))
    both = browser.post(
        f"/idea/{made['id']}/edit",
        data={**base, **fields, "title": "Leek soup", "serves": "8"},
        follow_redirects=True,
    )
    assert "Changed #" in _said(both) and ">Undo<" not in both.text


def test_a_kid_is_shown_no_guesses(app, sam, conn, settings, clock, family):  # noqa: F811
    made = _recipe(conn, settings, clock, family["sam"], "Stir fry", total_minutes=20)
    kid = _browser_as(app, "the girls", _start(sam, family["girls"].id))
    kid.post("/you", data={**_tokens(kid, "/you"), "new": KIDS, "again": KIDS})
    page = kid.get(f"/idea/{made['id']}").text
    assert "Stir fry" in page and "guess" not in page.casefold()


def test_a_grocery_tick_is_a_whole_target_and_the_one_action(settings, clock, conn, family):
    _recipe(conn, settings, clock, family["sam"], "Stir fry", ingredients=["1 onion"])
    page = _client(settings, clock).get("/eat?side=cook").text
    assert 'class="check check--tick"' in page
    assert 'class="btn btn--primary btn--sm" type="submit">' in page  # Grocery list for these


def test_tonight_s_pick_and_the_cook_list_agree(settings, thursday_clock, conn, family):
    """On a weeknight with nothing quick enough, the time alone decides, and the one order
    (meals.rank_for_meal) names the pick and draws the list: never a pick the list rules out."""
    made = _recipe(conn, settings, thursday_clock, family["sam"], "Short ribs", total_minutes=240)
    page = _client(settings, thursday_clock).get("/eat").text
    assert "Tonight: Short ribs, 4 h." in page
    cook = page[page.index('id="h-cook"') :]
    assert f'href="/idea/{made["id"]}"' in cook and "r--faded" not in cook


def test_an_idea_made_a_recipe_with_empty_boxes_keeps_its_undo(settings, clock, conn, family):
    """Turning an outing into a recipe without filling a box is one change (update_idea), so its
    Undo stands: empty boxes against nothing kept are no second write."""
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    made = json.loads(
        REGISTRY.dispatch("add_idea", {"title": "Pancakes", "kind": "outing"}, ctx).content
    )
    browser = _client(settings, clock)
    form = browser.get(f"/idea/{made['id']}/edit").text
    fields = dict(re.findall(r'name="(csrf|once|revision)" value="([^"]+)"', form))
    changed = browser.post(
        f"/idea/{made['id']}/edit",
        data={
            **fields,
            "title": "Pancakes",
            "kind": "recipe",
            "recipe_shown": "1",
            "ingredients": "",
            "steps": "",
            "serves": "",
            "total_minutes": "",
        },
        follow_redirects=True,
    )
    assert "Changed #" in _said(changed) and ">Undo<" in changed.text
