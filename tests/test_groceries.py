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
        # A spice ground is the shelf's; nuts and seeds ground are bought by the cup.
        ("ground ginger", "1 tsp", True),
        ("ground cloves", "1/2 tsp", True),
        ("ground fennel seed", "1 tsp", True),
        ("ground almonds", "200 g", False),
        ("ground hazelnuts", "1 cup", False),
        ("ground flaxseed", "2 tbsp", False),
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
    # Once, both lines' amounts added: two for the dish and two for serving is four to buy.
    assert limes.on_list is not None and not limes.got and limes.amount == "4"
    assert buttermilk.alternatives and buttermilk.on_list is None


@pytest.mark.parametrize(
    ("amounts", "in_all"),
    [
        (["1 cup", "1 cup"], "2 cups"),
        (["1/2 cup", "1/2 cup"], "1 cup"),
        (["1 1/2 cups", "1/2 cup"], "2 cups"),
        (["\u00bd tsp", "\u00bd tsp"], "1 tsp"),
        (["1.5 cups", "1 cup"], "2.5 cups"),
        (["200 g", "100 g"], "300 g"),
        (["1 clove", "2 cloves"], "3 cloves"),
        (["1 (14-oz) can", "1 (14-oz) can"], "2 (14-oz) cans"),
        (["2", "2"], "4"),
        (["1 large", "1 large"], "2 large"),
        # What does not add up by rule is said one after another, so nothing is lost.
        (["1 cup", "2 tbsp"], "1 cup + 2 tbsp"),
        (["2-3", "1"], "2-3 + 1"),
        ([None, "1 cup"], "1 cup"),
        ([None, None], None),
    ],
)
def test_two_lines_of_one_thing_add_up(amounts, in_all):
    assert groceries.added_up(amounts) == in_all


def test_a_clove_is_a_clove_however_many():
    assert groceries.key("cloves") == groceries.key("clove") == "clove"
    assert groceries.key("olives") == "olive" and groceries.key("bay leaves") == "bay leaf"


def test_a_recipe_asking_twice_for_onion_puts_both_on_the_list_once(settings, clock, conn, family):
    """One cup for the filling and one for the topping is two cups; asking again adds nothing."""
    from familydb.store import ideas, lists
    from familydb.store.recipes import Ingredient

    with db.transaction(conn):
        pie = ideas.insert(conn, title="Shepherd's pie", kind="recipe", now=NOW_ISO)
        soup = ideas.insert(conn, title="Onion soup", kind="recipe", now=NOW_ISO)
    chosen = [
        (
            pie,
            Recipe(
                idea_id=pie.id,
                ingredients=[
                    Ingredient(text="1 cup onion, for the filling", item="onion", amount="1 cup"),
                    Ingredient(text="1 cup onion, for the top", item="onion", amount="1 cup"),
                ],
            ),
        ),
        (
            soup,
            Recipe(
                idea_id=soup.id,
                ingredients=[Ingredient(text="4 onions", item="onions", amount="4")],
            ),
        ),
    ]
    with db.transaction(conn):
        ref = lists.list_id(conn, "shopping", NOW_ISO)
        groceries.put_on(conn, ref, chosen, by=None, now=NOW_ISO)
    (onion,) = lists.items(conn, ref)
    assert onion.note == "2 cups (Shepherd's pie), 4 (Onion soup)"
    with db.transaction(conn):
        again = groceries.put_on(conn, ref, chosen, by=None, now=NOW_ISO)
    assert again.added == [] and lists.items(conn, ref)[0].note == onion.note


def test_two_recipes_whose_names_begin_alike_stay_apart():
    from familydb.store.ideas import Idea

    def idea(number, title):
        return Idea(id=number, kind="recipe", title=title, created_at=NOW_ISO, updated_at=NOW_ISO)

    soup = Recipe(idea_id=2, ingredients=[groceries.parse("2 cups onion")])
    alike = [idea(3, "Chicken tikka masala"), idea(4, "Chicken tikka masala skewers")]
    needed, _ = groceries.wanted([(one, soup) for one in alike])
    assert needed[0].note() == "2 cups (Chicken tikka masala), 2 cups (Chicken tikka masala…)"


@pytest.mark.parametrize(
    ("one", "other", "same"),
    [
        ("flour tortillas", "tortillas", True),
        ("Tortillas", "corn tortillas", True),
        ("boneless skinless chicken thighs", "chicken thighs", True),
        ("red bell peppers", "bell pepper", True),
        ("large eggs", "eggs", True),
        ("yellow onion", "onions", True),
        # Words that make it another thing keep it a line of its own.
        ("flour tortillas", "corn tortillas", False),
        ("sour cream", "cream", False),
        ("peanut butter", "butter", False),
        ("green onions", "onion", False),
        ("sweet potatoes", "potatoes", False),
        ("coconut milk", "milk", False),
        ("corn syrup", "syrup", False),
        ("red bell peppers", "peppers", False),  # a pepper may be the pepper mill's
    ],
)
def test_a_kind_of_a_thing_is_that_thing_and_another_thing_is_not(one, other, same):
    assert groceries.same_thing(one, other) is same
    assert groceries.same_thing(other, one) is same


def test_tortillas_on_the_list_are_what_flour_tortillas_want(settings, clock, conn, family):
    """The Fajitas' "8 small flour tortillas" went on as a second line under the tortillas
    already there; now they go on that line, and its note says which kind."""
    from familydb.store import ideas, lists
    from familydb.store.recipes import Ingredient

    with db.transaction(conn):
        fajitas = ideas.insert(conn, title="Fajitas", kind="recipe", now=NOW_ISO)
        tacos = ideas.insert(conn, title="Fish tacos", kind="recipe", now=NOW_ISO)
        ref = lists.list_id(conn, "shopping", NOW_ISO)
        lists.add(conn, ref, "tortillas", by=None, now=NOW_ISO)
        lists.add(conn, ref, "cream", by=None, now=NOW_ISO)

    def recipe(idea, *lines: str) -> tuple:
        read = [groceries.parse(line) for line in lines]
        return idea, Recipe(
            idea_id=idea.id, ingredients=[Ingredient(**one.model_dump()) for one in read]
        )

    chosen = [
        recipe(fajitas, "8 small flour tortillas", "1 cup sour cream"),
        recipe(tacos, "12 corn tortillas", "4 tortillas"),
    ]
    with db.transaction(conn):
        shopped = groceries.put_on(conn, ref, chosen, by=None, now=NOW_ISO)
    assert shopped.there == ["tortillas"] and shopped.added == ["sour cream"]
    held = {item.text: item.note for item in lists.items(conn, ref)}
    assert sorted(held) == ["cream", "sour cream", "tortillas"]
    assert held["tortillas"] == (
        "8 small flour tortillas (Fajitas), 4 (Fish tacos), 12 corn tortillas (Fish tacos)"
    )
    # Asked again, nothing more is added and the note is not said twice.
    with db.transaction(conn):
        again = groceries.put_on(conn, ref, chosen, by=None, now=NOW_ISO)
    after = {item.text: item.note for item in lists.items(conn, ref)}
    assert again.added == [] and again.there == ["tortillas", "sour cream"] and after == held
    # The recipe's Shopping page sees them on the list too.
    on_list = {groceries.key(item.text): item for item in lists.items(conn, ref)}
    shop = groceries.shopping(chosen[0][1], on_list)
    assert [(one.item, one.on_list is not None) for one in shop.to_buy] == [
        ("flour tortillas", True),
        ("sour cream", True),
    ]


def test_flour_tortillas_on_the_list_cover_a_recipe_that_wants_tortillas(
    settings, clock, conn, family
):
    from familydb.store import ideas, lists
    from familydb.store.recipes import Ingredient

    with db.transaction(conn):
        tacos = ideas.insert(conn, title="Tacos", kind="recipe", now=NOW_ISO)
        ref = lists.list_id(conn, "shopping", NOW_ISO)
        lists.add(conn, ref, "flour tortillas", by=None, now=NOW_ISO)
    chosen = [
        (
            tacos,
            Recipe(
                idea_id=tacos.id,
                ingredients=[Ingredient(text="8 tortillas", item="tortillas", amount="8")],
            ),
        )
    ]
    with db.transaction(conn):
        shopped = groceries.put_on(conn, ref, chosen, by=None, now=NOW_ISO)
    assert shopped.there == ["flour tortillas"] and shopped.added == []
    (only,) = lists.items(conn, ref)
    assert only.note == "8 (Tacos)"
