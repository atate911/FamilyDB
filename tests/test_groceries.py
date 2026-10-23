"""What to buy in a recipe's line (familydb/groceries.py), by rule. A line the family pastes that
reads wrong is added here with what it should read as."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from familydb import groceries
from familydb.store import db
from familydb.store.recipes import Recipe
from tests.conftest import NOW_ISO

LINES = [
    ("2 cups chopped onion", "onion", "2 cups"),
    ("1 (28-oz) can crushed tomatoes", "crushed tomatoes", "1 (28-oz) can"),
    ("1 (14-oz) can black beans, drained and rinsed", "black beans", "1 (14-oz) can"),
    ("½ tsp kosher salt", "kosher salt", "1/2 tsp"),
    ("1½ cups rice", "rice", "1 1/2 cups"),
    ("3 cloves garlic, minced", "garlic", "3 cloves"),
    ("1 1/2 pounds boneless skinless chicken thighs", "boneless skinless chicken thighs", None),
    ("Salt and pepper to taste", "salt and pepper", None),
    ("2 large red bell peppers, sliced", "red bell peppers", "2 large"),
    ("Juice of 1 lime", "lime", "juice of 1"),
    ("1-2 jalapeños", "jalapeños", "1-2"),
    ("8 small flour tortillas", "flour tortillas", "8 small"),
    ("• 2 tbsp olive oil", "olive oil", "2 tbsp"),
    ("Fresh cilantro, for serving", "fresh cilantro", None),
    ("4 cups low-sodium chicken broth (or vegetable)", "low-sodium chicken broth", "4 cups"),
    ("a pinch of chili flakes", "chili flakes", "a pinch"),
    ("an onion", "onion", "an"),
    ("apples, cored", "apples", None),
]


@pytest.mark.parametrize(("line", "item", "amount"), LINES)
def test_a_line_is_read_into_what_to_buy(line, item, amount):
    read = groceries.parse(line)
    assert read.item == item
    if amount is not None:
        assert read.amount == amount
    assert read.text == line


def test_onions_and_onion_are_one_thing():
    assert groceries.key("Onions") == groceries.key("onion")
    assert groceries.key("tomatoes") == "tomato"
    assert groceries.key("berries") == "berry"
    assert groceries.key("swiss cheese") == "swiss cheese"


@pytest.mark.parametrize("item", ["salt", "Kosher salt", "salt and pepper", "olive oil", "water"])
def test_staples_are_left_off(item):
    assert groceries.staple(item)


def test_what_one_buys_is_not_a_staple():
    assert not groceries.staple("chicken thighs")


def test_peppers_to_buy_are_not_the_pepper_mill():
    assert not groceries.staple("peppers", "3")
    assert not groceries.staple("pepper", "1")  # one bell pepper
    assert groceries.staple("pepper", "1/2 tsp")
    assert groceries.staple("pepper")


# -- the shop: sections, the pantry, stand-ins (docs/RECIPES.md) -----------------------------------


@pytest.mark.parametrize(
    ("item", "amount", "section"),
    [
        ("cherry tomatoes", None, "Produce"),
        ("red bell pepper", "1", "Produce"),
        ("fresh oregano", None, "Produce"),
        ("flour tortillas", "8", "Bakery"),
        ("boneless chicken thighs", "2 lb", "Meat & fish"),
        ("ground beef", "1 lb", "Meat & fish"),
        ("sour cream", "1/2 cup", "Dairy & eggs"),
        ("eggs", "2", "Dairy & eggs"),
        ("coconut milk", "1 can", "Dry goods & cans"),
        ("chicken stock", "2 cups", "Dry goods & cans"),
        ("dried cranberries", "1 cup", "Dry goods & cans"),
        ("tomatoes", "1 can", "Produce"),  # the word decides, not the amount
        ("canned tomatoes", "1", "Dry goods & cans"),
        ("frozen peas", "1 cup", "Frozen"),
        ("ice cream", None, "Frozen"),
        ("dry white wine", "1/2 cup", "Dry goods & cans"),
        ("dry white wine", "1 bottle", "Drinks"),
        ("orange juice", "1 cup", "Drinks"),
        ("birthday candles", None, "Other"),
    ],
)
def test_a_thing_is_found_in_its_section_of_the_store(item, amount, section):
    assert groceries.section_of(item, amount) == section


@pytest.mark.parametrize(
    ("item", "amount", "pantry"),
    [
        ("salt", None, True),
        ("smoked paprika", "1 tsp", True),
        ("ground cumin", "1 tsp", True),
        ("dried oregano", "1 tsp", True),
        ("bay leaves", "2", True),
        ("red pepper flakes", "1/2 tsp", True),
        ("soy sauce", "2 tbsp", True),
        ("rice vinegar", "1 tbsp", True),
        ("baking powder", "1 tsp", True),
        ("fresh oregano", "1 tbsp", False),
        ("ground beef", "1 lb", False),
        ("dried cranberries", "1 cup", False),
        ("onion", "1", False),
        ("gochujang", "2 tbsp", False),
    ],
)
def test_what_a_kitchen_has_is_the_pantry_s(item, amount, pantry):
    assert groceries.pantry(item, amount) is pantry


def test_the_family_s_own_pantry_list_counts(settings, clock, conn, family):
    """Whatever the family keeps on a list named pantry is checked, not bought: onions here."""
    from familydb.store import lists

    assert groceries.family_pantry(conn) == frozenset()
    with db.transaction(conn):
        ref = lists.list_id(conn, "pantry", NOW_ISO)
        lists.add(conn, ref, "Onions", by=None, now=NOW_ISO)
    have = groceries.family_pantry(conn)
    assert have == frozenset({"onion"})
    assert groceries.pantry("1 onion", have=have) is False  # the whole item, one form
    assert groceries.pantry("onion", have=have) and groceries.pantry("onions", have=have)


def test_what_could_stand_in_is_a_table():
    assert groceries.alternatives("buttermilk")[0].startswith("milk with a spoon")
    assert groceries.alternatives("capers") == ("chopped green olives",)  # one form
    assert groceries.alternatives("fresh cilantro") == groceries.alternatives("cilantro")
    assert groceries.alternatives("chicken thighs") == ()


def test_a_recipe_s_shopping_walks_the_store_with_the_pantry_apart():
    recipe = Recipe(
        idea_id=1,
        ingredients=[
            groceries.parse(line)
            for line in (
                "1 cup buttermilk",
                "2 limes",
                "1 tsp smoked paprika",
                "8 flour tortillas",
                "1 lb chicken thighs",
                "2 limes, for serving",
                "salt",
            )
        ],
    )
    on_list = {"lime": SimpleNamespace(text="limes", ticked_at=None)}
    shop = groceries.shopping(recipe, on_list)
    assert [section for section, _ in shop.sections] == [
        "Produce",
        "Bakery",
        "Meat & fish",
        "Dairy & eggs",
    ]
    assert [one.item for one in shop.to_buy] == [
        "limes",
        "flour tortillas",
        "chicken thighs",
        "buttermilk",
    ]
    assert [one.item for one in shop.pantry] == ["smoked paprika", "salt"]
    limes, _, _, buttermilk = shop.to_buy
    assert limes.on_list is not None and not limes.got and limes.amount == "2"  # once, the first
    assert buttermilk.alternatives and buttermilk.on_list is None
