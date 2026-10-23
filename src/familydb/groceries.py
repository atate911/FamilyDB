"""Ingredients and the grocery list (docs/RECIPES.md): what to buy read out of a recipe's line by
rule, and one or more recipes put on the family's list with their amounts as a note. No model is
asked: "2 cups chopped onion" is onion by parsing, not judgement.

`parse` keeps a line it cannot read whole as the item, which is still a thing one can buy, and is
held to real lines by `tests/test_groceries.py`, grown from what the family pastes.

For the shop itself (`shopping`, drawn by a recipe's Shopping page and the Lists page): each thing
under the section of the store it is found in, in the order a store is walked (`SECTIONS`,
`section_of`), what a kitchen has already apart (`pantry`: the staples, dried spices, vinegars,
the sauces in the door, and whatever the family keeps on a list named pantry), and for an
uncommon thing what could stand in (`alternatives`, a table; what the table does not know is
the family's to ask). All by word tables: no model call for a page.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any

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
        amount = f"{part.group('part').casefold()} {part.group('n')}"
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
    elif last.endswith("ves") and len(last) > 4:
        last = last[:-3] + "f"
    elif last.endswith("ies") and len(last) > 4:
        last = last[:-3] + "y"
    elif last.endswith("s") and not last.endswith("ss") and len(last) > 3:
        last = last[:-1]
    return " ".join([*words[:-1], last])


# Staples that are also something to buy: "pepper" with a spoon or a pinch is black pepper, but
# "2 peppers" or "1 pepper, diced" is a bell pepper.
SEASONING = frozenset({"pepper"})
SPOONS = re.compile(r"\b(?:tsp|tbsp|tbs|tb|teaspoons?|tablespoons?|pinch(?:es)?|dash(?:es)?)\b")


def staple(item: str, amount: str | None = None) -> bool:
    """Whether a household has it already: salt, oil, flour and the like, as written (never
    "peppers" for "pepper"); a lone pepper only as a seasoning."""
    folded = lists.fold(item)
    if folded not in STAPLES:
        return False
    return not (folded in SEASONING and amount and not SPOONS.search(amount.casefold()))


# -- The shop (docs/RECIPES.md): sections in the order a store is walked ---------------------------
SECTIONS = (
    "Produce",
    "Bakery",
    "Meat & fish",
    "Dairy & eggs",
    "Dry goods & cans",
    "Frozen",
    "Drinks",
    "Other",
)
OTHER = SECTIONS[-1]
# A whole item (folded, one form by `key`) that its last word would misplace: coconut milk is an
# aisle, sour cream the dairy case.
SECTION_PHRASES: dict[str, str] = {
    "coconut milk": "Dry goods & cans",
    "almond milk": "Dry goods & cans",
    "oat milk": "Dry goods & cans",
    "evaporated milk": "Dry goods & cans",
    "condensed milk": "Dry goods & cans",
    "coconut cream": "Dry goods & cans",
    "cream of tartar": "Dry goods & cans",
    "peanut butter": "Dry goods & cans",
    "almond butter": "Dry goods & cans",
    "tomato paste": "Dry goods & cans",
    "tomato sauce": "Dry goods & cans",
    "tomato puree": "Dry goods & cans",
    "passata": "Dry goods & cans",
    "sun-dried tomato": "Dry goods & cans",
    "sundried tomato": "Dry goods & cans",
    "dried cranberry": "Dry goods & cans",
    "dried apricot": "Dry goods & cans",
    "dried cherry": "Dry goods & cans",
    "dried fig": "Dry goods & cans",
    "sea salt": "Dry goods & cans",
    "bell pepper": "Produce",
    "red pepper": "Produce",
    "green pepper": "Produce",
    "yellow pepper": "Produce",
    "sweet potato": "Produce",
    "green onion": "Produce",
    "spring onion": "Produce",
    "red onion": "Produce",
    "green bean": "Produce",
    "snap pea": "Produce",
    "snow pea": "Produce",
    "fresh pea": "Produce",
    "cherry tomato": "Produce",
    "plum tomato": "Produce",
    "roma tomato": "Produce",
    "fresh basil": "Produce",
    "fresh thyme": "Produce",
    "fresh rosemary": "Produce",
    "fresh oregano": "Produce",
    "fresh dill": "Produce",
    "fresh mint": "Produce",
    "fresh parsley": "Produce",
    "fresh cilantro": "Produce",
    "fresh ginger": "Produce",
    "cream cheese": "Dairy & eggs",
    "sour cream": "Dairy & eggs",
    "heavy cream": "Dairy & eggs",
    "whipping cream": "Dairy & eggs",
    "double cream": "Dairy & eggs",
    "single cream": "Dairy & eggs",
    "half and half": "Dairy & eggs",
    "half-and-half": "Dairy & eggs",
    "ice cream": "Frozen",
    "frozen pea": "Frozen",
    "frozen corn": "Frozen",
    "frozen spinach": "Frozen",
    "puff pastry": "Frozen",
    "filo pastry": "Frozen",
    "phyllo pastry": "Frozen",
    "pizza dough": "Bakery",
    "fish sauce": "Dry goods & cans",
    "oyster sauce": "Dry goods & cans",
    "hoisin sauce": "Dry goods & cans",
    "hot sauce": "Dry goods & cans",
    "chicken stock": "Dry goods & cans",
    "chicken broth": "Dry goods & cans",
    "beef stock": "Dry goods & cans",
    "beef broth": "Dry goods & cans",
    "vegetable stock": "Dry goods & cans",
    "vegetable broth": "Dry goods & cans",
    "sparkling water": "Drinks",
    "coconut water": "Drinks",
    "orange juice": "Drinks",
    "apple juice": "Drinks",
    "lime juice": "Produce",
    "lemon juice": "Produce",
    "pepper flake": "Dry goods & cans",
    "tofu": "Produce",
    "tempeh": "Produce",
}
# The last word of an item, one form (`key`), to its section; a word anywhere in it when the last
# says nothing ("chicken thighs" is the meat case by chicken).
SECTION_WORDS: dict[str, str] = {}
for _section, _words in (
    (
        "Produce",
        "onion garlic shallot leek scallion chive tomato tomatillo potato carrot celery cucumber "
        "avocado lettuce romaine arugula spinach kale chard cabbage broccoli cauliflower zucchini "
        "courgette squash pumpkin eggplant aubergine mushroom pepper chili chile jalapeno jalapeño "
        "serrano poblano habanero corn asparagus bean pea radish beet beetroot turnip parsnip "
        "fennel ginger lemongrass galangal lime lemon orange apple banana pear grape berry "
        "strawberry blueberry raspberry blackberry cherry peach plum apricot nectarine mango "
        "pineapple melon watermelon kiwi pomegranate fig date cilantro coriander parsley basil "
        "mint dill rosemary thyme sage tarragon herb sprout microgreen salad greens plantain yam "
        "okra artichoke bok choy pak choi daikon edamame",
    ),
    (
        "Bakery",
        "bread tortilla bun baguette pita naan roll loaf bagel croissant brioche ciabatta "
        "sourdough focaccia flatbread wrap crust dough breadstick muffin crumpet",
    ),
    (
        "Meat & fish",
        "chicken beef pork lamb turkey veal duck bacon sausage ham steak mince brisket chuck rib "
        "loin tenderloin thigh breast drumstick wing chop cutlet shrimp prawn salmon tuna cod "
        "halibut tilapia trout haddock fish clam mussel oyster scallop crab lobster squid "
        "calamari anchovy sardine pancetta prosciutto chorizo salami pepperoni kielbasa meatball "
        "ribs ground mackerel",
    ),
    (
        "Dairy & eggs",
        "milk butter cheese cheddar parmesan mozzarella feta ricotta mascarpone gouda gruyere "
        "gruyère brie pecorino provolone havarti jack manchego halloumi paneer yogurt yoghurt "
        "cream buttermilk egg kefir ghee margarine",
    ),
    (
        "Dry goods & cans",
        "rice pasta spaghetti penne linguine fettuccine macaroni noodle lasagna lasagne orzo "
        "couscous quinoa bulgur barley oat oatmeal cereal granola flour cornmeal polenta "
        "semolina sugar honey syrup molasses oil vinegar sauce stock broth bouillon paste can "
        "lentil chickpea beans tomatoes salsa mustard ketchup mayonnaise mayo relish pickle "
        "olive caper tahini miso gochujang harissa sriracha salt spice cumin paprika oregano "
        "turmeric cinnamon nutmeg clove cardamom cayenne curry powder flake seed sesame nut "
        "almond walnut pecan cashew pistachio peanut raisin cranberry coconut chocolate cocoa "
        "vanilla extract gelatin yeast soda cornstarch cornflour arrowroot breadcrumb panko "
        "cracker chip tortillas jam jelly marmalade tofu tempeh seaweed nori wrapper wine",
    ),
    ("Frozen", "frozen pastry popsicle"),
    ("Drinks", "juice soda cola beer lager ale cider coffee tea kombucha lemonade"),
):
    for _word in _words.split():
        SECTION_WORDS[_word] = _section
# Said anywhere in the item, these settle it before any other word.
SECTION_MARKERS: dict[str, str] = {
    "frozen": "Frozen",
    "canned": "Dry goods & cans",
    "tinned": "Dry goods & cans",
    "dried": "Dry goods & cans",
    "jarred": "Dry goods & cans",
}
# A dried herb is the pantry's; fresh, it is produce.
HERBS = frozenset(
    {
        "basil",
        "oregano",
        "thyme",
        "rosemary",
        "parsley",
        "dill",
        "mint",
        "sage",
        "tarragon",
        "cilantro",
        "coriander",
        "chive",
        "marjoram",
        "chervil",
    }
)
# Wine is in the aisles for cooking and a drink by the bottle: the amount decides.
BY_THE_BOTTLE = re.compile(r"\bbottles?\b")


def section_of(item: str, amount: str | None = None) -> str:
    """Which part of the store a thing is found in: by a word that settles it (frozen, canned,
    dried), the whole item, its last word, then any word; Other when none says."""
    folded = key(item)
    words = folded.split()
    if not words:
        return OTHER
    for word in words:
        if word in SECTION_MARKERS:
            return SECTION_MARKERS[word]
    for start in range(len(words)):  # the whole, then what it ends with: "red bell pepper"
        phrase = " ".join(words[start:])
        if phrase in SECTION_PHRASES:
            return SECTION_PHRASES[phrase]
    if words[-1] == "wine" and amount and BY_THE_BOTTLE.search(amount.casefold()):
        return "Drinks"
    if words[-1] in SECTION_WORDS:
        return SECTION_WORDS[words[-1]]
    for word in words:
        if word in SECTION_WORDS:
            return SECTION_WORDS[word]
    return OTHER


# What a kitchen has already, beyond the staples: dried herbs and spices, what is in the door of
# the fridge, the baking shelf. Matched on the whole item (one form), then its last word, so
# "smoked paprika" and "ground cumin" are the spice; "fresh oregano" is produce, never the
# pantry. A family's own are whatever they keep on a list named pantry (`family_pantry`).
PANTRY_PHRASES = frozenset(
    {
        "soy sauce",
        "fish sauce",
        "oyster sauce",
        "hoisin sauce",
        "worcestershire sauce",
        "hot sauce",
        "sriracha",
        "ketchup",
        "mustard",
        "dijon mustard",
        "mayonnaise",
        "mayo",
        "honey",
        "maple syrup",
        "brown sugar",
        "powdered sugar",
        "icing sugar",
        "confectioners sugar",
        "baking powder",
        "baking soda",
        "bicarbonate of soda",
        "cornstarch",
        "cornflour",
        "vanilla extract",
        "vanilla",
        "cocoa powder",
        "sesame oil",
        "toasted sesame oil",
        "red pepper flakes",
        "chili flakes",
        "chilli flakes",
        "chili powder",
        "chilli powder",
        "curry powder",
        "garlic powder",
        "onion powder",
        "bay leaf",
        "bay leaves",
        "italian seasoning",
        "garam masala",
        "five spice",
        "five-spice powder",
        "everything bagel seasoning",
        "stock cube",
        "bouillon cube",
        "bouillon",
        "peanut butter",
        "rice vinegar",
        "white vinegar",
        "cider vinegar",
        "apple cider vinegar",
        "balsamic vinegar",
        "red wine vinegar",
        "white wine vinegar",
        "sherry vinegar",
    }
)
PANTRY_WORDS = frozenset(
    {
        "vinegar",
        "cumin",
        "paprika",
        "oregano",
        "thyme",
        "rosemary",
        "turmeric",
        "cinnamon",
        "nutmeg",
        "cardamom",
        "cayenne",
        "coriander",
        "allspice",
        "cloves",
        "peppercorn",
        "peppercorns",
        "sumac",
        "zaatar",
        "za'atar",
        "saffron",
        "fenugreek",
        "anise",
        "star anise",
        "seasoning",
        "extract",
    }
)
FRESH = re.compile(r"^(?:fresh|whole|a bunch of)\b")


def family_pantry(conn: sqlite3.Connection) -> frozenset[str]:
    """What the family said they always have: the things on a list named pantry, as kept; empty
    with no such list, so the built-in table stands alone."""
    ref = lists.find(conn, "pantry")
    if ref is None:
        return frozenset()
    return frozenset(key(item.text) for item in lists.items(conn, ref))


def pantry(item: str, amount: str | None = None, *, have: frozenset[str] = frozenset()) -> bool:
    """Whether a kitchen has it already, so it is checked rather than bought: a staple, a dried
    spice or herb, a vinegar, a sauce from the fridge door, the baking shelf, or one of the
    family's own (`have`). Never something fresh."""
    if staple(item, amount):
        return True
    folded = key(item)
    if folded in have:
        return True
    if FRESH.match(folded):
        return False
    if folded in PANTRY_PHRASES:
        return True
    words = folded.split()
    if any(" ".join(words[start:]) in PANTRY_PHRASES for start in range(1, len(words))):
        return True
    if words and words[-1] in PANTRY_WORDS:
        return True
    if len(words) < 2:
        return False
    # A dried herb, a ground spice: the word before says so; ground beef is the meat case.
    if words[0] == "dried":
        return words[-1] in HERBS
    return words[0] == "ground" and SECTION_WORDS.get(words[-1]) in ("Produce", "Dry goods & cans")


# What could stand in for an uncommon thing, by the item (one form, `key`): each a short phrase
# the page shows on a tap. What is not here, the family asks her about.
SUBSTITUTES: dict[str, tuple[str, ...]] = {
    "buttermilk": (
        "milk with a spoon of lemon juice or vinegar, left 5 minutes",
        "plain yogurt thinned with milk",
    ),
    "creme fraiche": ("sour cream", "Greek yogurt"),
    "crème fraîche": ("sour cream", "Greek yogurt"),
    "sour cream": ("Greek yogurt", "crème fraîche"),
    "greek yogurt": ("plain yogurt, strained", "sour cream"),
    "heavy cream": ("whipping cream", "evaporated milk, for cooking", "coconut cream"),
    "half and half": ("equal milk and cream", "whole milk"),
    "mascarpone": ("cream cheese beaten with a little cream", "ricotta"),
    "ricotta": ("cottage cheese, blended", "mascarpone"),
    "parmesan": ("pecorino", "grana padano"),
    "pecorino": ("parmesan",),
    "gruyere": ("emmental", "comté", "a sharp cheddar"),
    "gruyère": ("emmental", "comté", "a sharp cheddar"),
    "feta": ("goat cheese", "ricotta salata"),
    "paneer": ("halloumi", "firm tofu"),
    "halloumi": ("paneer", "feta, grilled"),
    "shallot": ("a small red onion", "the white of a green onion"),
    "leek": ("green onions", "a mild onion"),
    "scallion": ("chives", "a small onion"),
    "green onion": ("chives", "a small onion"),
    "chive": ("the green of a green onion",),
    "lemongrass": ("lemon zest", "a squeeze of lime"),
    "galangal": ("ginger",),
    "fresh ginger": ("ground ginger, a quarter as much",),
    "cilantro": ("flat-leaf parsley", "leave it out"),
    "fresh coriander": ("flat-leaf parsley", "leave it out"),
    "fresh basil": ("dried basil, a third as much", "spinach, for pesto"),
    "fresh thyme": ("dried thyme, a third as much",),
    "fresh rosemary": ("dried rosemary, a third as much",),
    "fresh oregano": ("dried oregano, a third as much",),
    "fresh dill": ("dried dill, a third as much", "fennel fronds"),
    "fresh mint": ("dried mint, a third as much",),
    "fresh parsley": ("dried parsley, a third as much", "cilantro"),
    "tarragon": ("fennel fronds", "a pinch of anise seed"),
    "gochujang": ("sriracha with a spoon of miso", "chili paste with a little sugar"),
    "miso": ("soy sauce, for salt", "tahini with a little soy sauce"),
    "fish sauce": ("soy sauce with a squeeze of lime", "Worcestershire sauce"),
    "oyster sauce": ("hoisin sauce", "soy sauce with a little sugar"),
    "hoisin sauce": ("oyster sauce with a little honey", "barbecue sauce"),
    "mirin": ("rice vinegar with a little sugar", "dry sherry"),
    "rice vinegar": ("white wine vinegar", "cider vinegar"),
    "sherry vinegar": ("red wine vinegar", "cider vinegar"),
    "sherry": ("dry white wine", "vermouth"),
    "white wine": ("stock with a splash of vinegar", "vermouth"),
    "red wine": ("stock with a splash of balsamic", "cranberry juice, for a braise"),
    "tahini": ("peanut butter, thinned", "sunflower seed butter"),
    "harissa": ("sriracha with ground cumin", "tomato paste with cayenne"),
    "chipotle in adobo": ("smoked paprika with a little cayenne", "chipotle powder"),
    "chipotle pepper": ("smoked paprika with a little cayenne", "chipotle powder"),
    "panko": ("breadcrumbs", "crushed crackers"),
    "breadcrumb": ("panko", "crushed crackers", "oats, blitzed"),
    "cornstarch": ("flour, twice as much", "arrowroot"),
    "arrowroot": ("cornstarch",),
    "pancetta": ("bacon",),
    "prosciutto": ("serrano ham", "bacon, cooked crisp"),
    "chorizo": ("spicy sausage", "bacon with smoked paprika"),
    "tomato paste": ("ketchup, half as much", "tomato sauce, reduced"),
    "coconut milk": ("cream with a little coconut extract", "evaporated milk"),
    "coconut cream": ("the thick top of a can of coconut milk",),
    "molasses": ("dark brown sugar", "honey"),
    "maple syrup": ("honey", "brown sugar"),
    "honey": ("maple syrup", "sugar"),
    "capers": ("chopped green olives",),
    "caper": ("chopped green olives",),
    "anchovy": ("a spoon of fish sauce", "Worcestershire sauce"),
    "fennel": ("celery", "a mild onion"),
    "bok choy": ("napa cabbage", "spinach, stirred in last"),
    "napa cabbage": ("green cabbage", "bok choy"),
    "kale": ("chard", "spinach"),
    "chard": ("kale", "spinach"),
    "polenta": ("cornmeal", "grits"),
    "quinoa": ("couscous", "bulgur", "rice"),
    "couscous": ("quinoa", "orzo"),
    "orzo": ("small pasta", "rice"),
    "farro": ("barley", "brown rice"),
    "bulgur": ("couscous", "quinoa"),
    "ghee": ("butter", "clarified butter"),
    "sesame oil": ("a neutral oil with toasted sesame seeds",),
    "lime": ("lemon",),
    "lemon": ("lime",),
    "tofu": ("paneer", "chickpeas"),
    "tempeh": ("firm tofu",),
    "edamame": ("peas", "broad beans"),
    "sumac": ("lemon zest", "a squeeze of lemon"),
    "zaatar": ("thyme, sesame seeds and sumac", "oregano with sesame seeds"),
    "garam masala": ("curry powder", "cumin, coriander and cinnamon"),
    "five spice": ("cinnamon with a pinch of clove and anise",),
    "saffron": ("turmeric, for colour",),
    "cardamom": ("cinnamon with a little nutmeg",),
    "star anise": ("anise seed", "fennel seed"),
}


SECTION_PHRASES = {key(phrase): section for phrase, section in SECTION_PHRASES.items()}
PANTRY_PHRASES = frozenset(key(phrase) for phrase in PANTRY_PHRASES)
SUBSTITUTES = {key(item): stand_ins for item, stand_ins in SUBSTITUTES.items()}


def alternatives(item: str) -> tuple[str, ...]:
    """What could stand in for it, from the table; nothing for a thing it does not know."""
    folded = key(item)
    if folded in SUBSTITUTES:
        return SUBSTITUTES[folded]
    words = folded.split()
    for start in range(1, len(words)):
        rest = " ".join(words[start:])
        if rest in SUBSTITUTES:
            return SUBSTITUTES[rest]
    return ()


@dataclass
class Buy:
    """One thing a recipe wants, as the shop sees it: what, how much this recipe asks, its line,
    what could stand in, and where it stands on the family's list (`lists.Item`, or None)."""

    item: str
    amount: str | None
    text: str
    alternatives: tuple[str, ...] = ()
    on_list: Any = None

    @property
    def got(self) -> bool:
        return self.on_list is not None and self.on_list.ticked_at is not None


@dataclass
class Shopping:
    """A recipe's shopping, in store order: each section with what is found there, and what the
    pantry has apart."""

    sections: list[tuple[str, list[Buy]]] = field(default_factory=list)
    pantry: list[Buy] = field(default_factory=list)

    @property
    def to_buy(self) -> list[Buy]:
        return [one for _, found in self.sections for one in found]


def shopping(
    recipe: Recipe, on_list: dict[str, Any], *, have: frozenset[str] = frozenset()
) -> Shopping:
    """The recipe's things by section, each laid over the family's list (`on_list`: by `key`,
    the list's items), the pantry's apart."""
    found: dict[str, list[Buy]] = {section: [] for section in SECTIONS}
    kept = Shopping()
    seen: set[str] = set()
    for ingredient in recipe.ingredients:
        item = ingredient.item or parse(ingredient.text).item
        if not item or key(item) in seen:
            continue
        seen.add(key(item))
        one = Buy(
            item=item,
            amount=ingredient.amount,
            text=ingredient.text,
            alternatives=alternatives(item),
            on_list=on_list.get(key(item)),
        )
        if pantry(item, ingredient.amount, have=have):
            kept.pantry.append(one)
        else:
            found[section_of(item, ingredient.amount)].append(one)
    kept.sections = [(section, found[section]) for section in SECTIONS if found[section]]
    return kept


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


def wanted(
    chosen: list[tuple[Idea, Recipe]], *, have: frozenset[str] = frozenset()
) -> tuple[list[Wanted], list[str]]:
    """What the recipes need, one line an item however many ask for it, in the order first asked,
    and what the pantry has left out (`have` is the family's own pantry, `family_pantry`)."""
    by_key: dict[str, Wanted] = {}
    staples: list[str] = []
    for idea, recipe in chosen:
        name = short_name(idea)
        for ingredient in recipe.ingredients:
            item = ingredient.item or parse(ingredient.text).item
            if not item:
                continue
            if pantry(item, ingredient.amount, have=have):
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
    amounts; a ticked one is wanted again, as `lists.add` does; what the pantry has is left off
    and said. Call inside a transaction."""
    needed, staples = wanted(chosen, have=family_pantry(conn))
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
