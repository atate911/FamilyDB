"""The settings page: the one part of the web surface that writes."""

from __future__ import annotations

import re

import pytest

from familydb.app import App
from familydb.store import db
from familydb.store import settings as settings_store
from familydb.store.settings import BEHAVIOUR, SECRETS
from familydb.web import create_app, fields

PASSWORD = "open sesame please"


@pytest.fixture
def page(settings, clock, conn, family):
    """A signed-in client on a database the test can also reach through `conn`."""
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    client.app = app  # the test looks at what the page put in force
    return client


def _token(client) -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get("/settings").text)
    assert found is not None
    return found.group(1)


def _whole_form(client, **changes) -> dict[str, str]:
    """Every box on the page, empty, with the given ones filled in: what a browser sends."""
    form = {one.key: "" for one in fields.FIELDS}
    form["csrf"] = _token(client)
    form.update({key: str(value) for key, value in changes.items()})
    return form


def _errors(text: str) -> list[str]:
    return [one.strip() for one in re.findall(r'class="error" role="alert">\s*([^<]+)', text)]


def test_the_page_offers_every_setting_that_can_be_stored() -> None:
    """A setting the store accepts but the page never shows would be unreachable."""
    shown = [one.key for one in fields.FIELDS]
    assert sorted(shown) == sorted(BEHAVIOUR)
    assert len(shown) == len(set(shown))
    assert not set(shown) & set(SECRETS)  # keys have their own form, and are never echoed


def test_a_box_left_empty_says_what_it_falls_back_to(page) -> None:
    text = page.get("/settings").text
    assert "From the environment (anthropic)" in text  # the provider dropdown
    assert "Between 0 and 23." in text  # read off the setting, not written out twice
    assert 'placeholder="claude-opus-5"' in text


def test_saving_puts_it_in_force_at_once(page, conn) -> None:
    form = _whole_form(page, provider="gemini", digest_hour=19, web_tools_enabled="true")
    saved = page.post("/settings", data=form)
    assert saved.status_code == 302 and saved.headers["Location"] == "/settings"
    assert settings_store.overrides(conn) == {
        "provider": "gemini",
        "digest_hour": 19,
        "web_tools_enabled": True,
    }
    assert page.app.settings.provider == "gemini"  # no restart, no wait
    after = page.get("/settings").text
    # In the words on the page, not the setting names.
    assert "Saved. Changed: Chat model company, Look ideas up on the web, Digest hour." in after
    assert 'value="gemini" selected' in after


def test_emptying_a_box_goes_back_to_the_environment(page, conn) -> None:
    page.post("/settings", data=_whole_form(page, web_title="The Tate family"))
    assert page.app.settings.web_title == "The Tate family"
    page.post("/settings", data=_whole_form(page))
    assert settings_store.overrides(conn) == {}
    assert page.app.settings.web_title == "FamilyDB"


def test_a_value_the_setting_will_not_take_is_refused_on_its_own_box(page, conn) -> None:
    refused = page.post("/settings", data=_whole_form(page, digest_hour="seven"))
    assert refused.status_code == 400
    assert "That needs to be a whole number." in _errors(refused.text)
    assert 'value="seven"' in refused.text  # what was typed comes back, not a blank box

    refused = page.post("/settings", data=_whole_form(page, digest_hour=99))
    assert refused.status_code == 400
    assert "Input should be less than or equal to 23" in _errors(refused.text)
    assert settings_store.overrides(conn) == {}  # and not one box was written


def test_a_form_without_this_session_s_token_is_refused(page, conn) -> None:
    form = _whole_form(page, provider="gemini")
    stale = page.post("/settings", data={**form, "csrf": "made up"})
    assert stale.status_code == 400
    assert "too old to use" in stale.text  # not "from another site": it was not
    assert settings_store.overrides(conn) == {}
    no_token = page.post("/settings", data={key: "" for key in form})
    assert no_token.status_code == 400
    elsewhere = page.post(
        "/settings", data=form, headers={"Origin": "https://not-this-page.example"}
    )
    assert elsewhere.status_code == 400
    assert "did not come from this page" in elsewhere.text
    for path in ("/settings/keys", "/settings/reveal"):
        assert page.post(path, data={"csrf": "made up"}).status_code == 400


def test_a_key_is_stored_but_never_shown_and_never_logged(page, conn) -> None:
    stored = page.post(
        "/settings/keys", data={"csrf": _token(page), "openai_api_key": "sk-secret-value"}
    )
    assert stored.status_code == 302
    assert settings_store.get(conn, "openai_api_key") == "sk-secret-value"
    assert page.app.settings.openai_api_key == "sk-secret-value"

    text = page.get("/settings").text
    assert "sk-secret-value" not in text
    assert "openai_api_key</strong>" in text and "replaced" in text
    line = settings_store.history(conn)[0]
    assert line["secret"] == 1 and line["old_value"] is None and line["new_value"] is None
    assert line["source"].startswith("web ")


def test_a_blank_key_box_leaves_the_key_alone(page, conn) -> None:
    page.post("/settings/keys", data={"csrf": _token(page), "gemini_api_key": "gm-1"})
    page.post("/settings/keys", data={"csrf": _token(page), "gemini_api_key": "  "})
    assert settings_store.get(conn, "gemini_api_key") == "gm-1"
    page.post("/settings/keys", data={"csrf": _token(page), "remove_gemini_api_key": "1"})
    assert settings_store.get(conn, "gemini_api_key") is None


def test_a_key_that_was_pasted_wrong_is_refused(page, conn) -> None:
    refused = page.post(
        "/settings/keys", data={"csrf": _token(page), "openai_api_key": "API key: sk-abc"}
    )
    assert refused.status_code == 400
    assert "A key has no spaces in it. Check what was pasted." in _errors(refused.text)
    assert settings_store.get(conn, "openai_api_key") is None


def test_seeing_a_key_needs_the_password_again(page, conn) -> None:
    page.post("/settings/keys", data={"csrf": _token(page), "openai_api_key": "sk-shown-once"})
    token = _token(page)

    without = page.post("/settings/reveal", data={"csrf": token, "key": "openai_api_key"})
    assert without.status_code == 400 and "sk-shown-once" not in without.text

    wrong = page.post(
        "/settings/reveal", data={"csrf": token, "key": "openai_api_key", "password": "guess"}
    )
    assert wrong.status_code == 401 and "sk-shown-once" not in wrong.text

    shown = page.post(
        "/settings/reveal", data={"csrf": token, "key": "openai_api_key", "password": PASSWORD}
    )
    assert shown.status_code == 200 and "sk-shown-once" in shown.text
    assert shown.headers["Cache-Control"] == "no-store"
    assert "sk-shown-once" not in page.get("/settings").text  # once, not from then on


def test_guessing_at_the_reveal_never_shuts_the_family_out(page) -> None:
    token = _token(page)
    for _ in range(5):
        page.post(
            "/settings/reveal", data={"csrf": token, "key": "openai_api_key", "password": "no"}
        )
    locked = page.post(
        "/settings/reveal", data={"csrf": token, "key": "openai_api_key", "password": PASSWORD}
    )
    assert locked.status_code == 429
    assert page.get("/settings").status_code == 200  # the page itself is still theirs
    assert page.post("/logout").status_code == 302
    assert page.post("/login", data={"password": PASSWORD}).status_code == 302


def test_a_key_nobody_named_is_not_a_key(page) -> None:
    refused = page.post(
        "/settings/reveal",
        data={"csrf": _token(page), "key": "web_password", "password": PASSWORD},
    )
    assert refused.status_code == 400 and PASSWORD not in refused.text


def test_the_history_shows_what_moved_and_who_moved_it(page, conn, family) -> None:
    with db.transaction(conn):
        settings_store.set_many(conn, {"effort": "high"}, changed_by=family["sam"].id, source="cli")
    text = page.get("/settings").text
    assert "effort</strong>" in text
    assert "from the environment → high" in text
    assert "Sam" in text and "cli" in text


def test_a_setting_cannot_be_reached_through_the_form_unless_the_page_offers_it(page, conn) -> None:
    """A crafted post naming something else changes nothing: only the boxes are read."""
    form = _whole_form(page, provider="gemini")
    form["web_password"] = "changed from the page"
    form["familydb_path"] = "/tmp/elsewhere.sqlite3"
    assert page.post("/settings", data=form).status_code == 302
    assert set(settings_store.overrides(conn)) == {"provider"}
    assert page.app.settings.web_password == PASSWORD


def test_a_visitor_who_is_not_signed_in_cannot_make_the_page_do_work(
    settings, clock, conn, monkeypatch
):
    """The gate runs first, so an unsigned request costs a refusal and not one query."""
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    asked = []
    real = settings_store.stamp
    monkeypatch.setattr(settings_store, "stamp", lambda conn: (asked.append(1), real(conn))[1])

    assert client.get("/settings").status_code == 302
    assert client.get("/healthz").status_code == 200
    assert asked == []
    client.post("/login", data={"password": PASSWORD})
    asked.clear()
    assert client.get("/settings").status_code == 200
    assert len(asked) == 1  # signed in, so the page is served from the settings in force
    assert client.get("/healthz").status_code == 200
    assert len(asked) == 1  # and a liveness check still never asks


def test_a_page_with_no_password_shows_a_key_to_whoever_can_reach_it(settings, clock, conn):
    """The relaxed home posture: there is no second password to ask for, and the page says so."""
    app = App(settings.model_copy(update={"openai_api_key": "sk-home"}), clock)
    client = create_app(app).test_client()
    text = client.get("/settings").text
    assert "This page has no password" in text
    assert 'id="reveal-password"' not in text  # nothing to type to see a key
    token = re.search(r'name="csrf" value="([^"]+)"', text).group(1)
    shown = client.post("/settings/reveal", data={"csrf": token, "key": "openai_api_key"})
    assert shown.status_code == 200 and "sk-home" in shown.text


def test_a_model_box_suggests_models_without_limiting_them(page) -> None:
    text = page.get("/settings").text
    assert 'list="s-openai_model"' in text
    assert '<datalist id="s-openai_model">' in text and '<option value="gpt-6-luna">' in text
    # Anything typed is still taken: a model released next week has to fit.
    page.post("/settings", data=_whole_form(page, openai_model="gpt-6-sol"))
    assert page.app.settings.openai_model == "gpt-6-sol"


def test_the_daily_limit_is_on_the_page(page) -> None:
    page.post("/settings", data=_whole_form(page, daily_spend_limit="0.5"))
    assert page.app.settings.daily_spend_limit == 0.5
    assert "of the $0.50 daily limit" in page.get("/status").text


class _Company:
    """Stands in for a provider, answering only the question the settings page asks."""

    def __init__(self, known: set[str] | None) -> None:
        self.known = known
        self.asked: list[str] = []

    def model_exists(self, model: str) -> bool | None:
        self.asked.append(model)
        return None if self.known is None else model in self.known


def test_a_model_the_company_does_not_have_is_refused(page, monkeypatch) -> None:
    from familydb.web import settings as settings_view

    company = _Company({"gpt-6-luna"})
    monkeypatch.setattr(settings_view.providers, "build", lambda name, settings: company)
    response = page.post("/settings", data=_whole_form(page, openai_model="gpt-6-lunar"))
    assert response.status_code == 400
    assert "OpenAI says it has no model called gpt-6-lunar. Check the spelling." in _errors(
        response.text
    )
    assert page.app.settings.openai_model == "gpt-6-luna"
    # A save that leaves the model alone does not ask again.
    company.asked.clear()
    page.post("/settings", data=_whole_form(page, effort="low"))
    assert company.asked == []


def test_a_company_that_cannot_be_asked_does_not_block_a_save(page, monkeypatch) -> None:
    from familydb.web import settings as settings_view

    monkeypatch.setattr(settings_view.providers, "build", lambda name, settings: _Company(None))
    page.post("/settings", data=_whole_form(page, openai_model="gpt-6-sol"))
    assert page.app.settings.openai_model == "gpt-6-sol"


def test_signing_everyone_out_ends_every_session_and_needs_the_password(page) -> None:
    from familydb.web.auth import DEVICE_COOKIE

    other = page.application.test_client()  # the same family on another phone
    assert other.post("/login", data={"password": PASSWORD}).status_code == 302
    assert other.get("/").status_code == 200

    refused = page.post(
        "/settings/sign-out-everyone", data={"csrf": _token(page), "password": "not it"}
    )
    assert refused.status_code == 401 and other.get("/").status_code == 200

    done = page.post(
        "/settings/sign-out-everyone", data={"csrf": _token(page), "password": PASSWORD}
    )
    assert done.status_code == 302 and done.headers["Location"] == "/login"
    assert other.get("/").status_code == 302  # signed out, with nothing done on that phone
    assert page.get("/").status_code == 302  # and this one too
    # The known-browser mark was signed with the old key, so it no longer spares anyone.
    from familydb.web.auth import known_device

    with page.application.test_request_context(
        "/login", headers={"Cookie": f"{DEVICE_COOKIE}={other.get_cookie(DEVICE_COOKIE).value}"}
    ):
        assert not known_device(page.app.settings)


def test_a_pinned_key_cannot_be_rotated_from_the_page(settings, clock, conn, family) -> None:
    pinned = settings.model_copy(
        update={"web_password": PASSWORD, "web_secret_key": "set in the environment file"}
    )
    client = create_app(App(pinned, clock)).test_client()
    client.post("/login", data={"password": PASSWORD})
    response = client.post(
        "/settings/sign-out-everyone", data={"csrf": _token(client), "password": PASSWORD}
    )
    assert response.status_code == 409 and "WEB_SECRET_KEY" in response.text


def test_the_timezone_is_set_on_the_page(page) -> None:
    page.post("/settings", data=_whole_form(page, family_tz="Europe/London"))
    assert page.app.settings.tz == "Europe/London"
    refused = page.post("/settings", data=_whole_form(page, family_tz="Mars/Olympus_Mons"))
    assert refused.status_code == 400 and page.app.settings.tz == "Europe/London"


def test_a_home_area_typed_on_the_page_is_found_on_the_map(settings, clock, conn, family) -> None:
    from familydb.integrations.geocode import GeoPoint
    from tests.fakes import FakeGeocoder

    point = GeoPoint(45.6387, -122.6615, "Vancouver, Washington", "nominatim")
    app = App(
        settings.model_copy(update={"web_password": PASSWORD}),
        clock,
        geocoder=FakeGeocoder(default=point),
    )
    client = create_app(app).test_client()
    client.post("/login", data={"password": PASSWORD})
    saved = client.post(
        "/settings", data=_whole_form(client, home_area="Vancouver, WA"), follow_redirects=True
    )
    assert "Found Vancouver, Washington" in saved.text
    assert (app.settings.home_lat, app.settings.home_lon) == (45.6387, -122.6615)
    # Coordinates typed by hand win over the map.
    client.post(
        "/settings",
        data=_whole_form(client, home_area="Portland, OR", home_lat="45.5", home_lon="-122.7"),
    )
    assert (app.settings.home_lat, app.settings.home_lon) == (45.5, -122.7)


def test_the_home_page_lists_what_is_left_to_set_up(page) -> None:
    text = page.get("/").text
    assert "Finish setting up" in text
    assert "Say where home is" in text and "Connect Google Calendar" in text
    assert "Give it a model key" not in text  # the test settings have one


def test_the_digest_chat_is_offered_from_the_chats_it_has_seen(page, conn) -> None:
    from familydb.store import messages

    with db.transaction(conn):
        for chat_id, update in (("-100200", "1"), ("1001", "2")):
            messages.insert_in(
                conn,
                channel="telegram",
                channel_update_id=update,
                chat_id=chat_id,
                member_id=None,
                text="hello",
                now="2026-09-20T10:00:00Z",
            )
    offers = re.search(
        r'<datalist id="s-digest_chat_id">(.*?)</datalist>', page.get("/settings").text, re.S
    )
    assert offers is not None
    listed = offers.group(1)
    assert 'value="web"' in listed and 'value="-100200">Telegram group' in listed
    assert "private chat with Sam" in listed and "hello" not in listed
