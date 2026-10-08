"""The AI model page: what it draws from the last 30 days of calls, and the one form that saves it
(docs/MODELS_PAGE.md)."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from html import unescape

import pytest

from familydb.agent import uses
from familydb.agent.providers import prices
from familydb.app import App
from familydb.config import CompanyDef, CompanyOptions
from familydb.dates import utc_iso
from familydb.store import calls
from familydb.store import settings as settings_store
from familydb.web import create_app, models_page

PASSWORD = "open sesame please"


@pytest.fixture
def keyed(settings):
    """Claude's key (the fixture's), OpenAI's, and OpenAI the company that answers."""
    return settings.model_copy(
        update={
            "web_password": PASSWORD,
            "model_watch": True,
            "openai_api_key": "sk-o",
            "provider": "openai",
            "choosing": True,
        }
    )


@pytest.fixture
def page(keyed, clock, conn, family):
    app = App(keyed, clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    client.app = app
    return client


def token(client) -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get("/settings/model").text)
    assert found is not None
    return found.group(1)


def post(client, **form):
    return client.post("/settings/models", data={"csrf": token(client), **form})


def data_of(client) -> dict:
    found = re.search(r"data-models='([^']*)'", client.get("/settings/model").text)
    assert found is not None
    return json.loads(unescape(found.group(1)))


def one(data: dict, use: str) -> dict:
    return next(each for each in data["uses"] if each["id"] == use)


def spend(conn, clock, kind, *, model="gpt-6-luna", provider="openai", days_ago=0, **usage):
    calls.log_llm_call(
        conn,
        message_id=None,
        iteration=1,
        model=model,
        served_model=None,
        request_id=None,
        stop_reason="end_turn",
        usage={"input_tokens": 1000, "output_tokens": 100, **usage},
        duration_ms=1,
        now=utc_iso(clock.now() - timedelta(days=days_ago)),
        provider=provider,
        cost_usd=0.01,
        kind=kind,
    )


# -- the numbers ---------------------------------------------------------------------------------


def test_a_use_is_priced_from_its_own_calls_at_every_model(page, conn, clock):
    for _ in range(4):
        spend(conn, clock, "chat", cache_read_input_tokens=9000)
    spend(conn, clock, "retry", days_ago=3)  # a retry is the chat's: one use
    chat = one(data_of(page), "chat")
    assert chat["calls"][-1] == 4 and chat["calls"][-4] == 1 and sum(chat["calls"]) == 5
    assert not chat["typical"]
    sol = next(o for o in chat["opts"] if (o["c"], o["n"]) == ("openai", "gpt-6-sol"))
    usage = {"input_tokens": 4000, "cache_read_input_tokens": 36000, "output_tokens": 400}
    usage_retry = {"input_tokens": 1000, "output_tokens": 100}
    expected = (
        prices.cost("openai", "gpt-6-sol", usage)[0]
        + prices.cost("openai", "gpt-6-sol", usage_retry)[0]
    )
    assert sol["m"] == pytest.approx(expected, abs=1e-4)
    assert sum(sol["d"]) == pytest.approx(sol["m"], abs=1e-3)  # the days add up to the month
    # A dearer model costs more for the same calls.
    luna = next(o for o in chat["opts"] if o["n"] == "gpt-6-luna")
    assert sol["m"] > luna["m"]


def test_a_use_with_no_calls_is_priced_at_a_typical_month_and_says_so(page, conn, clock):
    spend(conn, clock, "chat")
    data = data_of(page)
    assert one(data, "chat")["typical"] is False
    digest = one(data, "digest")
    assert digest["typical"] and digest["calls"] == [0] * 30
    assert max(o["m"] for o in digest["opts"]) > 0 and all(o["d"] == [] for o in digest["opts"])
    assert "No calls in the last 30 days, so costs here are a typical month" in _row(
        page.get("/settings/model").text, "digest"
    )


def test_calls_older_than_thirty_days_are_not_counted(page, conn, clock):
    spend(conn, clock, "chat", days_ago=45)
    assert one(data_of(page), "chat")["typical"]


def test_each_use_is_offered_only_the_models_that_can_do_it(page, keyed, conn, clock):
    from familydb.agent.providers import companies

    data = data_of(page)
    assert {o["c"] for o in one(data, "hear")["opts"]} == {
        "openai",
        "gemini",
    }  # Claude hears nothing
    assert {o["c"] for o in one(data, "chat")["opts"]} == {"openai", "anthropic", "gemini"}
    added = CompanyDef(
        slug="acme", label="Acme", base_url="https://api.acme.example/v1", model="m-1"
    )
    page.app.settings = keyed.model_copy(
        update={"companies": [added], "company_keys": {"acme": "k"}}
    )
    companies.use(page.app.settings.companies)
    data = models_page.build(page.app, conn).data
    assert "acme" in one(data, "chat")["vendors"] and "acme" not in one(data, "lookup")["vendors"]
    assert "acme" not in one(data, "hear")["vendors"] and "acme" not in one(data, "look")["vendors"]


def test_a_default_that_follows_another_use_moves_with_it(page):
    data = data_of(page)
    assert one(data, "digest")["default"] == "same:chat"
    assert one(data, "lookup")["default"] == "openai:gpt-6-luna"
    choose = one(data, "choose")
    # Choosing follows the chat's company, at its own strength: the page can say so before saving.
    assert choose["default"] == "openai:gpt-6-astra"
    assert choose["by_company"]["anthropic"] == "anthropic:claude-opus-5"
    assert choose["by_company"]["gemini"] == "gemini:gemini-3.1-pro-preview"
    assert one(data, "judge")["default"] == "off"


def test_the_company_cards_say_what_each_may_do_and_has_spent(page, conn, clock):
    spend(conn, clock, "chat", provider="openai")
    cards = {each["id"]: each for each in data_of(page)["companies"]}
    assert (
        cards["openai"]["haskey"] and cards["anthropic"]["haskey"] and not cards["gemini"]["haskey"]
    )
    assert cards["openai"]["spent"] == pytest.approx(0.01)
    assert cards["gemini"]["allowed"] and cards["gemini"]["limit"] is None


def test_viewing_the_page_asks_no_model(page, monkeypatch):
    from familydb.agent import gateway

    def refuse(*args, **kwargs):
        raise AssertionError("the page asked a model")

    monkeypatch.setattr(gateway, "run_turn", refuse)
    assert page.get("/settings/model").status_code == 200


def _row(text: str, use: str) -> str:
    found = re.search(rf'id="row-{use}".*?</li>', text, re.S)
    assert found is not None
    return found.group(0)


# -- the page without its script -----------------------------------------------------------------


def test_each_row_is_one_dropdown_that_posts_without_the_script(page):
    text = page.get("/settings/model").text
    for use in uses.USES:
        assert f'name="choice_{use.key}"' in text
    row = _row(text, "chat")
    assert '<optgroup label="OpenAI">' in row and '<optgroup label="Anthropic">' in row
    assert '<option value="openai:__other">Another model…</option>' in row
    # Off and "same as" only where a use can be, or can follow.
    assert 'value="off"' not in row and 'value="same:chat"' in _row(text, "digest")
    assert 'value="off"' in _row(text, "choose") and 'value="off"' in _row(text, "hear")
    # The page's own files, and nothing written into the page itself.
    assert "models.js" in text and "models.css" in text
    assert not re.search(r"<script(?![^>]*\bsrc=)", text) and " style=" not in text


# -- saving --------------------------------------------------------------------------------------


def test_a_choice_is_stored_only_when_it_is_not_the_default(page, conn):
    saved = post(page, choice_chat="anthropic:claude-sonnet-5", choice_digest="same:chat")
    assert saved.status_code == 302
    assert settings_store.get(conn, "model_choices") == {"chat": "anthropic:claude-sonnet-5"}
    assert page.app.settings.model_choices == {"chat": "anthropic:claude-sonnet-5"}
    assert uses.resolve(page.app.settings, "digest").followed == "chat"
    # Choosing the default again is putting it back.
    post(page, choice_chat="")
    assert settings_store.get(conn, "model_choices") is None
    assert "Saved. Changed: which model does what." in page.get("/settings/model").text


def test_a_save_that_changes_nothing_says_so_and_writes_nothing(page, conn):
    first = post(page, choice_chat="", choice_digest="", effort_chat="")
    assert first.status_code == 302
    assert "Nothing was different, so nothing was written." in page.get("/settings/model").text
    assert settings_store.overrides(conn) == {}


def test_off_and_follow_are_kept_for_the_uses_that_may_and_refused_for_those_that_may_not(
    page, conn
):
    assert post(page, choice_choose="off", choice_hear="off").status_code == 302
    assert settings_store.get(conn, "model_choices") == {"choose": "off", "hear": "off"}
    refused = post(page, choice_chat="off")
    assert (
        refused.status_code == 400 and "Answering the family: That is not a choice." in refused.text
    )
    refused = post(page, choice_choose="same:chat")  # only a use that follows exactly may follow
    assert refused.status_code == 400
    refused = post(page, choice_chat="nobody:model")
    assert refused.status_code == 400
    assert page.app.settings.model_choices == {"choose": "off", "hear": "off"}


def test_a_company_cannot_be_chosen_for_what_it_cannot_do(page):
    refused = post(page, choice_hear="anthropic:claude-opus-5")
    assert (
        refused.status_code == 400 and "Anthropic cannot do that: it hears nothing." in refused.text
    )
    refused = post(page, choice_lookup="anthropic:claude-opus-5", choice_look="same:lookup")
    assert refused.status_code == 302  # Claude searches, and reads pictures, and may be chosen


def test_a_model_typed_in_needs_a_name_and_is_kept_as_typed(page, conn):
    needs = post(page, choice_chat="openai:__other", other_chat="  ")
    assert needs.status_code == 400 and "Type the model" in needs.text
    assert post(page, choice_chat="openai:__other", other_chat=" gpt-9-new ").status_code == 302
    assert settings_store.get(conn, "model_choices") == {"chat": "openai:gpt-9-new"}
    assert "selected>gpt-9-new</option>" in page.get("/settings/model").text
    assert re.search(
        r'id="row-chat".*?<option value="openai:gpt-9-new" selected',
        page.get("/settings/model").text,
        re.S,
    )


def test_thinking_is_stored_only_when_it_is_not_the_default(page, conn):
    post(page, effort_chat="high", effort_lookup="")
    assert settings_store.get(conn, "use_effort") == {"chat": "high"}
    assert uses.overlay(page.app.settings, "chat").settings.effort == "high"
    assert post(page, effort_chat="loud").status_code == 400
    post(page, effort_chat="")
    assert settings_store.get(conn, "use_effort") is None


def test_what_a_company_may_do_is_stored_as_the_difference_from_the_default(page, conn):
    form = {"company": ["openai", "anthropic", "gemini"]}
    # Nothing different from the default: nothing stored.
    ticked = {
        "allow_openai": "1",
        "allow_anthropic": "1",
        "allow_gemini": "1",
        "standin_openai": "1",
        "standin_anthropic": "1",
        "standin_gemini": "1",
    }
    post(page, **form, **ticked)
    assert settings_store.get(conn, "company_options") is None
    # Anthropic is not let answer, and OpenAI is limited.
    changed = {**ticked, "limit_openai": "12.5"}
    del changed["allow_anthropic"]
    post(page, **form, **changed)
    assert settings_store.get(conn, "company_options") == {
        "anthropic": {"allowed": False},
        "openai": {"monthly_limit": 12.5},
    }
    live = page.app.settings
    assert live.company_options["anthropic"] == CompanyOptions(allowed=False)
    # Stand-in off for Google is what the family said; on is what it was, so it is not stored.
    del ticked["standin_gemini"]
    post(page, **form, **ticked)
    assert settings_store.get(conn, "company_options") == {"gemini": {"stand_in": False}}


def test_a_limit_that_is_not_a_number_is_refused_and_what_else_was_typed_is_kept(page, conn):
    bad = post(
        page,
        company=["openai"],
        allow_openai="1",
        limit_openai="plenty",
        choice_chat="openai:gpt-6-sol",
    )
    assert bad.status_code == 400 and "most to spend" in bad.text
    assert settings_store.overrides(conn) == {}
    assert (
        '<option value="openai:gpt-6-sol" selected>' in bad.text
    )  # the rest of the form is not lost
    assert 'value="plenty"' in bad.text


def test_a_cap_equal_to_the_default_is_not_an_override(page, conn):
    post(page, choose_budget="5.0", judgement_budget="1")
    assert settings_store.overrides(conn) == {}
    post(page, choose_budget="2.5")
    assert settings_store.get(conn, "choose_budget") == 2.5
    assert page.app.settings.choose_budget == 2.5
    assert post(page, choose_budget="a lot").status_code == 400


def test_the_daily_check_is_a_tick_and_an_unticked_one_sends_nothing(page, conn):
    assert page.app.settings.model_watch
    post(page, model_watch_seen="1")  # not ticked: the browser sends only the sentinel
    assert settings_store.get(conn, "model_watch") is False
    post(page, model_watch_seen="1", model_watch="true")
    assert settings_store.get(conn, "model_watch") is None  # on is what it is without a word
    assert page.app.settings.model_watch


def test_the_form_changes_only_what_it_carried(page, conn):
    settings_store.set_many(
        conn, {"web_title": "The Tates", "model_choices": {"chat": "openai:gpt-6-sol"}}
    )
    page.app.refresh()
    post(page, effort_chat="low")
    assert settings_store.get(conn, "web_title") == "The Tates"
    assert settings_store.get(conn, "model_choices") == {"chat": "openai:gpt-6-sol"}


def test_a_save_needs_the_page_s_own_token(page, conn):
    assert (
        page.post("/settings/models", data={"choice_chat": "openai:gpt-6-sol"}).status_code == 400
    )
    assert settings_store.overrides(conn) == {}


# -- a key's check -------------------------------------------------------------------------------


def test_a_key_is_checked_from_its_company_card_and_nothing_is_saved(page, conn, monkeypatch):
    from familydb.agent.providers.openai import OpenAIProvider

    monkeypatch.setattr(OpenAIProvider, "check_key", lambda self: "works")
    done = page.post(
        "/settings/models/check/openai", data={"csrf": token(page), "section": "model"}
    )
    assert done.status_code == 302 and done.headers["Location"].endswith("#co-openai")
    assert "OpenAI's key works." in unescape(page.get("/settings/model").text)
    none = page.post("/settings/models/check/gemini", data={"csrf": token(page)})
    assert none.status_code == 302
    assert "Google has no key yet." in unescape(page.get("/settings/model").text)
    assert page.post("/settings/models/check/nobody", data={"csrf": token(page)}).status_code == 404
    assert settings_store.overrides(conn) == {}


def test_a_key_check_that_is_refused_says_so(page, monkeypatch):
    from familydb.agent.providers.openai import OpenAIProvider

    monkeypatch.setattr(OpenAIProvider, "check_key", lambda self: "refused")
    page.post("/settings/models/check/openai", data={"csrf": token(page)})
    assert "OpenAI refused the key." in page.get("/settings/model").text


# -- what the independent review found -----------------------------------------------------------


def test_a_key_the_company_refuses_is_not_saved_and_one_it_cannot_be_asked_about_is(
    page, conn, monkeypatch
):
    from familydb.agent.providers.gemini import GeminiProvider

    monkeypatch.setattr(GeminiProvider, "check_key", lambda self: "refused")
    refused = page.post(
        "/settings/keys",
        data={"csrf": token(page), "gemini_api_key": "gm-wrong", "section": "model"},
    )
    assert refused.status_code == 400 and "Google did not accept that key" in unescape(refused.text)
    assert settings_store.get(conn, "gemini_api_key") is None
    monkeypatch.setattr(GeminiProvider, "check_key", lambda self: "unchecked")
    kept = page.post("/settings/keys", data={"csrf": token(page), "gemini_api_key": "gm-maybe"})
    assert kept.status_code == 302 and settings_store.get(conn, "gemini_api_key") == "gm-maybe"


def test_a_company_chosen_for_a_row_cannot_be_taken_away_and_goes_with_what_named_it(
    page, conn, monkeypatch
):
    from familydb.agent.providers.chat import ChatProvider

    monkeypatch.setattr(ChatProvider, "check_key", lambda self: "works")
    monkeypatch.setattr(ChatProvider, "listed_models", lambda self: None)
    monkeypatch.setattr(ChatProvider, "priced_models", lambda self: None)
    monkeypatch.setattr("familydb.integrations.address.classify", lambda host: "public")

    def form(**more):
        return {"csrf": token(page), "section": "model", **more}

    page.post(
        "/settings/companies/add",
        data=form(template="openrouter", key="sk-or-1", model="deepseek/deepseek-chat"),
    )
    post(
        page,
        choice_digest="openrouter:deepseek/deepseek-chat",
        company=["openrouter"],
        allow_openrouter="1",
        limit_openrouter="3",
    )
    refused = page.post("/settings/companies/openrouter/remove", data=form())
    assert refused.status_code == 400 and "chosen for The weekend digest" in refused.text
    post(page, choice_digest="")
    assert page.post("/settings/companies/openrouter/remove", data=form()).status_code == 302
    # What was said of it goes too.
    assert settings_store.get(conn, "company_options") is None


def test_a_choice_naming_a_company_that_is_gone_is_the_default(page, conn):
    settings_store.set_many(conn, {"model_choices": {"digest": "nobody:model"}})
    page.app.refresh()
    chat = data_of(page)
    assert one(chat, "digest")["stored"] == "" and one(chat, "digest")["default"] == "same:chat"


def test_a_local_company_that_needs_no_key_is_not_said_to_have_none(page, keyed, conn):
    from familydb.agent.providers import companies

    local = CompanyDef(
        slug="box", label="My box", base_url="http://192.168.1.20:1/v1", model="m", local=True
    )
    page.app.settings = keyed.model_copy(update={"companies": [local]})
    companies.use(page.app.settings.companies)
    cards = {c["id"]: c for c in models_page.build(page.app, conn).data["companies"]}
    assert cards["box"]["haskey"]


def test_a_use_follows_only_the_one_it_follows_and_a_model_name_is_a_name(page, conn):
    assert post(page, choice_look="same:judge").status_code == 400
    assert post(page, choice_look="same:lookup").status_code == 302
    long = post(page, choice_chat="openai:__other", other_chat="x" * 200)
    assert long.status_code == 400 and "no spaces" in long.text
    spaced = post(page, choice_chat="openai:__other", other_chat="gpt 9")
    assert spaced.status_code == 400


def test_the_page_prices_a_claudes_cache_as_the_family_set_it(page, keyed, conn, clock):
    spend(
        conn,
        clock,
        "chat",
        model="claude-haiku-4-5",
        provider="anthropic",
        cache_creation_input_tokens=50000,
    )

    def haiku():
        chat = one(models_page.build(page.app, conn).data, "chat")
        return next(o for o in chat["opts"] if o["n"] == "claude-haiku-4-5")["m"]

    hour = haiku()
    page.app.settings = keyed.model_copy(update={"anthropic_cache_ttl": "5m"})
    assert haiku() < hour  # writing the cache for five minutes costs less than for an hour
