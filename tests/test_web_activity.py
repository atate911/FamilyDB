"""The status page's recent activity, and each message's or lookup's history in full."""

from __future__ import annotations

import re

from familydb.channels.base import IncomingMessage
from familydb.jobs.enrich import run_enrichment
from familydb.pipeline import handle_incoming
from familydb.store import ideas
from tests import fakes
from tests import test_web_logins as logins
from tests.test_jobs import _captured_idea, _web_app

# The logins tests' fixtures: an app whose people sign in as themselves, Sam an admin, Alex not.
app = logins.app
sam = logins.sam
alex = logins.alex


def _activity(page: str) -> list[tuple[str, str]]:
    """Each line of recent activity: where it opens, and its title."""
    found = re.search(r'<section class="panel" id="activity">.*?</section>', page, re.S)
    assert found is not None
    return re.findall(
        r'<a href="(/status/activity/[^"]+)">\s*<span class="activity-title">([^<]+)</span>',
        found.group(0),
    )


def test_a_message_s_history_shows_every_call_and_tool_and_the_reply(app, sam, alex, conn):
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "tu_1", "add_idea", {"title": "Ramen <b>place</b>", "kind": "restaurant"}
                )
            ],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("Saved #1 Ramen place.")]),
    )
    reply = handle_incoming(
        app,
        IncomingMessage("telegram", "9", "chat-1", "1001", "we should try the ramen place"),
        api=api,
        conn=conn,
    )
    lines = _activity(sam.get("/status").text)
    assert lines == [
        (f"/status/activity/m{reply.in_message_id}", "Sam: we should try the ramen place")
    ]

    page = sam.get(lines[0][0]).text
    assert "A message from Sam" in page and "we should try the ramen place" in page
    assert "Saved #1 Ramen place." in page  # the reply
    assert "2 calls:" in page and page.count("<td>answering the family</td>") == 2
    assert "<code>add_idea</code>" in page
    # What the model sent is shown as it came, never as markup.
    assert "Ramen &lt;b&gt;place&lt;/b&gt;" in page and "<b>place</b>" not in page

    # Words from any chat: a parent sees neither the list nor a history.
    assert 'id="activity"' not in alex.get("/status").text
    assert alex.get(lines[0][0]).status_code == 403


def test_a_lookup_s_history_says_what_it_found_and_the_pages_it_read(
    settings, clock, conn, family
) -> None:
    from familydb.web import create_app

    looking = _web_app(settings, clock)
    idea, _ = _captured_idea(conn, family)
    api = fakes.FakeMessagesAPI(
        *fakes.enrich_script(
            {
                "idea_id": idea.id,
                "name": "Hopscotch Portland",
                "hours": [{"day": "sat", "open": "10:00", "close": "20:00"}],
                "source_urls": ["https://example.com/place", "javascript:alert(1)"],
            }
        )
    )
    assert run_enrichment(looking, api=api)["done"] == 1
    client = create_app(looking).test_client()
    lines = _activity(client.get("/status").text)
    assert lines[0][1] == f"Looking up #{idea.id} Hopscotch, Portland"
    assert re.fullmatch(r"/status/activity/t[0-9a-f]{16}", lines[0][0])

    page = client.get(lines[0][0]).text
    assert "What the lookup found" in page and "Hopscotch Portland" in page
    assert "sat 10:00-20:00" in page
    # A page it read is a link only when it is a web address; the rest stays words.
    assert '<a href="https://example.com/place"' in page and 'href="javascript:' not in page
    assert "<code>save_place</code>" in page
    assert ideas.get(conn, idea.id).enrichment == "done"
    # And the idea itself says how it was looked up, with the way to it.
    assert f'href="{lines[0][0]}">How it was looked up</a>' in client.get(f"/idea/{idea.id}").text


def test_a_history_that_is_not_there_is_not_found(settings, clock, conn, family) -> None:
    from familydb.app import App
    from familydb.web import create_app

    client = create_app(App(settings, clock)).test_client()
    for key in ("m999", "tffffffffffffffff", "x1", "t123", "m1'--"):
        assert client.get(f"/status/activity/{key}").status_code == 404, key
