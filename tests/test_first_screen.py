"""What each page is for is on the first screen of a phone (docs/STYLE.md, "The test").

Measured on a 390 by 844 phone, a recipe's Shopping list was a screen and a half down and today was
under the to-dos. This holds the answer in a real browser, on the example household
(examples/household.py, Friday 16 October 2026, 5:02 pm, signed in as Sam): each page's first
useful thing starts above the row of places at the foot, and nothing scrolls sideways at 390 or
320 pixels.

Opt-in, as it needs a browser and takes some seconds:

    FAMILYDB_BROWSER=1 uv run --with playwright pytest -m browser -n 0

FAMILYDB_CHROMIUM names a Chromium to launch when Playwright's own is not installed. Nothing here
leaves the machine: the household is served on 127.0.0.1 and asks no model.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from typing import Any

import pytest

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
NARROWEST = {"width": 320, "height": 640}
SAM = ("Sam", "sam keeps the family list")

# Each page, what somebody comes to it for, and where that is drawn (the first match counts).
FIRST = [
    ("/", "what waits on you", "main .q, main .todo"),
    ("/eat", "tonight's pick", "main .r--top"),
    ("/do", "the first idea", "main .r"),
    ("/week", "today", "main .wk__day--today"),
    ("/lists", "the first thing to get", "main .list-items--big li"),
]


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Any, str]]:
    if os.environ.get("FAMILYDB_BROWSER") != "1":
        pytest.skip(
            "needs a browser: FAMILYDB_BROWSER=1 uv run --with playwright pytest -m browser"
        )
    sync = pytest.importorskip("playwright.sync_api")
    from examples import household
    from waitress import create_server

    from familydb.web import create_app

    app, _ = household.build(tmp_path_factory.mktemp("household"))
    server = create_server(create_app(app), host="127.0.0.1", port=0, threads=4)
    threading.Thread(target=server.run, daemon=True).start()
    try:
        with sync.sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.environ.get("FAMILYDB_CHROMIUM") or None
            )
            try:
                yield browser, f"http://127.0.0.1:{server.effective_port}"
            finally:
                browser.close()
    finally:
        server.close()


def _signed_in(site: tuple[Any, str], viewport: dict[str, int]) -> Any:
    browser, base = site
    page = browser.new_context(viewport=viewport).new_page()
    page.goto(base + "/login")
    page.fill("#name", SAM[0])
    page.fill("#password", SAM[1])
    with page.expect_navigation():
        page.click("form button[type=submit]")
    return page


def _fold(page: Any) -> float:
    """Where the first screen ends: the top of the row of places fixed at the foot."""
    return page.evaluate("document.querySelector('nav.row').getBoundingClientRect().top")


def _top(page: Any, selector: str) -> float:
    found = page.locator(selector).first
    assert found.count() == 1, selector
    return found.evaluate("one => one.getBoundingClientRect().top + window.scrollY")


@pytest.mark.parametrize(("address", "what", "selector"), FIRST, ids=[one[0] for one in FIRST])
def test_what_a_page_is_for_is_on_the_first_screen(site, address, what, selector) -> None:
    page = _signed_in(site, PHONE)
    page.goto(site[1] + address)
    assert _top(page, selector) < _fold(page), f"{address}: {what} is below the first screen"
    page.context.close()


def test_a_recipe_s_shopping_list_is_on_the_first_screen(site) -> None:
    """A recipe is cooked from: its one solid button is under what it takes, in sight."""
    page = _signed_in(site, PHONE)
    page.goto(site[1] + "/eat")
    recipe = page.locator("main .r--top .r__t a").first.get_attribute("href")
    page.goto(site[1] + recipe)
    assert _top(page, "main .acts .btn--primary") < _fold(page)
    page.context.close()


@pytest.mark.parametrize("viewport", [PHONE, NARROWEST], ids=["390", "320"])
def test_nothing_scrolls_sideways(site, viewport) -> None:
    page = _signed_in(site, viewport)
    for address, _, _ in FIRST:
        page.goto(site[1] + address)
        wider = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert wider <= 0, f"{address} at {viewport['width']}: {wider} px sideways"
    page.context.close()
