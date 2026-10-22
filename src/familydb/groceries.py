"""Ingredients and the grocery list (docs/RECIPES.md): what to buy read out of a recipe's line by
rule, and one or more recipes put on the family's list with their amounts as a note. No model is
asked: "2 cups chopped onion" is onion by parsing, not judgement.

`parse` keeps a line it cannot read whole as the item, which is still a thing one can buy, and is
held to real lines by `tests/test_groceries.py`, grown from what the family pastes.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from familydb.store import lists
from familydb.store.ideas import Idea
from familydb.store.recipes import Ingredient, Recipe

FRACTIONS = {
    "¼": "1/4",
    "½": "1/2",
    "¾": "3/4",
    "⅓": "1/3",
    "⅔": "2/3",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
    "⅕": "1/5",
    "⅙": "1/6",
}
# Units an amount may carry, longest first so "tablespoons" is not read as "t".
UNITS = sorted(
    {
        "cups",
        "cup",
        "c",
        "tablespoons",
        "tablespoon",
        "tbsp",
        "tbs",
        "tb",
        "teaspoons",
        "teaspoon",
        "tsp",
        "ounces",
        "ounce",
        "oz",
        "fl oz",
        "pounds",
        "pound",
        "lbs",
        "lb",
        "grams",
        "gram",
        "g",
        "kilograms",
        "kilogram",
        "kg",
        "milliliters",
        "millilitres",
        "ml",
        "liters",
        "litres",
        "l",
        "quarts",
        "quart",
        "qt",
        "pints",
        "pint",
        "pt",
        "cans",
        "can",
        "jars",
        "jar",
        "packages",
        "package",
        "pkg",
        "packets",
        "packet",
        "boxes",
        "box",
        "bags",
        "bag",
        "bottles",
        "bottle",
        "bunches",
        "bunch",
        "heads",
        "head",
        "cloves",
        "clove",
        "sprigs",
        "sprig",
        "stalks",
        "stalk",
        "sticks",
        "stick",
        "slices",
        "slice",
        "pieces",
        "piece",
        "pinches",
        "pinch",
        "dashes",
        "dash",
        "handfuls",
        "handful",
        "fillets",
        "fillet",
        "loaves",
        "loaf",
        "sheets",
        "sheet",
        "inch",
        "inches",
    },
    key=len,
    reverse=True,
)
SIZES = ("extra large", "extra-large", "large", "medium", "small", "big", "heaping", "scant")
NUMBER = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"
AMOUNT = re.compile(
    rf"^(?P<n>{NUMBER}(?:\s*(?:-|\u2013|to|or)\s*{NUMBER})?|an?\b|one\b)\s*"
    r"(?P<paren>\([^)]*\)\s*)?"
    rf"(?P<size>(?:{'|'.join(re.escape(s) for s in SIZES)})\s+)?"
    rf"(?P<unit>(?:{'|'.join(re.escape(u) for u in UNITS)})\.?(?=\s|$))?\s*(?:of\s+)?",
    re.IGNORECASE,
)
# Words that say how it is cut or cooked, never what it is: taken off the front of an item.
PREPARED = frozenset(
    {
        "chopped",
        "diced",
        "minced",
        "sliced",
        "finely",
        "roughly",
        "coarsely",
        "thinly",
        "freshly",
        "grated",
        "shredded",
        "peeled",
        "crushed",
        "softened",
        "melted",
        "beaten",
        "halved",
        "quartered",
        "cubed",
        "trimmed",
        "rinsed",
        "drained",
        "packed",
        "lightly",
        "about",
        "approximately",
    }
)
TRAILING = re.compile(
    r"\b(?:to taste|as needed|optional|for serving|for garnish|to serve|to garnish|divided|"
    r"plus more.*|or more.*|if desired|at room temperature)\b.*$",
    re.IGNORECASE,
)
# What a household always has: left off a list built from recipes, and said as left off, so the
# family can add one they are out of.
STAPLES = frozenset(
    {
        "salt",
        "kosher salt",
        "sea salt",
        "table salt",
        "pepper",
        "black pepper",
        "ground black pepper",
        "salt and pepper",
        "salt and black pepper",
        "kosher salt and black pepper",
        "kosher salt and freshly ground black pepper",
        "water",
        "cold water",
        "warm water",
        "hot water",
        "boiling water",
        "ice",
        "oil",
        "olive oil",
        "extra virgin olive oil",
        "extra-virgin olive oil",
        "vegetable oil",
        "canola oil",
        "neutral oil",
        "cooking spray",
        "nonstick cooking spray",
        "sugar",
        "granulated sugar",
        "flour",
        "all-purpose flour",
        "all purpose flour",
    }
)
MOST_NOTE = 200
# "Juice of 1 lime" is a lime: the part of it the recipe uses goes with the amount.
PART_OF = re.compile(
    r"^(?P<part>(?:the\s+)?(?:juice and zest|zest and juice|juice|zest)\s+of)\s+"
    rf"(?P<n>{NUMBER}|a|an|one|half(?:\s+a)?)\s+(?P<rest>.+)$",
    re.IGNORECASE,
)


def _plain(line: str) -> str:
    text = line.strip()
    for glyph, written in FRACTIONS.items():
        text = re.sub(rf"(\d){glyph}", rf"\1 {written}", text)
        text = text.replace(glyph, written)
    text = text.replace("\u2044", "/")
    text = re.sub("^[-\u2022*\u25aa\u25cf\u2013]+\\s*", "", text)
    return " ".join(text.split())


def parse(line: str) -> Ingredient:
    """What to buy in a recipe's line, and how much: "2 cups chopped onion" is onion, 2 cups."""
    text = _plain(line)
    amount = None
    rest = text
    part = PART_OF.match(text)
    if part:
        amount = f"{part.group('n')}, {part.group('part').casefold()}"
        text = part.group("rest")
        rest = text
    found = AMOUNT.match(text) if part is None else None
    if found and found.group("n"):
        amount = " ".join(found.group(0).split()).removesuffix(" of").strip() or None
        rest = text[found.end() :]
    rest = re.sub(r"\([^)]*\)", " ", rest)
    rest = rest.split(",")[0].split(";")[0]
    rest = TRAILING.sub("", rest)
    words = [word for word in re.split(r"\s+", rest.strip()) if word]
    while words and words[0].casefold().strip(".") in PREPARED:
        words.pop(0)
    while words and words[-1].casefold() in {"and", "or", "plus", "for", "to"}:
        words.pop()
    item = lists.fold(" ".join(words)).strip(" -")
    if not item:
        item = lists.fold(text)
    return Ingredient(text=line.strip(), item=item, amount=amount)


def key(item: str) -> str:
    """One form for an item however many there are: onions and onion, tomatoes and tomato."""
    words = lists.fold(item).split()
    if not words:
        return ""
    last = words[-1]
    if last.endswith("oes") and len(last) > 4:
        last = last[:-2]
    elif last.endswith("ies") and len(last) > 4:
        last = last[:-3] + "y"
    elif last.endswith("s") and not last.endswith("ss") and len(last) > 3:
        last = last[:-1]
    return " ".join([*words[:-1], last])


def staple(item: str) -> bool:
    folded = lists.fold(item)
    return folded in STAPLES or key(folded) in STAPLES


@dataclass
class Wanted:
    """One thing to buy across the recipes asked for, and how much each wants."""

    item: str
    amounts: list[str] = field(default_factory=list)

    def note(self) -> str:
        return ", ".join(self.amounts)[:MOST_NOTE]


@dataclass
class Shopped:
    """What putting recipes on a list did, for the reply and the page's notice."""

    added: list[str] = field(default_factory=list)
    there: list[str] = field(default_factory=list)
    left_out: list[str] = field(default_factory=list)
    recipes: list[str] = field(default_factory=list)


def short_name(idea: Idea) -> str:
    """A recipe as its amounts' note names it: the title's first few words."""
    words = idea.title.split()
    return " ".join(words[:3]) + ("…" if len(words) > 3 else "")


def wanted(chosen: list[tuple[Idea, Recipe]]) -> tuple[list[Wanted], list[str]]:
    """What the recipes need, one line an item however many ask for it, in the order first asked,
    and the staples left out."""
    by_key: dict[str, Wanted] = {}
    staples: list[str] = []
    for idea, recipe in chosen:
        name = short_name(idea)
        for ingredient in recipe.ingredients:
            item = ingredient.item or parse(ingredient.text).item
            if not item:
                continue
            if staple(item):
                if item not in staples:
                    staples.append(item)
                continue
            one = by_key.setdefault(key(item), Wanted(item))
            said = f"{ingredient.amount} ({name})" if ingredient.amount else f"({name})"
            if said not in one.amounts:
                one.amounts.append(said)
    return list(by_key.values()), staples


def put_on(
    conn: sqlite3.Connection,
    list_ref: int,
    chosen: list[tuple[Idea, Recipe]],
    *,
    by: int | None,
    now: str,
) -> Shopped:
    """Put what the recipes need on a list. A thing there already keeps its place and gains the
    amounts; a ticked one is wanted again, as `lists.add` does. Call inside a transaction."""
    needed, staples = wanted(chosen)
    shopped = Shopped(left_out=staples, recipes=[idea.title for idea, _ in chosen])
    on_list = {key(item.text): item for item in lists.items(conn, list_ref)}
    for one in needed:
        there = on_list.get(key(one.item))
        if there is not None and there.ticked_at is None:
            lists.set_note(conn, there.id, _joined(there.note, one.note()))
            shopped.there.append(there.text)
            continue
        added = lists.add(conn, list_ref, there.text if there else one.item, by=by, now=now)
        if added is None:  # written another way that folds the same: it is there
            shopped.there.append(one.item)
            continue
        lists.set_note(conn, added.id, one.note())
        shopped.added.append(added.text)
    return shopped


def _joined(before: str | None, more: str) -> str:
    if not before:
        return more
    if more in before:
        return before
    return f"{before}, {more}"[:MOST_NOTE]
