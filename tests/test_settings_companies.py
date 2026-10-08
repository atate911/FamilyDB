"""The Other companies card on the AI model settings page: adding a company, changing it, choosing
it and taking it away, with the key checked by the company and kept like every other key."""

from __future__ import annotations

import re

import pytest

from familydb.agent.providers import companies
from familydb.agent.providers.chat import ChatProvider
from familydb.app import App
from familydb.integrations import address
from familydb.store import settings as settings_store
from familydb.web import create_app

PASSWORD = "open sesame please"
KEY = "sk-or-very-secret-1234"


@pytest.fixture
def page(settings, clock, conn, family, monkeypatch):
    """A signed-in client; a company's key checks as accepted unless a test says otherwise, and no
    address is looked up on the network."""
    app = App(settings.model_copy(update={"web_password": PASSWORD, "model_watch": True}), clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    client.app = app
    client.verdict = "works"
    monkeypatch.setattr(ChatProvider, "check_key", lambda self: client.verdict)
    # What the company lists and what it says things cost: nothing here reaches a network.
    client.listed = None
    client.priced = None
    monkeypatch.setattr(ChatProvider, "listed_models", lambda self: client.listed)
    monkeypatch.setattr(ChatProvider, "priced_models", lambda self: client.priced)
    monkeypatch.setattr(
        address, "classify", lambda host: "private" if host.startswith("192.168.") else "public"
    )
    return client


def _token(client) -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get("/settings/model").text)
    assert found is not None
    return found.group(1)


def post(client, path, **form):
    return client.post(path, data={"csrf": _token(client), "section": "model", **form})


def add_openrouter(client, **form):
    return post(
        client,
        "/settings/companies/add",
        template="openrouter",
        key=KEY,
        model="deepseek/deepseek-chat",
        **form,
    )


def errors(text: str) -> str:
    return " ".join(re.findall(r'class="banner__text">\s*([^<]+)', text)).strip()


def stored_companies(conn):
    return settings_store.get(conn, "companies") or []


# -- the card ---------------------------------------------------------------------------------


def test_the_card_offers_openrouter_and_any_other_company(page):
    text = page.get("/settings/model").text
    assert "Other companies" in text
    assert "Add OpenRouter" in text and "Add another company" in text
    assert "None of them can search the web" in text


# -- adding -----------------------------------------------------------------------------------


def test_adding_openrouter_needs_a_key_and_a_model_and_keeps_the_rest_from_its_template(page, conn):
    saved = add_openrouter(page)
    assert saved.status_code == 302
    (one,) = stored_companies(conn)
    assert one["slug"] == "openrouter" and one["base_url"] == "https://openrouter.ai/api/v1"
    assert one["model"] == "deepseek/deepseek-chat" and one["stand_in"] is False
    assert one["extra_body"]["provider"]["data_collection"] == "deny"
    assert one["reasoning_fields"] == ["reasoning_details", "reasoning"]
    assert settings_store.get(conn, "company_keys") == {"openrouter": KEY}
    live = page.app.settings
    assert companies.get("openrouter", live) is not None and live.provider != "openrouter"


def test_an_added_company_is_asked_nothing_until_it_is_chosen(page):
    add_openrouter(page)
    from familydb.agent import gateway

    assert gateway.answering(page.app.settings, "chat")[0].name != "openrouter"


def test_a_key_is_never_shown_or_logged(page, conn):
    add_openrouter(page)
    for path in ("/settings/model", "/settings", "/settings/security", "/status"):
        assert KEY not in page.get(path).text
    history = page.get("/settings/history")
    assert history.status_code == 200 and KEY not in history.text
    for line in settings_store.history(conn):
        assert line["key"] not in {"company_keys"} or line["secret"] == 1
        assert KEY not in str(line)


def test_a_key_the_company_refuses_is_not_kept(page, conn):
    page.verdict = "refused"
    refused = add_openrouter(page)
    assert refused.status_code == 400
    assert "did not accept that key" in refused.text
    assert stored_companies(conn) == [] and settings_store.get(conn, "company_keys") is None


def test_a_company_that_cannot_be_asked_is_kept_with_a_word_about_it(page, conn):
    page.verdict = "unchecked"
    add_openrouter(page)
    assert len(stored_companies(conn)) == 1
    assert "could not be asked just now" in page.get("/settings/model").text


def test_a_model_the_company_does_not_list_is_kept_with_a_word_about_it(page, conn):
    page.verdict = "unknown_model"
    add_openrouter(page)
    assert len(stored_companies(conn)) == 1
    assert "no model called deepseek/deepseek-chat" in page.get("/settings/model").text


def test_adding_a_company_with_nothing_missing(page, conn):
    saved = post(
        page,
        "/settings/companies/add",
        label="Deep Seek",
        base_url="https://api.deepseek.com/",
        model="deepseek-chat",
        key="dk-1",
        reasoning_fields="reasoning_content",
    )
    assert saved.status_code == 302
    (one,) = stored_companies(conn)
    assert one["slug"] == "deep-seek" and one["base_url"] == "https://api.deepseek.com"
    assert one["reasoning_fields"] == ["reasoning_content"] and one["local"] is False
    assert settings_store.get(conn, "company_keys") == {"deep-seek": "dk-1"}


@pytest.mark.parametrize(
    "form, words",
    [
        (
            {"label": "", "base_url": "https://a.example/v1", "model": "m", "key": "k"},
            "Give the company a name",
        ),
        ({"label": "A", "base_url": "", "model": "m", "key": "k"}, "web address"),
        ({"label": "A", "base_url": "ftp://a.example/v1", "model": "m", "key": "k"}, "web address"),
        ({"label": "A", "base_url": "http://a.example/v1", "model": "m", "key": "k"}, "https"),
        (
            {"label": "A", "base_url": "https://a.example/v1", "model": "", "key": "k"},
            "Name the model",
        ),
        (
            {"label": "A", "base_url": "https://a.example/v1", "model": "m", "key": ""},
            "Paste the key",
        ),
        (
            {"label": "A", "base_url": "https://a.example/v1", "model": "m", "key": "a b"},
            "no spaces",
        ),
        (
            {"label": "OpenAI", "base_url": "https://a.example/v1", "model": "m", "key": "k"},
            "already a company",
        ),
        (
            {"label": "A", "base_url": "https://192.168.1.5/v1", "model": "m", "key": "k"},
            "not out on the internet",
        ),
    ],
)
def test_a_form_that_will_not_do_is_refused_in_words_and_nothing_is_kept(page, conn, form, words):
    refused = post(page, "/settings/companies/add", **form)
    assert refused.status_code == 400 and words in refused.text
    assert stored_companies(conn) == []


def test_a_service_on_the_family_network_needs_no_key_and_may_use_http(page, conn):
    saved = post(
        page,
        "/settings/companies/add",
        label="Kitchen box",
        base_url="http://192.168.1.20:11434/v1",
        model="llama",
        local="1",
        key="",
    )
    assert saved.status_code == 302
    (one,) = stored_companies(conn)
    assert one["local"] is True
    assert not settings_store.get(conn, "company_keys")


def test_two_companies_cannot_share_a_name_and_there_is_a_limit(page, conn):
    add_openrouter(page)
    again = add_openrouter(page)
    assert again.status_code == 400 and "already a company" in again.text
    assert len(stored_companies(conn)) == 1


def test_a_form_from_somewhere_else_is_refused(page, conn):
    refused = page.post(
        "/settings/companies/add",
        data={"csrf": "made up", "template": "openrouter", "key": KEY, "model": "m"},
    )
    assert refused.status_code == 400 and stored_companies(conn) == []


# -- changing ---------------------------------------------------------------------------------


def edit(client, slug="openrouter", **form):
    base = {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-chat",
        "reasoning_fields": "reasoning_details, reasoning",
        "extra_body": '{"provider": {"data_collection": "deny"}}',
    }
    return post(client, f"/settings/companies/{slug}", **{**base, **form})


def test_the_models_and_the_prices_of_a_company_can_be_changed(page, conn):
    add_openrouter(page)
    saved = edit(
        page,
        better_model="vendor/better",
        prices="deepseek/deepseek-chat 0.27 1.10 0.07\nvendor/better cheap",
    )
    assert saved.status_code == 400 and "Line 2 of the prices" in saved.text
    saved = edit(
        page,
        better_model="vendor/better",
        prices="deepseek/deepseek-chat 0.27 1.10 0.07\nvendor/better 1 4",
        stand_in="1",
    )
    assert saved.status_code == 302
    (one,) = stored_companies(conn)
    assert one["better_model"] == "vendor/better" and one["stand_in"] is True
    assert [price["name"] for price in one["prices"]] == ["deepseek/deepseek-chat", "vendor/better"]
    from familydb.agent.providers import prices

    assert prices.price("openrouter", "vendor/better").output == 4
    assert settings_store.get(conn, "company_keys") == {
        "openrouter": KEY
    }  # a blank key box keeps it


def test_a_new_key_is_checked_with_the_company_and_a_refused_one_changes_nothing(page, conn):
    add_openrouter(page)
    page.verdict = "refused"
    refused = edit(page, key="sk-or-new")
    assert refused.status_code == 400
    assert settings_store.get(conn, "company_keys") == {"openrouter": KEY}
    page.verdict = "works"
    assert edit(page, key="sk-or-new").status_code == 302
    assert settings_store.get(conn, "company_keys") == {"openrouter": "sk-or-new"}


def test_extra_fields_must_be_a_json_object_and_not_the_ones_we_own(page, conn):
    add_openrouter(page)
    assert "JSON object" in edit(page, extra_body="[1, 2]").text
    assert "JSON object" in edit(page, extra_body="{oops").text
    assert "set by FamilyDB" in edit(page, extra_body='{"messages": []}').text
    assert stored_companies(conn)[0]["extra_body"]["provider"]["data_collection"] == "deny"


def test_a_company_nobody_added_cannot_be_changed(page):
    assert edit(page, slug="nobody").status_code == 404


# -- choosing and taking away -----------------------------------------------------------------


def test_a_company_answers_once_chosen_and_stays_until_another_is(page, conn):
    add_openrouter(page)
    chosen = post(page, "/settings/companies/openrouter/use")
    assert chosen.status_code == 302
    assert page.app.settings.provider == "openrouter"
    assert "OpenRouter answers the family now" in page.get("/settings/model").text
    # Every page still draws with it answering.
    for path in (
        "/settings",
        "/settings/model",
        "/settings/lookups",
        "/status",
        "/settings/spending",
    ):
        assert page.get(path).status_code == 200, path
    in_use = post(page, "/settings/companies/openrouter/remove")
    assert in_use.status_code == 400 and "answering now" in in_use.text
    post(page, "/settings/model", provider="openai", key="sk-new")
    assert page.app.settings.provider == "openai"


def test_a_company_without_its_key_cannot_be_chosen(page, conn):
    post(
        page,
        "/settings/companies/add",
        label="Local box",
        base_url="http://192.168.1.20:1/v1",
        model="m",
        local="1",
    )
    kept = settings_store.get(conn, "companies")
    page.app.refresh()
    # Take its address away from "local": a company that needs a key and has none is not ready.
    edit_form = {
        "label": "Local box",
        "base_url": "https://box.example/v1",
        "model": "m",
        "reasoning_fields": "reasoning_content",
        "extra_body": "",
    }
    post(page, f"/settings/companies/{kept[0]['slug']}", **edit_form)
    refused = post(page, f"/settings/companies/{kept[0]['slug']}/use")
    assert refused.status_code == 400 and "needs its key" in refused.text


def test_taking_a_company_away_takes_its_key(page, conn):
    add_openrouter(page)
    gone = post(page, "/settings/companies/openrouter/remove")
    assert gone.status_code == 302
    assert stored_companies(conn) == [] and settings_store.get(conn, "company_keys") == {}
    assert companies.get("openrouter", page.app.settings) is None


def test_the_daily_check_does_not_break_when_a_company_is_added(page, conn):
    add_openrouter(page)
    post(page, "/settings/companies/openrouter/use")
    assert page.get("/status").status_code == 200


def test_an_address_nobody_can_find_is_said_so_and_a_templates_is_not_looked_up(
    page, conn, monkeypatch
):
    monkeypatch.setattr(address, "classify", lambda host: "unresolved")
    refused = post(
        page,
        "/settings/companies/add",
        label="Nowhere",
        base_url="https://nowhere.example/v1",
        model="m",
        key="k",
    )
    assert refused.status_code == 400 and "could not find nowhere.example" in refused.text
    # OpenRouter's address is ours, so no lookup of it can stop adding it.
    monkeypatch.setattr(address, "classify", lambda host: 1 / 0)
    assert add_openrouter(page).status_code == 302


# -- what a review found: a key goes only where its owner has just said, and nothing is wiped


@pytest.fixture
def checked(page, monkeypatch):
    """Every key check the page makes, with the key it would have sent."""
    seen = []

    def check(self):
        seen.append((self.defined.base_url, self.key))
        return "works"

    monkeypatch.setattr(ChatProvider, "check_key", check)
    return seen


def test_a_saved_key_is_not_sent_to_a_new_address_unless_the_key_is_typed_again(
    page, conn, checked
):
    add_openrouter(page)
    checked.clear()
    refused = edit(page, base_url="https://elsewhere.example/v1")
    assert refused.status_code == 400 and "type its key again" in refused.text
    assert checked == []  # the stored key went nowhere, not even to be checked
    assert stored_companies(conn)[0]["base_url"] == "https://openrouter.ai/api/v1"
    # Typed again, it is the new key that is checked, with the new address.
    assert edit(page, base_url="https://elsewhere.example/v1", key="sk-new").status_code == 302
    assert checked == [("https://elsewhere.example/v1", "sk-new")]
    assert settings_store.get(conn, "company_keys") == {"openrouter": "sk-new"}


def test_moving_a_company_to_the_family_network_drops_its_key_and_sends_it_nowhere(
    page, conn, checked
):
    add_openrouter(page)
    checked.clear()
    moved = edit(page, base_url="http://192.168.1.20:11434/v1", local="1")
    assert moved.status_code == 302
    assert settings_store.get(conn, "company_keys") == {}
    assert [key for _, key in checked] == [None]


def test_a_company_pointed_somewhere_else_is_no_longer_its_templates(page, conn, checked):
    add_openrouter(page)
    assert stored_companies(conn)[0]["template"] == "openrouter"
    edit(page, base_url="https://elsewhere.example/v1", key="k")
    assert stored_companies(conn)[0]["template"] == ""
    text = page.get("/settings/model").text
    panel = text.split('id="company-openrouter"')[1].split("Add OpenRouter")[0]
    assert "Added from OpenRouter" not in panel and "keep and train on nothing" not in panel
    assert "Add OpenRouter" in text  # its template is on offer again, as it is nobody's now


def test_a_form_that_leaves_boxes_out_keeps_what_those_boxes_held(page, conn):
    add_openrouter(page)
    short = post(
        page,
        "/settings/companies/openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        model="another/model",
    )
    assert short.status_code == 302
    (one,) = stored_companies(conn)
    assert one["model"] == "another/model"
    assert one["extra_body"]["provider"]["data_collection"] == "deny"
    assert one["reasoning_fields"] == ["reasoning_details", "reasoning"]


def test_taking_away_the_privacy_fields_is_allowed_and_said(page, conn):
    add_openrouter(page)
    said = edit(page, extra_body="")
    assert said.status_code == 302
    assert stored_companies(conn)[0]["extra_body"] == {}
    after = page.get("/settings/model").text
    assert "no longer asks OpenRouter to use only companies that keep and train on nothing" in after
    assert "no longer ask OpenRouter to use only companies that keep" in after


def test_a_service_out_on_the_internet_cannot_be_called_local(page, conn):
    refused = post(
        page,
        "/settings/companies/add",
        label="Far away",
        base_url="http://api.example.com/v1",
        model="m",
        key="k",
        local="1",
    )
    assert refused.status_code == 400 and "out on the internet" in refused.text
    assert stored_companies(conn) == []


def test_the_company_boxes_stay_dropdowns_and_offer_no_added_company_for_lookups(page, conn):
    from familydb.web import fields

    for key in ("provider", "worker_provider"):
        one = next(box for box in fields.FIELDS if box.key == key)
        assert one.choices == companies.SPARE_ORDER, key
    add_openrouter(page)
    text = page.get("/settings/model").text
    lookups = text.split('<select id="f-worker_provider"')[1].split("</select>")[0]
    assert "openrouter" not in lookups  # it has no hosted search, so it is not offered for lookups


# -- a new company is priced at once, or said to be unpriced


def test_a_new_company_is_priced_from_its_own_list_at_once(page, conn):
    from familydb.agent.providers import prices

    page.listed = ["deepseek/deepseek-chat"]
    page.priced = {"deepseek/deepseek-chat": (0.27, 1.10, 0.07)}
    add_openrouter(page)
    rate = prices.price("openrouter", "deepseek/deepseek-chat")
    assert rate is not None and (rate.input, rate.output) == (0.27, 1.10)
    assert "no price yet" not in page.get("/settings/model").text


def test_a_new_company_that_gives_no_prices_is_said_to_be_counted_dear(page, conn):
    from familydb.agent.providers import prices

    page.listed = ["deepseek/deepseek-chat"]
    page.priced = {}  # its list names the model but carries no price
    add_openrouter(page)
    assert prices.price("openrouter", "deepseek/deepseek-chat") is None
    text = page.get("/settings/model").text
    assert "no price yet for deepseek/deepseek-chat" in text and "counted at more than any" in text
    # Typing one is the way out, and the warning goes.
    saved = edit(page, prices="deepseek/deepseek-chat 0.27 1.10")
    assert saved.status_code == 302
    assert "no price yet" not in page.get("/settings/model").text


def test_a_company_that_cannot_be_asked_for_prices_still_keeps_what_was_typed(page, conn):
    page.listed = None  # unreachable
    page.priced = None
    assert add_openrouter(page).status_code == 302
    assert len(stored_companies(conn)) == 1
