import socket
import threading
import time
import urllib.request
from datetime import UTC, timedelta
from pathlib import Path
from urllib.error import URLError

import pytest

from familydb.app import App
from familydb.errors import ConfigError
from familydb.store import db, ideas, outcomes, places, plans
from familydb.web import check_configuration, create_app
from tests.conftest import NOW_ISO

PASSWORD = "open sesame please"  # at least MIN_PASSWORD characters


def _client(settings, clock, **overrides):
    return create_app(App(settings.model_copy(update=overrides), clock)).test_client()


def _signed_in(settings, clock, **overrides):
    client = _client(settings, clock, web_password=PASSWORD, **overrides)
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


def test_health_check_needs_no_password(settings, clock) -> None:
    response = _client(settings, clock, web_password=PASSWORD).get("/healthz")
    assert response.status_code == 200 and response.text.strip() == "ok"
    assert response.mimetype == "text/plain"


def test_pages_are_behind_the_password(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    response = client.get("/idea/1")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/idea/1"
    assert client.post("/idea/1").status_code == 401  # a redirect would hide the reason
    assert client.head("/idea/1").status_code == 302  # a monitor reading is sent to log in
    page = client.get("/login")
    assert page.status_code == 200 and "Family password" in page.text


def test_signing_in_and_out(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    wrong = client.post("/login", data={"password": "guess"})
    assert wrong.status_code == 401 and "not right" in wrong.text
    good = client.post("/login", data={"password": PASSWORD, "next": "/plans"})
    assert good.status_code == 302 and good.headers["Location"] == "/plans"
    cookie = good.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Secure" not in cookie
    assert client.get("/nope").status_code == 404  # signed in: a real page, not a redirect
    assert client.get("/login").headers["Location"] == "/"  # already in
    assert client.post("/logout").headers["Location"] == "/login"
    assert client.get("/nope").status_code == 302


def test_the_next_parameter_cannot_leave_the_site(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    hostile = (
        "//evil.example/x",
        "https://evil.example",
        "javascript:alert(1)",
        "/\\evil.example",  # browsers read the backslash as a second slash
        "\\\\evil.example",
        "not-a-path",
    )
    for target in hostile:
        response = client.post("/login", data={"password": PASSWORD, "next": target})
        assert response.headers["Location"] == "/", target
        client.post("/logout")


def test_repeated_failures_lock_the_address_out(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    for _ in range(4):
        assert client.post("/login", data={"password": "no"}).status_code == 401
    locked = client.post("/login", data={"password": "no"})
    assert locked.status_code == 401 and "Too many tries" in locked.text
    still = client.post("/login", data={"password": PASSWORD})
    assert still.status_code == 429  # the right password does not shorten the wait
    clock.advance(timedelta(minutes=16))
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302


def test_a_post_from_another_site_is_refused(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    elsewhere = {"Origin": "https://evil.example"}
    refused = client.post("/login", data={"password": PASSWORD}, headers=elsewhere)
    assert refused.status_code == 400 and "did not come from this page" in refused.text
    client.post("/login", data={"password": PASSWORD})
    client.post("/logout", headers=elsewhere)
    assert client.get("/nope").status_code == 404  # still signed in


def test_every_response_carries_the_security_headers(settings, clock) -> None:
    client = _client(settings, clock, web_password=PASSWORD)
    plain = client.get("/login")
    assert "script-src 'none'" in plain.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in plain.headers["Content-Security-Policy"]
    assert plain.headers["X-Content-Type-Options"] == "nosniff"
    assert plain.headers["Referrer-Policy"] == "same-origin"
    assert plain.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in plain.headers  # plain HTTP: nothing to promise
    secure = client.get("/login", base_url="https://familydb.example")
    assert secure.headers["Strict-Transport-Security"].startswith("max-age=")


def test_a_browser_s_own_posts_carry_an_origin_the_page_accepts(settings, clock) -> None:
    """Under `Referrer-Policy: no-referrer` Chromium posts every form with `Origin: null`.

    The check below is right to refuse that — a null origin is also what a sandboxed frame on
    another site sends — so the policy is what has to let the real origin through. Both halves
    are pinned: a null origin is refused, and the policy is one under which browsers send the
    real one. The test client sends no Origin header on its own, so without this nothing would
    notice the page being unusable in a browser, which is how it went unnoticed before.
    """
    client = _client(settings, clock, web_password=PASSWORD)
    refused = client.post("/login", data={"password": PASSWORD}, headers={"Origin": "null"})
    assert refused.status_code == 400
    policy = client.get("/login").headers["Referrer-Policy"]
    # The policies under which a browser still names this origin on a same-site post.
    assert policy in {"same-origin", "strict-origin", "strict-origin-when-cross-origin"}
    accepted = client.post(
        "/login", data={"password": PASSWORD}, headers={"Origin": "http://localhost"}
    )
    assert accepted.status_code == 302


def test_a_loopback_page_without_a_password_is_open(settings, clock) -> None:
    client = _client(settings, clock)
    assert client.get("/nope").status_code == 404  # no gate at all
    assert client.get("/login").headers["Location"] == "/"
    assert "Sign out" not in client.get("/nope").text


def test_a_public_page_without_a_password_refuses_to_start(settings, clock) -> None:
    public = settings.model_copy(update={"web_host": "0.0.0.0"})
    with pytest.raises(ConfigError) as info:
        check_configuration(public)
    assert "WEB_PASSWORD" in str(info.value) and "WEB_ALLOW_NO_PASSWORD" in str(info.value)
    check_configuration(public.model_copy(update={"web_password": PASSWORD}))
    check_configuration(public.model_copy(update={"web_allow_no_password": True}))
    assert _client(settings, clock, web_host="0.0.0.0", web_allow_no_password=True) is not None


def test_behind_a_proxy_the_cookie_is_secure_and_the_client_is_the_real_one(settings, clock):
    client = _client(settings, clock, web_password=PASSWORD, web_trust_proxy=True)
    forwarded = {"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.7"}
    response = client.post("/login", data={"password": PASSWORD}, headers=forwarded)
    assert response.status_code == 302 and "Secure" in response.headers["Set-Cookie"]
    client.post("/logout", headers=forwarded)
    # The lockout counts the forwarded address, so one guesser cannot lock the whole family out.
    for _ in range(5):
        client.post("/login", data={"password": "no"}, headers=forwarded)
    assert client.post("/login", data={"password": PASSWORD}, headers=forwarded).status_code == 429
    other = {**forwarded, "X-Forwarded-For": "203.0.113.8"}
    assert client.post("/login", data={"password": PASSWORD}, headers=other).status_code == 302


def _idea(conn, title, **fields):
    with db.transaction(conn):
        return ideas.insert(
            conn, title=title, kind=fields.pop("kind", "activity"), now=NOW_ISO, **fields
        )


def _with_place(conn, idea, **fields):
    with db.transaction(conn):
        place = places.insert(
            conn,
            name=fields.pop("name", idea.title),
            now=NOW_ISO,
            last_checked_at=NOW_ISO,
            **fields,
        )
        ideas.update(conn, idea.id, {"place_id": place.id, "enrichment": "done"}, now=NOW_ISO)
    return place


def test_the_ideas_list_shows_what_is_stored(settings, clock, conn, family) -> None:
    ramen = _idea(
        conn,
        "Ramen & noodles <Main St>",
        kind="restaurant",
        participants=["whole family"],
        tags=["cheap"],
        cost_level=2,
        duration_min=60,
        location_name="Main St",
        suggested_by=family["sam"].id,
    )
    _idea(conn, "Museum day", kind="outing", participants=["with the girls"])
    page = _client(settings, clock).get("/")
    assert page.status_code == 200
    assert page.text.count('class="panel card"') == 2
    assert "2 ideas" in page.text
    # Titles come from chat, so they are escaped rather than rendered as markup.
    assert "Ramen &amp; noodles &lt;Main St&gt;" in page.text
    assert "<Main St>" not in page.text
    assert f'href="/idea/{ramen.id}"' in page.text
    assert "for whole family" in page.text and "$$" in page.text


def test_the_ideas_list_filters(settings, clock, conn, family) -> None:
    _idea(conn, "Ramen place", kind="restaurant", participants=["whole family"])
    _idea(conn, "Museum day", kind="outing", participants=["with the girls"])
    _idea(conn, "Old plan", kind="outing", status="done")
    dropped = _idea(conn, "Never again", kind="outing", status="dropped")
    client = _client(settings, clock)
    assert client.get("/").text.count('class="panel card"') == 3  # dropped is hidden
    assert "Ramen place" in client.get("/?kind=restaurant").text
    assert "Museum day" not in client.get("/?kind=restaurant").text
    assert client.get("/?status=done").text.count('class="panel card"') == 1
    assert f'href="/idea/{dropped.id}"' in client.get("/?status=dropped").text
    assert client.get("/?who=with+the+girls").text.count('class="panel card"') == 1
    assert "Museum" in client.get("/?q=museum").text
    assert client.get("/?q=nothinglikethis").text.count('class="panel card"') == 0
    assert "Clear" in client.get("/?kind=outing").text  # a way back to everything


def test_an_idea_page_shows_its_place_details(settings, clock, conn, family) -> None:
    idea = _idea(
        conn,
        "Hopscotch Portland",
        kind="outing",
        participants=["with the girls"],
        duration_min=120,
        cost_level=3,
        needs_booking=True,
        lead_time_days=2,
        setting="indoor",
        suggested_by=family["sam"].id,
    )
    _with_place(
        conn,
        idea,
        address="1030 NW 12th Ave, Portland",
        lat=45.53,
        lon=-122.68,
        website="https://example.com/hopscotch",
        booking_url="https://example.com/tickets",
        phone="555-0100",
        price_note="adults $28, kids free",
        hours={"sat": [{"open": "10:00", "close": "20:00"}], "mon": []},
        travel_minutes=45,
        travel_km=38.0,
        source_urls=["https://example.com/hopscotch"],
    )
    with db.transaction(conn):
        outcomes.insert(
            conn,
            idea_id=idea.id,
            plan_id=None,
            happened_on="2026-08-14",
            rating=9,
            would_repeat=True,
            notes="The girls loved it",
            recorded_by=family["sam"].id,
            now=NOW_ISO,
        )
        plans.insert(
            conn,
            title="Hopscotch",
            start="2026-10-03T18:30-07:00",
            end=None,
            all_day=False,
            idea_id=idea.id,
            created_by=family["sam"].id,
            now=NOW_ISO,
        )
    page = _client(settings, clock).get(f"/idea/{idea.id}")
    assert page.status_code == 200
    assert "1030 NW 12th Ave" in page.text and "openstreetmap.org" in page.text
    assert "Saturday" in page.text and "10:00-20:00" in page.text
    assert "closed" in page.text and "not known" in page.text  # Monday closed, Sunday unknown
    assert "about 45 min away, 38 km (estimate)" in page.text
    assert "needed, about 2 days ahead" in page.text
    assert "adults $28, kids free" in page.text
    assert "9/10" in page.text and "would go again" in page.text
    assert "The girls loved it" in page.text
    assert "Saturday 3 October, 18:30" in page.text
    assert 'rel="noopener noreferrer"' in page.text
    assert "checked today" in page.text


def test_an_idea_page_without_a_lookup_says_so(settings, clock, conn, family) -> None:
    idea = _idea(conn, "A picnic somewhere")
    page = _client(settings, clock).get(f"/idea/{idea.id}")
    assert "details not looked up yet" in page.text
    assert "Opening hours" not in page.text
    assert _client(settings, clock).get("/idea/404").status_code == 404
    assert "Not found" in _client(settings, clock).get("/idea/404").text


def test_a_stale_lookup_is_flagged(settings, clock, conn, family) -> None:
    idea = _idea(conn, "Old museum")
    with db.transaction(conn):
        place = places.insert(
            conn, name="Old museum", now=NOW_ISO, last_checked_at="2026-01-01T00:00:00Z"
        )
        ideas.update(conn, idea.id, {"place_id": place.id, "enrichment": "done"}, now=NOW_ISO)
    page = _client(settings, clock).get(f"/idea/{idea.id}")
    assert "may be out of date" in page.text
    assert "No opening hours were found." in page.text


def test_view_helpers_word_things_for_people() -> None:
    from datetime import date, datetime

    from familydb.store.ideas import Idea
    from familydb.store.places import Place
    from familydb.web import views

    def idea(**fields):
        return Idea(id=1, kind="activity", title="t", created_at="", updated_at="", **fields)

    assert views.duration_text(idea(duration_min=45)) == "about 45 min"
    assert views.duration_text(idea(duration_min=60, duration_max=90)) == "1 h to 1.5 h"
    assert views.duration_text(idea(duration_min=90, duration_max=90)) == "about 1.5 h"
    assert views.duration_text(idea()) is None
    assert views.cost_text(0) == "free" and views.cost_text(3) == "$$$"
    assert views.cost_text(None) is None
    assert views.participants_text(idea()) == "anyone"
    assert views.rating_text(idea(times_done=1, avg_rating=8.0)) == "done once, rated 8/10"
    assert views.rating_text(idea(times_done=2)) == "done 2 times"
    assert views.rating_text(idea()) is None
    assert views.details_text(idea(enrichment="skipped")) == "not one place to look up"

    now = datetime(2026, 9, 20, tzinfo=UTC)
    assert views.place_panel(None, now, 30) is None
    assert views.travel_text(None) is None
    bare = Place(id=1, name="X", created_at="c", updated_at="u")
    assert views.freshness_text(bare, now, 30) == "never checked"
    assert views.map_url(bare) is None
    assert views.map_url(bare.model_copy(update={"address": "1 Main St"})).endswith("1%20Main%20St")
    assert [r["hours"] for r in views.hours_rows(None)] == ["not known"] * 7

    today = date(2026, 9, 20)
    assert views.day_text("2026-09-26") == "Saturday 26 September"
    assert views.day_text("2026-09-26T18:30-07:00") == "Saturday 26 September, 18:30"
    assert views.day_text("not a date") == "not a date"
    assert views.relative_text("2026-09-20", today) == "today"
    assert views.relative_text("2026-09-21", today) == "tomorrow"
    assert views.relative_text("2026-09-19", today) == "yesterday"
    assert views.relative_text("2026-09-23", today) == "in 3 days"
    assert views.relative_text("2026-10-11", today) == "in 3 weeks"
    assert views.relative_text("2026-09-06", today) == "2 weeks ago"
    assert views.relative_text("whenever", today) is None


def test_the_restaurants_page_links_out(settings, clock, conn, family) -> None:
    ramen = _idea(
        conn, "Ramen place", kind="restaurant", participants=["whole family"], cost_level=2
    )
    _with_place(
        conn,
        ramen,
        address="1 Main St",
        lat=45.6,
        lon=-122.6,
        website="https://example.com/ramen",
        booking_url="https://example.com/book",
        price_note="about $18 a bowl",
        summary="Small counter, long queue.",
        hours={"sun": [{"open": "11:00", "close": "21:00"}]},
        travel_minutes=12,
    )
    _idea(conn, "Closed on Sundays", kind="restaurant")
    _idea(conn, "Museum day", kind="outing")
    page = _client(settings, clock).get("/restaurants")
    assert page.status_code == 200
    assert page.text.count('class="panel card"') == 2  # the outing is not here
    assert "Museum day" not in page.text and "2 places" in page.text
    assert "Small counter, long queue." in page.text and "1 Main St" in page.text
    assert "open today 11:00-21:00" in page.text  # the shared clock is a Sunday
    assert "about 12 min away" in page.text and "$$" in page.text
    assert 'href="https://example.com/ramen" rel="noopener noreferrer"' in page.text
    assert 'href="https://example.com/book" rel="noopener noreferrer"' in page.text
    assert "openstreetmap.org" in page.text
    assert f'href="/idea/{ramen.id}"' in page.text
    assert "details not looked up yet" in page.text  # the second restaurant


def test_the_restaurants_page_when_there_are_none(settings, clock, conn, family) -> None:
    _idea(conn, "Museum day", kind="outing")
    page = _client(settings, clock).get("/restaurants")
    assert "No restaurants yet" in page.text and page.text.count('class="panel card"') == 0


def test_the_plans_page_shows_what_is_coming_and_what_just_happened(
    settings, clock, conn, family
) -> None:
    idea = _idea(conn, "Hopscotch Portland", kind="outing")
    with db.transaction(conn):
        plans.insert(
            conn,
            title="Hopscotch",
            start="2026-10-03T18:30-07:00",
            end=None,
            all_day=False,
            idea_id=idea.id,
            location="Portland",
            created_by=family["sam"].id,
            now=NOW_ISO,
        )
        plans.insert(
            conn,
            title="Farmers market",
            start="2026-09-12",
            end="2026-09-12",
            all_day=True,
            created_by=family["sam"].id,
            now=NOW_ISO,
        )
        gone = plans.insert(
            conn,
            title="Cancelled dinner",
            start="2026-09-26",
            end=None,
            all_day=True,
            created_by=family["sam"].id,
            now=NOW_ISO,
        )
        far = plans.insert(
            conn,
            title="Next summer",
            start="2027-07-01",
            end=None,
            all_day=True,
            created_by=family["sam"].id,
            now=NOW_ISO,
        )
        plans.update(conn, gone.id, {"status": "cancelled"}, now=NOW_ISO)
    page = _client(settings, clock).get("/plans")
    assert page.status_code == 200
    assert "Saturday 3 October, 18:30" in page.text and "in 13 days" in page.text
    assert f'href="/idea/{idea.id}"' in page.text and "Portland" in page.text
    assert "Farmers market" in page.text and "Saturday 12 September" in page.text
    assert "Cancelled dinner" not in page.text  # cancelled plans are not shown
    assert "Next summer" not in page.text and str(far.id) not in page.text.split("Recently")[0]


def test_the_plans_page_when_the_calendar_is_empty(settings, clock, conn, family) -> None:
    page = _client(settings, clock).get("/plans")
    assert "Nothing on the calendar for the next 90 days." in page.text
    assert "Recently" not in page.text


def test_the_nav_reaches_every_page(settings, clock, conn, family) -> None:
    client = _client(settings, clock)
    home = client.get("/")
    for target in ("/", "/restaurants", "/plans"):
        assert f'href="{target}"' in home.text, target
        assert client.get(target).status_code == 200


def test_links_that_are_not_web_addresses_never_become_links(settings, clock, conn, family) -> None:
    # An idea's link comes straight from a chat message, and a place saved before links were
    # filtered may hold anything. Neither may reach an href.
    idea = _idea(conn, "Dodgy link", url="javascript:alert(1)")
    _with_place(
        conn,
        idea,
        website="javascript:alert(2)",
        booking_url="  https://example.com/book  ",
        source_urls=["data:text/html,<script>", "https://example.com/about"],
    )
    page = _client(settings, clock).get(f"/idea/{idea.id}")
    assert page.status_code == 200
    assert "javascript:" not in page.text and "data:text/html" not in page.text
    assert 'href="https://example.com/book"' in page.text
    assert 'href="https://example.com/about"' in page.text

    restaurant = _idea(conn, "Dodgy diner", kind="restaurant", url="javascript:alert(3)")
    cards = _client(settings, clock).get("/restaurants")
    assert "javascript:" not in cards.text and "Their site" not in cards.text
    assert restaurant.title in cards.text


def test_the_lockout_table_does_not_grow_without_limit(settings, clock) -> None:
    from familydb.web.auth import MAX_ATTEMPTS, MAX_TRACKED, Lockout

    lockout = Lockout()
    now = clock.now()
    for number in range(MAX_TRACKED + 50):  # one failure each, from many addresses
        lockout.failed(f"10.0.{number // 256}.{number % 256}", now)
    assert len(lockout.failures) <= MAX_TRACKED + 1
    # Someone actually locked out is still locked out after a prune.
    for _ in range(MAX_ATTEMPTS):
        lockout.failed("198.51.100.4", now)
    assert lockout.locked("198.51.100.4", now)
    for number in range(MAX_TRACKED + 50):
        lockout.failed(f"172.16.{number // 256}.{number % 256}", now)
    assert lockout.locked("198.51.100.4", now)


def test_no_page_reaches_a_table_to_write_to_it() -> None:
    """No module in the package may write to a table itself, and that includes the three
    that change things: the chat page hands a message to the pipeline, the edit forms call the
    tools, the settings page goes through one repository. Every write is somebody else's, which
    is what keeps the checks, the transactions and the audit rows in one place."""
    import ast

    import familydb.web as package

    stores = {
        "db",
        "ideas",
        "places",
        "plans",
        "outcomes",
        "members",
        "messages",
        "calls",
        "suggestions",
        "idea_store",
        "place_store",
        "plan_store",
        "outcome_store",
    }
    writes = {
        "insert",
        "insert_in",
        "insert_out",
        "update",
        "delete",
        "transaction",
        "migrate",
        "apply_outcome",
        "requeue_enrichment",
        "mark_followed_up",
        "set_reply",
        "set_active",
        "mark_processed",
        "mark_failed",
        "claim_retry",
        "give_up",
        "reset_retries",
        "add",
        "set_many",
        "clear",
    }
    stores.add("settings_store")
    for module in sorted(Path(package.__file__).parent.glob("*.py")):
        if module.name == "settings.py":
            continue  # app_settings is its own table; the next test pins how far it goes
        tree = ast.parse(module.read_text("utf-8"), filename=module.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "familydb.store"
            ):
                for alias in node.names:
                    assert alias.name not in writes, f"{module.name} imports {alias.name}"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                base = node.func.value
                called = node.func.attr
                writing = isinstance(base, ast.Name) and base.id in stores and called in writes
                assert not writing, f"{module.name}:{node.lineno} calls {called} on a store"


def test_only_four_pages_can_change_anything_and_only_the_agreed_way() -> None:
    """Which modules may cause a write, and what each one is allowed to go through.

    Nothing here writes, so the previous test alone would pass even if a page had quietly grown
    a way to change an idea. This one names the doors instead: the chat page may reach the
    pipeline and nothing else, the edit forms may dispatch a fixed list of tools and nothing
    else, the family page may add and change people through `familydb.family` and nothing else,
    and every other module in the package may do none of it.
    """
    import ast

    import familydb.web as package

    folder = Path(package.__file__).parent
    trees = {
        module.name: ast.parse(module.read_text("utf-8"), filename=module.name)
        for module in sorted(folder.glob("*.py"))
    }

    # The chat page hands a message over, and the handing over is all it does.
    chat = trees["chat.py"]
    assert {
        f"{node.module}.{alias.name}"
        for node in ast.walk(chat)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("familydb.channels")
        for alias in node.names
    } == {"familydb.channels.web.DEFAULT_CHAT", "familydb.channels.web.WebChat"}
    assert not [
        node
        for node in ast.walk(chat)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("familydb.pipeline")
    ], "chat.py reaches the pipeline through the channel, not around it"

    # The edit forms may run these tools and no others. A new one is a deliberate line here.
    edits = trees["edits.py"]
    dispatched = {
        node.args[0].value
        for node in ast.walk(edits)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert dispatched == {
        "add_idea",
        "update_idea",
        "record_outcome",
        "create_event",
        "update_event",
        "delete_event",
    }
    # And it runs them the one way: through the registry, which validates and owns the
    # transaction. Constructing a store call or a connection of its own would not be that.
    assert (
        sum(
            1
            for node in ast.walk(edits)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "dispatch"
        )
        == 1
    )

    # The family page adds and changes people, through the rules module, and that is all.
    family = trees["family.py"]
    ruled = {
        node.func.attr
        for node in ast.walk(family)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "rules"
    }
    assert ruled <= {"add", "change", "revision"}, ruled
    assert {"add", "change"} <= ruled

    # And the doors are shut to everything else. Not whole packages: `views.py` reads opening
    # hours out of `tools.places` and tidies a link with `tools.urls`, which write nothing. It
    # is the two ways of causing a write that are spoken for — the pipeline, and dispatch.
    for name, tree in trees.items():
        reached = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        dispatches = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "dispatch"
            for node in ast.walk(tree)
        )
        assert not any(module.startswith("familydb.pipeline") for module in reached), name
        # The page reads Google through calendar_sync's pure translation of an event; the two
        # functions there that bring stored plans up to date are writes, and belong to the bot.
        synced = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "familydb.calendar_sync"
            for alias in node.names
        }
        assert synced <= {"event_changes"}, f"{name} imports {synced}"
        if name != "family.py":
            family_rules = any(
                isinstance(node, ast.ImportFrom)
                and (
                    node.module == "familydb.family"
                    or (node.module == "familydb" and any(a.name == "family" for a in node.names))
                )
                for node in ast.walk(tree)
            )
            assert not family_rules, f"{name} reaches the family rules"
        if name not in {"chat.py", "__init__.py"}:  # the factory builds the thing chat.py uses
            assert not any(module.startswith("familydb.channels") for module in reached), name
        if name != "edits.py":
            assert "familydb.tools" not in reached, f"{name} imports the tool machinery"
            assert not dispatches, f"{name} dispatches a tool"


def test_only_the_settings_page_writes_and_only_to_the_settings() -> None:
    """One module may write, to one table, through one repository, and that is the whole of it."""
    import ast

    import familydb.web as package

    module = Path(package.__file__).parent / "settings.py"
    tree = ast.parse(module.read_text("utf-8"), filename=module.name)
    imported = {
        f"{node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("familydb.store")
        for alias in node.names
    }
    assert imported == {
        "familydb.store.settings",  # the only repository it may reach
        "familydb.store.settings.SECRETS",
        "familydb.store.db.transaction",  # a write has to be inside one
    }
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "settings_store"
    }
    assert called == {"overrides", "history", "set_many"}


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_a_page_that_cannot_start_leaves_the_bot_running(settings, clock) -> None:
    from familydb.web.server import serve_in_thread

    forbidden = App(settings.model_copy(update={"web_host": "0.0.0.0"}), clock)
    assert serve_in_thread(forbidden) is None  # no password: refused, and no exception escapes

    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen(1)
        busy = settings.model_copy(update={"web_port": taken.getsockname()[1]})
        assert serve_in_thread(App(busy, clock)) is None


def test_the_page_really_serves_on_a_thread_and_stops(settings, clock) -> None:
    from familydb.web.server import serve_in_thread

    port = _free_port()
    app = App(settings.model_copy(update={"web_port": port, "web_password": PASSWORD}), clock)
    stop = serve_in_thread(app)
    assert stop is not None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=5) as answer:
            assert answer.read().strip() == b"ok"
    finally:
        stop()
    # Stopping is not instant: give the serving loop a moment to notice the closed socket.
    for _ in range(50):
        if not any(t.name == "familydb-web" and t.is_alive() for t in threading.enumerate()):
            break
        time.sleep(0.1)
    else:
        raise AssertionError("the web thread did not stop")
    with pytest.raises(URLError):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2)


def test_changing_the_password_ends_the_sessions_opened_with_the_old_one(
    settings, clock, conn
) -> None:
    client = _signed_in(settings, clock)
    assert client.get("/").status_code == 200
    cookie = client.get_cookie("session")
    assert cookie is not None

    # The same family, the same signing key, a new password: the old cookie is no longer a login.
    changed = _client(settings, clock, web_password="a different long one")
    changed.set_cookie("session", cookie.value)
    assert changed.get("/").status_code == 302
    assert changed.get("/").headers["Location"] == "/login?next=/"


def test_a_form_token_outside_ascii_is_refused_and_not_a_crash(settings, clock, conn) -> None:
    client = _signed_in(settings, clock)
    answer = client.post("/settings", data={"csrf": "n\u00e9", "web_title": "x"})
    assert answer.status_code == 400


def test_the_server_refuses_a_body_before_reading_it(settings, clock) -> None:
    from familydb.web import MAX_BODY_BYTES
    from familydb.web.server import create_server

    app = App(settings.model_copy(update={"web_port": _free_port()}), clock)
    server = create_server(app)
    try:
        assert server.adj.max_request_body_size == MAX_BODY_BYTES
    finally:
        server.close()


def test_a_public_page_needs_a_password_worth_having(settings, clock) -> None:
    from familydb.web import MIN_PASSWORD

    public = settings.model_copy(update={"web_host": "0.0.0.0"})
    with pytest.raises(ConfigError) as info:
        check_configuration(public.model_copy(update={"web_password": "hunter2"}))
    assert str(MIN_PASSWORD) in str(info.value) and "7 characters" in str(info.value)
    check_configuration(public.model_copy(update={"web_password": "x" * MIN_PASSWORD}))
    # A page only this machine can reach may keep a short one.
    check_configuration(settings.model_copy(update={"web_password": "hunter2"}))


def test_guessing_from_many_addresses_still_runs_out(settings, clock) -> None:
    from familydb.web.auth import GLOBAL_ATTEMPTS, Lockout

    lockout = Lockout()
    now = clock.now()
    for number in range(GLOBAL_ATTEMPTS):
        who = f"203.0.113.{number}"  # a fresh address every time, so no address is ever locked
        assert not lockout.locked(who, now)
        lockout.failed(who, now)
    assert lockout.locked("198.51.100.1", now)  # the site as a whole stops answering
    clock.advance(timedelta(minutes=16))
    assert not lockout.locked("198.51.100.1", clock.now())


def test_an_impossible_idea_number_is_a_missing_page(settings, clock, conn, family) -> None:
    client = _client(settings, clock)
    assert client.get("/idea/99999999999999999999").status_code == 404
    assert client.get("/idea/-1").status_code == 404
    assert client.get("/idea/abc").status_code == 404


def test_a_page_the_bot_serves_is_never_cached(settings, clock, conn, family) -> None:
    client = _client(settings, clock)
    assert client.get("/").headers["Cache-Control"] == "no-store"
    assert client.get("/login").headers["Cache-Control"] == "no-store"
    # The stylesheet keeps whatever Flask decided; only the family's own pages are held back.
    assert client.get("/static/style.css").headers["Cache-Control"] != "no-store"


def test_the_added_date_is_the_family_s_date(settings, clock, conn, family) -> None:
    # 02:30 UTC is still the evening before in America/Vancouver.
    with db.transaction(conn):
        idea = ideas.insert(
            conn, title="Late night idea", kind="activity", now="2026-09-21T02:30:00Z"
        )
    page = _client(settings, clock).get(f"/idea/{idea.id}")
    assert "added 2026-09-20" in page.text
