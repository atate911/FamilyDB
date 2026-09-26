"""Setting up on the page, one step at a time, from a new install to the first answer.

The setup pages only read. Every form on them is one the rest of the page already has, posting to
the module that owns the change and asking to be brought back; these tests walk that loop.
"""

from __future__ import annotations

import re

import pytest

from familydb.app import App
from familydb.integrations.geocode import GeoPoint
from familydb.store import db, knocks, members
from familydb.store import settings as settings_store
from familydb.web import create_app
from tests.conftest import NOW_ISO
from tests.fakes import FakeGeocoder

INSTALLERS = "installer-made-password-1"
POINT = GeoPoint(45.6387, -122.6615, "Vancouver, Washington", "nominatim")


@pytest.fixture
def fresh(settings, clock, conn):
    """A new install: the installer's password, nobody on the list, and no model key."""
    app = App(
        settings.model_copy(
            update={
                "web_password": INSTALLERS,
                # OpenAI, because Anthropic's SDK also finds credentials the settings never see.
                "provider": "openai",
                "anthropic_api_key": "",
                "openai_api_key": "",
                "gemini_api_key": "",
                "provider_fallback": False,
            }
        ),
        clock,
        geocoder=FakeGeocoder(default=POINT),
    )
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": INSTALLERS}).status_code == 302
    client.app = app
    return client


def app_client(app):
    """Another browser on the same install."""
    return create_app(app).test_client()


def _tokens(client, url: str) -> dict[str, str]:
    text = client.get(url).text
    found = {"csrf": re.search(r'name="csrf" value="([^"]+)"', text).group(1)}
    once = re.search(r'name="once" value="([^"]+)"', text)
    if once:
        found["once"] = once.group(1)
    return found


def _post(browser, step: str, action: str, **form: str):
    """Send a form the way the setup page draws it: tokens, and where to come back to."""
    data = {**_tokens(browser, f"/setup/{step}"), "then": f"/setup/{step}", **form}
    return browser.post(action, data=data)


def _say(monkeypatch, verdict: str) -> None:
    """What every company says about any key, for the length of one test."""
    from familydb.agent.providers.anthropic import AnthropicProvider
    from familydb.agent.providers.gemini import GeminiProvider
    from familydb.agent.providers.openai import OpenAIProvider

    for company in (AnthropicProvider, GeminiProvider, OpenAIProvider):
        monkeypatch.setattr(company, "check_key", lambda self: verdict)


def test_a_new_install_opens_on_setup_until_it_can_answer(fresh) -> None:
    assert fresh.get("/").headers["Location"] == "/setup"
    page = fresh.get("/setup").text
    for title in ("Add yourself", "Your own password", "Connect an AI model"):
        assert title in page
    assert page.count('class="tag need-needed">needed<') == 2  # yourself, and a model
    assert 'href="/setup/you">Start' in page
    assert "Go to the home page" not in page  # it would only send you back here


def test_every_step_says_where_it_is_and_how_to_leave(fresh) -> None:
    page = fresh.get("/setup/model").text
    assert "Step 3 of 7" in page and 'aria-current="step"' in page
    assert 'href="/setup/password">← Back' in page
    assert "Skip for now" in page and 'href="/setup/home"' in page
    assert fresh.get("/setup/nothing-like-this").status_code == 404


def test_the_whole_way_through(fresh, monkeypatch, conn) -> None:
    app = fresh.app

    # 1. Yourself, as the admin.
    back = _post(fresh, "you", "/family", name="Sam", role="admin")
    assert back.headers["Location"] == "/setup/you"
    assert "✓ On the list as Sam." in fresh.get("/setup/you").text

    # 2. Your own password, which signs this browser in as Sam and ends the installer's.
    sam = members.find_by_name(conn, "Sam")
    page = fresh.get("/setup/password").text
    assert f'name="member" value="{sam.id}"' in page and "For <strong>Sam</strong>" in page
    ours = "pancakes on sunday mornings"
    back = _post(fresh, "password", "/you", member=str(sam.id), new=ours, again=ours)
    assert back.headers["Location"] == "/setup/password"
    page = fresh.get("/setup/password").text
    assert "You sign in as Sam from now on" in page
    assert "✓ Everybody signs in as themselves." in page and "You sign in as Sam" in page
    stranger = app_client(app)
    assert stranger.post("/login", data={"password": INSTALLERS}).status_code == 400
    refused = stranger.post("/login", data={"name": "Sam", "password": INSTALLERS})
    assert refused.status_code == 401
    assert stranger.post("/login", data={"name": "sam", "password": ours}).status_code == 302

    # 3. A model: the key is checked with the company before it is kept.
    _say(monkeypatch, "works")
    back = _post(fresh, "model", "/settings/model", provider="openai", key="sk-good")
    assert back.headers["Location"] == "/setup/model"
    page = fresh.get("/setup/model").text
    assert "OpenAI accepted the key. Vera answers with gpt-6-luna." in page
    lineup = " ".join(page.split())
    assert "GPT-6 Luna (everyday, $0.10 in, $0.50 out); GPT-6 Sol (better," in lineup
    assert app.settings.openai_api_key == "sk-good" and app.settings.provider == "openai"

    # It can answer now, so the home page is the home page again.
    assert fresh.get("/").status_code == 200

    # 4. Home: found on the map, and said so.
    _post(fresh, "home", "/settings", home_area="Vancouver, WA", weather_units="imperial")
    page = fresh.get("/setup/home").text
    assert "Found Vancouver, Washington" in page and "✓ Vancouver, WA" in page
    assert app.settings.weather_units == "imperial"

    done = fresh.get("/setup/done").text
    assert "You\u2019re set up" in done and "What should we do this weekend?" in done


def test_a_key_the_company_refuses_is_not_kept(fresh, monkeypatch) -> None:
    _say(monkeypatch, "refused")
    _post(fresh, "model", "/settings/model", provider="openai", key="sk-mistyped")
    page = fresh.get("/setup/model").text
    assert "OpenAI did not accept that key, so it was not saved." in page
    assert not fresh.app.settings.openai_api_key


def test_a_company_that_cannot_be_asked_does_not_stop_the_key(fresh, monkeypatch) -> None:
    _say(monkeypatch, "unchecked")
    _post(fresh, "model", "/settings/model", provider="gemini", key="AIza-maybe")
    page = fresh.get("/setup/model?company=gemini").text
    assert "Google could not be asked just now" in page
    assert fresh.app.settings.gemini_api_key == "AIza-maybe"
    assert fresh.app.settings.provider == "gemini"


def test_a_key_check_names_the_model_it_asked_about(fresh, monkeypatch, conn) -> None:
    """The check looks the everyday model up; a stronger chat level is what then answers."""
    with db.transaction(conn):
        settings_store.set_many(conn, {"chat_level": "better"})
    _say(monkeypatch, "unknown_model")
    _post(fresh, "model", "/settings/model", provider="openai", key="sk-good")
    assert "says it has no model called gpt-6-luna" in fresh.get("/setup/model").text
    _say(monkeypatch, "works")
    _post(fresh, "model", "/settings/model", provider="openai", key="sk-good")
    page = fresh.get("/setup/model").text
    assert "OpenAI accepted the key. Vera answers with gpt-6-sol." in page


def test_choosing_a_company_shows_its_own_instructions(fresh) -> None:
    assert "platform.openai.com/api-keys" in fresh.get("/setup/model").text
    anthropic = fresh.get("/setup/model?company=anthropic").text
    assert "console.anthropic.com/settings/keys" in anthropic and "sk-ant-" in anthropic
    assert "aistudio.google.com/apikey" in fresh.get("/setup/model?company=gemini").text
    # Anything else is the company in force, not an error.
    assert "platform.openai.com/api-keys" in fresh.get("/setup/model?company=nope").text


def test_telegram_from_a_token_to_a_linked_phone(fresh, monkeypatch, conn) -> None:
    app = fresh.app
    _post(fresh, "you", "/family", name="Sam", role="admin")
    first = fresh.get("/setup/telegram").text
    assert "https://t.me/BotFather" in first and "/newbot" in first
    # Her name will do, since the bot's contact follows it once connected.
    assert "<em>Vera</em> will do. Once the bot is connected" in " ".join(first.split())

    _post(fresh, "telegram", "/settings/keys", telegram_bot_token="7123:AAH-token")
    connecting = fresh.get("/setup/telegram").text
    assert "Connecting to Telegram" in connecting
    assert 'http-equiv="refresh" content="4;url=/setup/telegram?wait=1"' in connecting
    tired = fresh.get("/setup/telegram?wait=45").text
    assert "http-equiv" not in tired and "Nothing has been heard from Telegram yet" in tired

    # The bot's own thread says it connected; somebody then messages it from a phone.
    app.channel_states["telegram"] = "connected as @tate_family_bot"
    waiting = fresh.get("/setup/telegram").text
    assert "https://t.me/tate_family_bot" in waiting and "Waiting for your message" in waiting
    with db.transaction(conn):
        knocks.record(
            conn,
            channel="telegram",
            channel_user_id="555",
            name="Sam Tate @samt",
            chat_id="555",
            now=fresh.app.clock.now(),
        )
    arrived = fresh.get("/setup/telegram").text
    assert "That\u2019s me, Sam" in arrived and "http-equiv" not in arrived
    sam = re.search(r'action="(/family/\d+/telegram)"', arrived).group(1)

    linked = _post(fresh, "telegram", sam, telegram_id="555")
    assert linked.headers["Location"] == "/setup/telegram"
    page = fresh.get("/setup/telegram").text
    assert "The bot knows Sam on Telegram now" in page
    assert "✓ @tate_family_bot, and it knows Sam." in page

    # And the weekend ideas can follow them there.
    _post(fresh, "telegram", "/settings", digest_chat_id="555")
    assert app.settings.digest_chat_id == "555"


def test_the_weekend_ideas_are_offered_by_the_day_they_come(fresh, conn) -> None:
    with db.transaction(conn):
        members.add(conn, "Sam", "admin", channel="telegram", channel_user_id="555", now=NOW_ISO)
        settings_store.set_many(
            conn,
            {"telegram_bot_token": "7123:AAH-token", "digest_chat_id": "web", "digest_day": "sat"},
        )
    fresh.app.channel_states["telegram"] = "connected as @tate_family_bot"
    page = " ".join(fresh.get("/setup/telegram").text.split())
    assert "Every Saturday FamilyDB sends ideas for the weekend" in page


def test_the_bot_is_named_for_whoever_speaks(fresh, conn) -> None:
    """The running bot gives its Telegram contact the name it goes by: hers, the one the family
    call her included, or FamilyDB under none. So the step says that name will do."""
    _post(fresh, "you", "/family", name="Sam", role="admin")
    with db.transaction(conn):
        settings_store.set_many(conn, {"persona_name": "Juno"})
    said = " ".join(fresh.get("/setup/telegram").text.split())
    assert "<em>Juno</em> will do. Once the bot is connected, its name in Telegram follows" in said
    assert "follows hers, and changes with it if you rename her under Personality." in said
    assert "The Tates" not in said and "what it calls itself" not in said

    with db.transaction(conn):
        settings_store.set_many(conn, {"persona": "none"})
    said = " ".join(fresh.get("/setup/telegram").text.split())
    assert "<em>FamilyDB</em> will do. Once the bot is connected, its name in Telegram" in said
    assert "follows what it calls itself, and becomes hers if you choose a persona" in said
    assert "The Tates" not in said and "follows hers" not in said


def test_the_last_page_says_who_answers(fresh, conn) -> None:
    said = " ".join(fresh.get("/setup/done").text.split())
    assert (
        "Vera is who answers. Her name, how she talks, or no persona at all are chosen under "
        '<a href="/settings/personality">Personality</a>.'
    ) in said

    with db.transaction(conn):
        settings_store.set_many(conn, {"persona": "none"})
    said = " ".join(fresh.get("/setup/done").text.split())
    assert (
        "It answers plainly, with no persona. One can be chosen under "
        '<a href="/settings/personality">Personality</a>.'
    ) in said
    assert "who answers" not in said


def test_the_family_step_lets_in_whoever_messaged_the_bot(fresh, conn) -> None:
    _post(fresh, "you", "/family", name="Sam", role="admin")
    fresh.app.channel_states["telegram"] = "connected as @tate_family_bot"
    with db.transaction(conn):
        knocks.record(
            conn,
            channel="telegram",
            channel_user_id="777",
            name="Alex",
            chat_id="777",
            now=fresh.app.clock.now(),
        )
    page = fresh.get("/setup/family").text
    assert "Waiting to be let in" in page and "t.me/tate_family_bot" in page
    _post(fresh, "family", "/family", name="Alex", role="parent", telegram_id="777")
    page = fresh.get("/setup/family").text
    assert "Alex is on the family list." in page and "Waiting to be let in" not in page
    assert "✓ 2 on the list." in page


def test_the_calendar_step_explains_google_and_reports_a_bad_paste(fresh) -> None:
    page = fresh.get("/setup/calendar").text
    assert "console.cloud.google.com/auth/clients" in page and "Publish app" in page
    back = _post(fresh, "calendar", "/settings/google/start", client="not json at all")
    assert back.headers["Location"] == "/setup/calendar"
    assert 'class="error" role="alert"' in fresh.get("/setup/calendar").text


def test_a_form_can_only_ask_to_come_back_to_a_setup_page(fresh) -> None:
    data = {**_tokens(fresh, "/setup/you"), "name": "Sam", "role": "admin"}
    elsewhere = fresh.post("/family", data={**data, "then": "https://evil.example/setup"})
    assert elsewhere.headers["Location"] == "/family"
    sideways = fresh.post(
        "/settings", data={**_tokens(fresh, "/setup/home"), "then": "/family", "home_area": "X"}
    )
    assert sideways.headers["Location"] == "/settings"


def test_once_ready_the_home_page_lists_what_was_left_for_later(settings, clock, conn, family):
    app = App(settings.model_copy(update={"web_password": INSTALLERS}), clock)
    client = create_app(app).test_client()
    client.post("/login", data={"password": INSTALLERS})
    text = client.get("/").text
    assert "Finish setting up" in text
    assert 'href="/setup/home"' in text and 'href="/setup/calendar"' in text
    assert 'href="/setup/model"' not in text  # the test settings have a key


def test_nothing_on_a_setup_page_writes(settings, clock, conn) -> None:
    """Drawing every step changes nothing: no row, no setting."""
    app = App(settings, clock)
    client = create_app(app).test_client()
    before = conn.total_changes
    for name in ("", "/password", "/you", "/model", "/home", "/telegram", "/family", "/calendar"):
        assert client.get(f"/setup{name}").status_code == 200
    assert client.get("/setup/done").status_code == 200
    assert conn.total_changes == before
