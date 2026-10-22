"""Reading a pasted recipe link by code (integrations/recipe_page.py): the shapes recipe sites
carry, read from saved pages with no network."""

from __future__ import annotations

from pathlib import Path

import pytest

from familydb.integrations import recipe_page as page

PAGES = Path(__file__).parent / "pages"


def _read(name: str) -> page.ReadRecipe | None:
    return page.recipe_in((PAGES / name).read_text())


def test_a_recipe_in_a_graph_with_sections_and_two_types():
    found = _read("recipe_graph.html")
    assert found is not None
    assert found.name == "Sheet-Pan Chicken Fajitas"
    assert found.serves == 4 and found.active_minutes == 15 and found.total_minutes == 35
    assert found.ingredients[0] == "1 1/2 pounds boneless skinless chicken thighs"
    assert found.steps == [
        "Heat the oven to 425°F.",
        "Roast 20 minutes, then squeeze over the lime.",
    ]
    assert found.tags == ["mexican", "weeknight", "sheet pan"]


def test_a_broken_block_beside_a_good_one_and_steps_as_one_string():
    found = _read("recipe_top.html")
    assert found is not None and found.name == "Weeknight Dal"
    assert found.steps == ["Rinse the lentils.", "Simmer for 30 minutes."]
    assert found.serves == 6 and found.total_minutes == 40


def test_a_recipe_in_a_list_of_blocks():
    found = _read("recipe_list.html")
    assert found is not None and found.steps == ["Stir together.", "Refrigerate overnight."]


def test_a_page_with_no_recipe_block_is_none():
    assert _read("no_recipe.html") is None
    assert page.recipe_in("<html>not even json</html>") is None


@pytest.mark.parametrize(
    ("written", "minutes"),
    [("PT1H30M", 90), ("PT45M", 45), ("P0DT2H", 120), ("PT0M", None), ("P3D", None), ("1h", None)],
)
def test_durations(written, minutes):
    assert page.minutes(written) == minutes


@pytest.mark.parametrize(
    "url",
    ["file:///etc/passwd", "ftp://example.com/x", "http://127.0.0.1/recipe", "http://localhost/"],
)
def test_an_address_this_server_should_not_read_is_refused(url):
    with pytest.raises(page.PageError):
        page.check_address(url)


def test_a_character_set_nobody_knows_is_read_as_utf8():
    assert page.decoded("Crème".encode(), "utf8mb4") == "Crème"
