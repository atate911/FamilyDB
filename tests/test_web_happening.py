"""The page of what is on near home: by day, outside links kept safe, for grown-ups, with a
tab beside Plans' List and Month."""

from __future__ import annotations

import re
from datetime import date, datetime

import pytest
from markupsafe import escape

from familydb import happening
from familydb.app import App
from familydb.integrations.events import FoundEvent
from familydb.store import finds
from familydb.store.db import transaction
from familydb.web import create_app
from tests.conftest import TZ

PASSWORD = "open sesame please"


@pytest.fixture
def page(settings, clock, conn, family):
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


def _listed(conn, *events: FoundEvent, source="feed:https://library.example.org/e.ics") -> None:
    with transaction(conn):
        finds.upsert_many(conn, source, "feed", events, tz=TZ, now="2026-09-20T12:00:00Z")


def test_what_is_on_is_listed_by_day_with_who_listed_it(page, conn) -> None:
    _listed(
        conn,
        FoundEvent(
            external_id="a",
            title="Story time <script>alert(1)</script>",
            starts=datetime(2026, 9, 26, 10, 30, tzinfo=TZ),
            venue="Main library",
            url="https://library.example.org/story",
        ),
        FoundEvent(
            external_id="b",
            title="Exhibit",
            starts=date(2026, 9, 1),
            ends=date(2026, 10, 2),
            all_day=True,
            url="javascript:alert(1)",
        ),
    )
    text = page.get("/happening").text
    assert f'<h1 class="dest__q">{escape(happening.NAME)}</h1>' in text
    assert "<script>alert(1)</script>" not in text and "&lt;script&gt;" in text
    assert "javascript:" not in text
    assert "listed by library.example.org" in text
    assert text.index("Today") < text.index("Saturday 26 September")
    assert "until Thu 1 Oct" in text and '<span class="fig">10:30\u00a0am</span>' in text
    # Each opens a page of its own: the listing's link there, never one that is no web address.
    story, exhibit = (finds.get(conn, number) for number in (1, 2))
    assert story is not None and exhibit is not None and 'href="/soon/1"' in text
    own = page.get("/soon/1").text
    assert 'href="https://library.example.org/story" rel="noopener noreferrer"' in own
    assert "Saturday 26 September, <span" in own and "Main library" in own
    assert "The listing" in own and "Save it" in own and 'action="/plans/new"' in own
    other = page.get("/soon/2").text
    assert "javascript:" not in other and "On until Thursday 1 October" in other
    assert page.get("/soon/99").status_code == 404


def test_the_page_is_soon_in_the_row_and_beside_list_and_month(page) -> None:
    for path in ("/plans", "/plans/month"):
        assert 'href="/soon"' in page.get(path).text
    text = page.get("/happening").text
    assert 'href="/soon" aria-current="page"' in text
    assert "Nothing near home is read yet." in text


def _form(text: str, action: str) -> dict[str, str]:
    """The tokens of the form posting to `action`."""
    import re

    form = text[text.index(f'action="{action}"') :]
    form = form[: form.index("</form>")]
    return dict(re.findall(r'name="(csrf|once|find_id|title|kind)" value="([^"]*)"', form))


def test_something_she_found_is_saved_or_not_for_us_and_says_so(page, conn) -> None:
    with transaction(conn):
        finds.keep(
            conn,
            "request",
            "request",
            [
                finds.NewFind(title="Rose garden", url="https://parks.example.org/roses"),
                finds.NewFind(title="Night market", url="https://market.example.org/"),
            ],
            now="2026-09-20T12:00:00Z",
        )
    roses = page.get("/soon/1").text
    # A place to go any time, named by the site the search found it on.
    assert "Any time" in roses and "Listed by parks.example.org." in roses
    assert "Not for us" in roses
    saving = _form(roses, "/ideas/new")
    assert (saving["find_id"], saving["kind"]) == ("1", "outing")
    assert page.post("/ideas/new", data=saving).status_code == 302
    saved = finds.get(conn, 1)
    assert saved.state == "saved" and saved.idea_id is not None
    after = page.get("/soon/1").text
    assert f'href="/idea/{saved.idea_id}"' in after and "Not for us" not in after

    market = page.get("/soon/2").text
    assert page.post("/soon/2/pass", data=_form(market, "/soon/2/pass")).status_code == 302
    assert finds.get(conn, 2).state == "passed"
    after = page.get("/soon/2").text
    assert "Not for you. It will not be offered again." in after and "Save it" not in after


def test_a_row_is_one_line_in_the_familys_clock(page, conn) -> None:
    """Each row says when, where, cost and who listed it on one line, the time as the family
    reads it, all-day things before timed ones and timed ones by the clock (6 pm after 10 am);
    what the listing says is on its own page."""
    _listed(
        conn,
        FoundEvent(
            external_id="late",
            title="Lantern walk",
            starts=datetime(2026, 9, 26, 18, 0, tzinfo=TZ),
            summary="Bring a lantern or make one at the craft tent.",
        ),
        FoundEvent(
            external_id="early", title="Story time", starts=datetime(2026, 9, 26, 10, 0, tzinfo=TZ)
        ),
        FoundEvent(external_id="day", title="Book sale", starts=date(2026, 9, 26), all_day=True),
    )
    text = page.get("/happening").text
    assert text.index("Book sale") < text.index("Story time") < text.index("Lantern walk")
    # What a person reads, not what Save it and Plan it carry for the tools.
    shown = re.sub(r'<input type="hidden"[^>]*>', "", text)
    assert "6\u00a0pm" in shown and "18:00" not in shown
    assert "Bring a lantern" not in shown and "Bring a lantern" in page.get("/soon/1").text
    assert '<span class="tag tag--off">listed by' not in text


def test_a_row_coming_up_is_saved_or_planned_where_it_is(page, conn) -> None:
    """Coming up (the redesign of November 2026): Save it, Plan it and Not for us on each row
    still hers to offer, each the tool she would call; Plan it takes the listing's day and time,
    and comes back to the list saying it is on the plans."""
    from familydb.store import plans

    _listed(
        conn,
        FoundEvent(
            external_id="late",
            title="Lantern walk",
            starts=datetime(2026, 9, 26, 18, 0, tzinfo=TZ),
            venue="Cedar Park",
        ),
        FoundEvent(external_id="day", title="Book sale", starts=date(2026, 9, 26), all_day=True),
    )
    text = page.get("/soon").text
    row = text[text.index("Lantern walk") :].split('<div class="r">')[0]
    assert "Save it" in row and "Not for us" in row and "Plan it" in row
    plan = re.search(r'<form method="post" action="/plans/new">.*?</form>', row, re.S).group(0)
    assert 'name="start" value="2026-09-26T18:00"' in plan and 'name="all_day"' not in plan
    assert 'name="back" value="/soon"' in plan and 'name="location" value="Cedar Park"' in plan
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', plan))
    back = page.post("/plans/new", data=fields, follow_redirects=True)
    assert "Added to the plans: Lantern walk." in back.text
    (made,) = [one for one in plans.everything(conn) if one.title == "Lantern walk"]
    assert made.start.startswith("2026-09-26T18:00")
    assert finds.get(conn, 1).state == "planned"
    # Planned, it is no longer hers to offer: its row has no buttons.
    again = page.get("/soon").text
    assert "Plan it<span" not in again[again.index("Lantern walk") :].split('<div class="r">')[0]
    # An all-day one goes on its day.
    sale = again[again.index("Book sale") :].split('<div class="r">')[0]
    assert 'name="start" value="2026-09-26"' in sale and 'name="all_day" value="yes"' in sale
    # Save it on a row comes back to the rows, so several can be saved one after another.
    saving = re.search(r'<form method="post" action="/ideas/new">.*?</form>', sale, re.S).group(0)
    kept = page.post("/ideas/new", data=dict(re.findall(r'name="(\w+)" value="([^"]*)"', saving)))
    assert kept.status_code == 302 and kept.headers["Location"] == "/soon"
    assert finds.get(conn, 2).state == "saved"
