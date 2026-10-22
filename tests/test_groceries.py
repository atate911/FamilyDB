"""What to buy in a recipe's line (familydb/groceries.py), by rule. A line the family pastes that
reads wrong is added here with what it should read as."""

from __future__ import annotations

import pytest

from familydb import groceries

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
    ("Juice of 1 lime", "lime", "1, juice of"),
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
