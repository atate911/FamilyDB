"""The page of what is on near home: by day, outside links kept safe, for grown-ups, with a
tab beside Plans' List and Month."""

from __future__ import annotations

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
    assert f"<h1>{escape(happening.NAME)}</h1>" in text
    assert "<script>alert(1)</script>" not in text and "&lt;script&gt;" in text
    assert "javascript:" not in text
    assert 'rel="noopener noreferrer"' in text and "listed by library.example.org" in text
    assert text.index("Today") < text.index("Saturday 26 September")
    assert "until Thu 1 Oct" in text and "10:30" in text


def test_the_tab_is_beside_list_and_month(page) -> None:
    for path in ("/plans", "/plans/month"):
        assert 'href="/happening"' in page.get(path).text
    text = page.get("/happening").text
    assert 'href="/happening" aria-current="page"' in text
    assert "Nothing near home is read yet." in text
