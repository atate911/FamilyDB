"""The settings pages: the one part of the web surface that writes settings."""

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
    found = re.search(r'name="csrf" value="([^"]+)"', client.get("/settings/general").text)
    assert found is not None
    return found.group(1)


def _whole_form(client, **changes) -> dict[str, str]:
    """Every box on every page, empty, with the given ones filled in, and no page named: what an
    older page, drawn as one form, sends."""
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
    assert (
        "Saved. Changed: Company that answers, Weekend ideas time, Look ideas up on the web."
        in (after)
    )
    assert '<label for="model-key">Google key</label>' in page.get("/settings/model").text
    assert 'value="19" selected' in page.get("/settings/messages").text


def test_emptying_a_box_goes_back_to_the_environment(page, conn) -> None:
    page.post("/settings", data=_whole_form(page, web_title="The Tate family"))
    assert page.app.settings.web_title == "The Tate family"
    page.post("/settings", data=_whole_form(page))
    assert settings_store.overrides(conn) == {}
    assert page.app.settings.web_title == "FamilyDB"


def test_a_value_the_setting_will_not_take_is_refused_on_its_own_box(page, conn) -> None:
    refused = page.post("/settings", data=_whole_form(page, enrich_batch="seven"))
    assert refused.status_code == 400
    assert "That needs to be a whole number." in _errors(refused.text)
    assert 'value="seven"' in refused.text  # what was typed comes back, not a blank box
    # On the page the box is on, with its folded group opened so the complaint is in sight.
    assert "<h1>Lookups</h1>" in refused.text
    assert '<details class="panel fold" id="pace" open>' in refused.text

    refused = page.post("/settings", data=_whole_form(page, enrich_batch=99))
    assert refused.status_code == 400
    assert "Input should be less than or equal to 20" in _errors(refused.text)
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

    for path in ("/settings", "/settings/model", "/settings/security"):
        assert "sk-secret-value" not in page.get(path).text
    text = page.get("/settings/history").text
    assert "OpenAI key</strong>" in text and "replaced" in text
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
    assert "sk-shown-once" not in page.get("/settings/security").text  # once, not from then on


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
    text = page.get("/settings/history").text
    assert "Chat thinking</strong>" in text  # by the name on the page, not the setting's
    assert "default → High" in text
    assert "Sam" in text and "cli" in text
    assert "Last: Chat thinking" in page.get("/settings").text


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
    text = client.get("/settings/security").text
    assert "This page has no password" in text
    assert 'id="reveal-password"' not in text  # nothing to type to see a key
    token = re.search(r'name="csrf" value="([^"]+)"', text).group(1)
    shown = client.post("/settings/reveal", data={"csrf": token, "key": "openai_api_key"})
    assert shown.status_code == 200 and "sk-home" in shown.text


def test_a_model_box_offers_models_without_limiting_them(page) -> None:
    """A dropdown of the company's models, each with what it is, and "Another model" opening a
    box to type one the list does not have: a model released next week has to fit."""
    text = page.get("/settings/model").text
    assert _choices(text, "openai_model")[0] == "Default (gpt-6-luna)"
    assert "gpt-6-luna · GPT-6 Luna, everyday · $0.10 in, $0.50 out" in _choices(
        text, "openai_model"
    )
    assert _choices(text, "openai_model")[-1] == "Another model…"
    assert '<input id="a-openai_model" name="openai_model_another"' in text
    page.post("/settings", data=_whole_form(page, openai_model="gpt-6-sol"))
    assert page.app.settings.openai_model == "gpt-6-sol"
    assert '<option value="gpt-6-sol" selected>' in page.get("/settings/model").text

    # Another, typed: taken, and shown again as typed, with "Another" chosen.
    typed = _whole_form(page, openai_model="another", openai_model_another="gpt-7-nova")
    page.post("/settings", data=typed)
    assert page.app.settings.openai_model == "gpt-7-nova"
    text = page.get("/settings/model").text
    assert '<option value="another" selected>Another model…</option>' in text
    assert 'name="openai_model_another" type="text" autocomplete="off"' in text
    assert 'value="gpt-7-nova"' in text
    # What was typed under a list that did not say "Another" is not read.
    page.post("/settings", data=_whole_form(page, openai_model="", openai_model_another="x"))
    assert page.app.settings.openai_model == "gpt-6-luna"


def _choices(text: str, key: str) -> list[str]:
    """What one dropdown offers, as it reads."""
    found = re.search(rf'<select id="f-{key}"[^>]*>(.*?)</select>', text, re.S)
    assert found is not None
    return [" ".join(one.split()) for one in re.findall(r">([^<]+)</option>", found.group(1))]


def test_each_level_says_which_model_it_means_and_what_it_costs(page) -> None:
    # The fixture's everyday Claude is Opus: a level up never answers with a cheaper model.
    assert _choices(page.get("/settings/model").text, "chat_level")[1:] == [
        "everyday: Claude Opus 5 ($5.00 in, $25.00 out)",
        "better: Claude Opus 5 ($5.00 in, $25.00 out)",
        "best: Claude Opus 5 ($5.00 in, $25.00 out)",
    ]
    page.post("/settings", data=_whole_form(page, provider="openai", digest_level="best"))
    assert page.app.settings.digest_level == "best"
    text = page.get("/settings/model").text
    assert _choices(text, "digest_level")[1:] == [
        "everyday: GPT-6 Luna ($0.10 in, $0.50 out)",
        "better: GPT-6 Sol ($2.00 in, $10.00 out)",
        "best: GPT-6 Astra ($10.00 in, $50.00 out)",
    ]
    assert '<option value="best" selected>best: GPT-6 Astra' in text
    # A model box says where each name stands, and what it costs.
    assert "gpt-6-sol · GPT-6 Sol, better · $2.00 in, $10.00 out" in _choices(text, "openai_model")
    assert "gpt-5 · $1.25 in, $10.00 out" in _choices(text, "openai_model")


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


def _ask(monkeypatch, company: _Company) -> None:
    """OpenAI's answer about a model name comes from `company`; the rest of it is as it is."""
    from familydb.agent.providers.openai import OpenAIProvider

    monkeypatch.setattr(
        OpenAIProvider, "model_exists", lambda self, model: company.model_exists(model)
    )


def test_a_model_the_company_does_not_have_is_refused(page, monkeypatch) -> None:

    company = _Company({"gpt-6-luna"})
    _ask(monkeypatch, company)
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


def test_a_hearing_model_is_offered_and_checked_like_the_other_models(page, monkeypatch) -> None:
    """Each with what it costs, by the minute for one billed so, and a name its company does not
    have is refused, as every voice note would otherwise go unheard."""
    text = page.get("/settings/model").text
    offered = _choices(text, "openai_transcribe_model")
    assert "whisper-1 · $0.006 a minute" in offered
    assert "gpt-4o-mini-transcribe · $1.25 in, $5.00 out" in offered
    _ask(monkeypatch, _Company({"gpt-4o-mini-transcribe"}))
    typo = _whole_form(page, openai_transcribe_model="gpt-4o-mini-transcrib")
    response = page.post("/settings", data=typo)
    assert response.status_code == 400
    assert "OpenAI says it has no model called gpt-4o-mini-transcrib. Check the spelling." in (
        _errors(response.text)
    )
    assert page.app.settings.openai_transcribe_model == "gpt-4o-mini-transcribe"


def test_a_company_that_cannot_be_asked_does_not_block_a_save(page, monkeypatch) -> None:

    _ask(monkeypatch, _Company(None))
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
    from contextlib import closing

    from familydb.web.auth import known_device

    cookie = f"{DEVICE_COOKIE}={other.get_cookie(DEVICE_COOKIE).value}"
    with (
        closing(page.app.connect()) as conn,
        page.application.test_request_context("/login", headers={"Cookie": cookie}),
    ):
        assert not known_device(conn, page.app.settings, personal=False)


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


def test_the_timezone_is_chosen_from_a_list_by_region(page) -> None:
    """A dropdown of the standard zones, under the region each is named for, each read as its
    place and its offset at the moment the page is drawn (the test clock's September)."""
    general = page.get("/settings/general").text
    assert '<select id="f-family_tz" name="family_tz"' in general
    assert 'name="family_tz" type="text"' not in general  # nothing to type, or to mistype
    headings = re.findall(r'<optgroup label="([^"]+)">', general)
    assert headings[:3] == ["Africa", "Americas", "Antarctica"] and headings[-1] == "Other"
    assert (
        '<option value="America/Argentina/Buenos_Aires">Buenos Aires, Argentina · UTC-03:00'
        "</option>" in general
    )
    assert '<option value="Asia/Kolkata">Kolkata · UTC+05:30</option>' in general
    assert '<option value="UTC">UTC</option>' in general
    # With nothing stored, the first choice says what the server's own zone gives, in those words.
    assert '<option value="">Default (Vancouver · UTC-07:00)</option>' in general
    page.post("/settings", data=_whole_form(page, family_tz="Europe/London"))
    chosen = page.get("/settings/general").text
    assert '<option value="Europe/London" selected>London · UTC+01:00</option>' in chosen


def test_a_zone_the_list_does_not_offer_is_kept_by_a_save(page, conn) -> None:
    """A zone stored before the list, or typed into an older page, stays chosen, so saving the
    page as it is drawn never quietly puts the default back."""
    with db.transaction(conn):
        settings_store.set_many(conn, {"family_tz": "US/Pacific"}, source="test")
    page.app.refresh()
    general = page.get("/settings/general").text
    assert '<option value="US/Pacific" selected>US/Pacific</option>' in general
    saved = page.post("/settings", data=_as_drawn(general))
    assert saved.status_code == 302
    assert settings_store.overrides(conn)["family_tz"] == "US/Pacific"
    assert page.app.settings.tz == "US/Pacific"


def _as_drawn(text: str) -> dict[str, str]:
    """What a browser sends for the settings form on a page, untouched: each box's value, and
    each dropdown's chosen option, or its first when none is chosen."""
    from html.parser import HTMLParser

    class Form(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.sent: dict[str, str] = {}
            self.inside = False
            self.select: str | None = None

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            found = {key: value or "" for key, value in attrs}
            if tag == "form":
                self.inside = found.get("action") == "/settings"
            elif not self.inside:
                return
            elif tag == "input" and found.get("type") != "checkbox" and "name" in found:
                self.sent[found["name"]] = found.get("value", "")
            elif tag == "select":
                self.select = found["name"]
            elif (
                tag == "option"
                and self.select is not None
                and (self.select not in self.sent or "selected" in found)
            ):
                self.sent[self.select] = found.get("value", "")

        def handle_endtag(self, tag: str) -> None:
            if tag == "select":
                self.select = None
            elif tag == "form":
                self.inside = False

    form = Form()
    form.feed(text)
    return form.sent


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
        r'<select id="f-digest_chat_id"[^>]*>(.*?)</select>',
        page.get("/settings/messages").text,
        re.S,
    )
    assert offers is not None
    listed = offers.group(1)
    assert 'value="web"' in listed and 'value="-100200">Telegram group' in listed
    assert "private chat with Sam" in listed and "hello" not in listed


# -- one page for each part


def _drawn(text: str) -> set[str]:
    """The settings a page's forms carry, by the names its boxes post."""
    return {key for key in BEHAVIOUR if f'name="{key}"' in text}


def test_every_setting_is_on_exactly_one_page_and_the_right_one(page) -> None:
    """Split into pages, a setting could fall between them, or turn up on two and be saved twice."""
    found: dict[str, list[str]] = {}
    for section in fields.SECTIONS:
        response = page.get(f"/settings/{section.name}")
        assert response.status_code == 200, section.name
        for key in _drawn(response.text):
            found.setdefault(key, []).append(section.name)
    assert sorted(found) == sorted(BEHAVIOUR)
    assert {key: pages for key, pages in found.items() if len(pages) > 1} == {}
    assert {key: pages[0] for key, pages in found.items()} == fields.SECTION_OF


def test_a_page_that_is_not_one_is_not_found(page) -> None:
    assert page.get("/settings/everything").status_code == 404


def test_a_page_s_form_comes_back_to_that_page(page, conn) -> None:
    form = {"csrf": _token(page), "section": "lookups", "web_tools_enabled": "true"}
    saved = page.post("/settings", data=form)
    assert saved.status_code == 302 and saved.headers["Location"] == "/settings/lookups"
    after = page.get("/settings/lookups").text
    assert "Saved. Changed: Look ideas up on the web." in after
    assert '<span class="changed">changed</span>' in after  # set here, not the default
    # Only the boxes the form carried were touched: every other page's are left alone.
    assert settings_store.overrides(conn) == {"web_tools_enabled": True}


def test_a_complaint_from_a_page_is_drawn_on_that_page(page, conn) -> None:
    form = {"csrf": _token(page), "section": "spending", "history_hours": "a while"}
    refused = page.post("/settings", data=form)
    assert refused.status_code == 400 and "<h1>Spending</h1>" in refused.text
    assert "That needs to be a number." in _errors(refused.text)
    assert '<details class="panel fold" id="each" open>' in refused.text
    assert settings_store.overrides(conn) == {}


def test_keys_come_back_to_the_page_they_were_saved_on(page, conn) -> None:
    ai = {"csrf": _token(page), "section": "model", "gemini_api_key": "gm-spare"}
    assert page.post("/settings/keys", data=ai).headers["Location"] == "/settings/model"
    bot = {"csrf": _token(page), "section": "connections", "telegram_bot_token": "7123:AA"}
    assert page.post("/settings/keys", data=bot).headers["Location"] == "/settings/connections"
    assert settings_store.get(conn, "telegram_bot_token") == "7123:AA"
    refused = page.post(
        "/settings/keys", data={"csrf": _token(page), "telegram_bot_token": "7123: AA"}
    )
    assert refused.status_code == 400 and "<h1>Connections</h1>" in refused.text


def test_a_phone_is_offered_the_keyboard_each_box_needs(page) -> None:
    general = page.get("/settings/general").text
    # A longitude may be negative, and a phone's number pads have no minus sign.
    assert re.search(r'name="home_lon"[^>]*inputmode', general) is None
    assert re.search(r'name="road_factor"[^>]*inputmode="decimal"', general)
    assert re.search(
        r'name="enrich_batch"[^>]*inputmode="numeric"', page.get("/settings/lookups").text
    )


def test_a_zone_reads_as_its_place_and_its_offset_that_day() -> None:
    from datetime import UTC, datetime

    from familydb.web.views import utc_offset, zone_groups, zone_label

    summer = datetime(2026, 7, 1, 12, tzinfo=UTC)
    winter = datetime(2026, 1, 15, 12, tzinfo=UTC)
    assert zone_label("America/Vancouver", summer) == "Vancouver · UTC-07:00"
    assert zone_label("America/Vancouver", winter) == "Vancouver · UTC-08:00"
    assert zone_label("America/Indiana/Indianapolis", winter) == "Indianapolis, Indiana · UTC-05:00"
    assert utc_offset("Asia/Kathmandu", winter) == "UTC+05:45"
    assert utc_offset("Europe/London", winter) == "UTC+00:00"
    assert zone_label("UTC", winter) == "UTC"
    groups = dict(zone_groups(["Europe/Paris", "UTC", "America/Toronto", "America/Denver"], winter))
    assert list(groups) == ["Americas", "Europe", "Other"]
    assert [zone for zone, _ in groups["Americas"]] == ["America/Denver", "America/Toronto"]


def test_behind_caddy_it_says_how_to_move_the_address_people_open(settings, clock, conn, family):
    app = App(
        settings.model_copy(update={"web_password": PASSWORD, "web_trust_proxy": True}), clock
    )
    client = create_app(app).test_client()
    # Signed in where the page is, since behind a proxy the sign-in cookie is sent on HTTPS only.
    opened = "https://203.0.113.7:24613"
    client.post("/login", data={"password": PASSWORD}, base_url=opened)
    served = client.get("/settings/general", base_url=opened).text
    assert "<code>https://203.0.113.7:24613/</code>, on port 24613" in served
    assert "and the page is passed on to it by Caddy" in served
    assert "https --port random</code> serves the page on a port" in served
    assert "The address people open stays as it is." in served


def test_the_connections_page_says_what_the_bot_can_read_in_a_group(page) -> None:
    app = page.app
    unknown = page.get("/settings/connections").text
    assert "Answer only when mentioned" in unknown and "privacy setting" not in unknown
    app.channel_states["telegram"] = "connected as @tate_family_bot"
    app.channel_facts["telegram"] = {"reads_groups": False}
    shy = " ".join(page.get("/settings/connections").text.split())
    assert "In a group it sees only a message that mentions it or replies to it" in shy
    assert "choose @tate_family_bot, then <em>Disable</em>" in shy
    app.channel_facts["telegram"] = {"reads_groups": True}
    reads = page.get("/settings/connections").text
    assert "It reads every message in the groups it is in." in reads
    saved = page.post(
        "/settings",
        data={"csrf": _token(page), "section": "connections", "telegram_require_mention": "true"},
    )
    assert saved.headers["Location"] == "/settings/connections"
    assert app.settings.telegram_require_mention is True
    assert app.settings.google_calendar_id is None  # the other form's box, left alone


def test_the_messages_page_says_what_goes_out_unasked_and_how_often(page, conn) -> None:
    from familydb.store import messages

    with db.transaction(conn):
        asked = messages.insert_out(
            conn,
            channel="telegram",
            chat_id="-100",
            text="How was Hopscotch on Saturday?",
            now="2026-09-19T17:00:00Z",
            sent_as="follow_up",
        )
        messages.mark_delivered(conn, [asked.id], now="2026-09-19T17:00:01Z")
        messages.insert_out(
            conn, channel="web", chat_id="web", text="An answer", now="2026-09-20T21:00:00Z"
        )
    text = page.get("/settings/messages").text
    listed = re.search(r'<section class="panel" id="on-her-own">.*?</section>', text, re.S)
    assert listed is not None
    shown = " ".join(listed.group(0).split())
    assert "How did it go?" in shown and "1 sent in 30 days, the last 19 Sep, 10:00." in shown
    assert "Weekend ideas" in shown and "Nowhere chosen, so none is sent" in shown
    assert "Costs: one model call a week." in shown and '<a href="#others">Change</a>' in shown
    assert "How was Hopscotch on Saturday?" in shown and "a Telegram group" in shown
    assert "An answer" not in shown  # a reply is not hers unasked
    # And the switch for it is on the same page.
    page.post("/settings", data=_whole_form(page, follow_ups="false"))
    assert page.app.settings.follow_ups is False
    assert 'How did it go?</strong> <span class="tag">off</span>' in " ".join(
        page.get("/settings/messages").text.split()
    )


def test_the_general_page_says_how_to_give_the_page_a_name(page) -> None:
    from familydb.web.settings import reached_by

    text = page.get("/settings/general").text
    assert "A name for the page" in text and "family.example.com" in text
    assert "https family.example.com</code>" in text  # the example until a name is typed

    named = page.get("/settings/general?domain=Family.Tates.ORG.").text
    assert "https family.tates.org</code>" in named and "dig +short family.tates.org" in named
    assert "WEB_DOMAIN=family.tates.org" in named  # the Docker way too

    refused = page.get("/settings/general?domain=<script>alert(1)</script>").text
    assert "That is not a name that can be pointed at a server" in refused
    assert "<script>alert" not in refused and "https family.example.com</code>" in refused

    assert reached_by("93.184.216.34") == "public"
    assert reached_by("192.168.1.20") == "private"
    assert reached_by("127.0.0.1") == "local" and reached_by("localhost") == "local"
    assert reached_by("family.example.com") == "name"
