"""Companies the settings define (config.CompanyDef): what is accepted, how the registry and the
price table read them, and that none of the family's words go to one by accident."""

import pytest
from pydantic import ValidationError

from familydb.agent import providers
from familydb.agent.providers import companies, prices
from familydb.config import CompanyDef, ModelPrice, Settings
from familydb.store import settings as settings_store


def defined(**more):
    return CompanyDef(
        **{
            "slug": "openrouter",
            "label": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "deepseek/deepseek-chat",
            **more,
        }
    )


def with_company(settings, **more):
    return settings.model_copy(
        update={"companies": [defined(**more)], "company_keys": {"openrouter": "sk-or-1"}}
    )


# -- what a definition accepts ----------------------------------------------------------------


@pytest.mark.parametrize("slug", ["x", "1abc", "Has Space", "under_score", "a" * 25, "openai"])
def test_a_slug_is_a_short_plain_name_that_is_not_a_built_in_company(slug):
    with pytest.raises(ValidationError):
        defined(slug=slug)


@pytest.mark.parametrize(
    "address",
    [
        "ftp://example.org/v1",
        "not a url",
        "https://user:pw@example.org/v1",
        "https://example.org/v1?key=abc",
        "https://example.org/v1#x",
        "http://example.org/v1",  # plain http only for a service on your own network
    ],
)
def test_an_address_is_https_with_nothing_secret_in_it(address):
    with pytest.raises(ValidationError):
        defined(base_url=address)


def test_a_service_on_your_own_network_may_use_http():
    one = defined(base_url="http://192.168.1.20:11434/v1/", local=True)
    assert one.base_url == "http://192.168.1.20:11434/v1"  # the trailing slash goes


def test_extra_fields_cannot_overwrite_what_the_adapter_owns():
    with pytest.raises(ValidationError, match="messages"):
        defined(extra_body={"messages": []})
    assert defined(extra_body={"provider": {"data_collection": "deny"}}).extra_body


def test_a_model_name_is_one_line():
    with pytest.raises(ValidationError):
        defined(model="a\nb")


def test_settings_refuse_two_companies_with_one_name_and_a_choice_nobody_defined():
    with pytest.raises(ValidationError, match="same name"):
        Settings(_env_file=None, companies=[defined(), defined(label="Again")])
    with pytest.raises(ValidationError, match="use one of"):
        Settings(_env_file=None, provider="nobody")
    assert Settings(_env_file=None, companies=[defined()], provider="openrouter").provider == (
        "openrouter"
    )


def test_a_companys_key_is_masked_wherever_settings_are_shown(settings):
    shown = with_company(settings).masked()
    assert shown["company_keys"] == "****"
    assert "sk-or-1" not in str(shown)


def test_the_stored_settings_accept_the_two_and_log_no_key(conn):
    one = defined().model_dump(mode="json")
    settings_store.set_many(conn, {"companies": [one], "company_keys": {"openrouter": "sk-or-1"}})
    assert settings_store.overrides(conn)["companies"] == [one]
    logged = conn.execute("SELECT key, secret, old_value, new_value FROM settings_log").fetchall()
    assert {row["key"] for row in logged} == {"companies", "company_keys"}
    keyed = next(row for row in logged if row["key"] == "company_keys")
    assert keyed["secret"] == 1 and keyed["new_value"] is None
    assert "sk-or-1" not in " ".join(str(tuple(row)) for row in logged)


# -- the registry ---------------------------------------------------------------------------------


def test_an_added_company_is_found_named_and_keyed_like_a_built_in_one(settings):
    live = with_company(settings)
    company = companies.get("openrouter", live)
    assert company is not None and not company.built_in
    assert company.label == companies.label("openrouter", live) == "OpenRouter"
    assert company.key(live) == "sk-or-1"
    assert company.key(settings) is None  # the key is kept with the settings that define it
    assert company.chat_model(live) == "deepseek/deepseek-chat"
    assert company.worker_model(live) == "deepseek/deepseek-chat"  # no lookup model named
    assert companies.slugs(live) == (*companies.SPARE_ORDER, "openrouter")
    assert companies.slugs(settings) == companies.SPARE_ORDER


def test_a_company_the_app_has_put_in_force_is_named_without_settings(settings):
    live = with_company(settings)
    assert companies.named("openrouter") == "openrouter"
    companies.use(live.companies)
    assert companies.named("openrouter") == "OpenRouter"
    assert companies.owner("deepseek/deepseek-chat") == "openrouter"
    assert companies.owner("deepseek/other") is None


def test_the_levels_above_everyday_are_the_names_the_family_gave(settings):
    live = with_company(settings, better_model="a/better", best_model="a/best")
    company = companies.get("openrouter", live)
    assert company.level_model(live, "better") == "a/better"
    assert company.level_model(live, "best") == "a/best"
    assert company.level_model(live, "everyday") == ""
    # A built-in company's still come from its own settings.
    assert companies.OPENAI.level_model(live, "better") == ""


# -- prices ---------------------------------------------------------------------------------------


def test_an_added_models_price_is_the_one_typed_and_only_for_that_exact_name(settings):
    live = with_company(
        settings,
        prices=[ModelPrice(name="deepseek/deepseek-chat", input=0.27, output=1.10, cached=0.07)],
    )
    companies.use(live.companies)
    rate = prices.price("openrouter", "DeepSeek/deepseek-chat")
    assert (rate.input, rate.output, rate.cached) == (0.27, 1.10, 0.07)
    # A longer name is another model, so it is counted at the dearer unlisted price.
    assert prices.price("openrouter", "deepseek/deepseek-chat-v2") is None
    dollars, listed = prices.cost("openrouter", "deepseek/deepseek-chat", {"input_tokens": 1000})
    assert listed and dollars == pytest.approx(0.00027)
    unlisted = prices.cost("openrouter", "deepseek/deepseek-chat-v2", {"input_tokens": 1000})
    assert not unlisted[1] and unlisted[0] == pytest.approx(0.015)
    assert prices.suggestions("openrouter") == ("deepseek/deepseek-chat",)


def test_a_price_with_no_cached_rate_is_not_cheaper_when_cached(settings):
    companies.use([defined(prices=[ModelPrice(name="m", input=2, output=8)])])
    assert prices.price("openrouter", "m").cached == 2


# -- who is asked ---------------------------------------------------------------------------------


def test_an_added_company_is_never_a_spare_unless_it_says_it_may_be(settings):
    keyed = with_company(settings).model_copy(
        update={"anthropic_api_key": None, "openai_api_key": None, "gemini_api_key": None}
    )
    assert providers.others("anthropic", keyed) == ["openai", "gemini", "openrouter"]
    assert providers.fallback_for(keyed, "chat", "anthropic") is None  # not allowed, so not built


def test_a_company_that_is_no_longer_defined_is_not_asked_for(settings):
    gone = settings.model_copy(update={"provider": "openrouter"})  # as a reload could leave it
    assert providers.chosen(gone, "chat") == companies.DEFAULT
    assert providers.chosen(gone.model_copy(update={"worker_provider": "nope"}), "worker") == (
        companies.DEFAULT
    )


def test_extra_fields_are_plain_json_and_cannot_give_a_chat_tools_or_a_search():
    for body in ({"x": float("nan")}, {"x": float("inf")}, {"x": object()}):
        with pytest.raises(ValidationError, match="plain JSON"):
            defined(extra_body=body)
    for name in ("plugins", "response_format", "functions", "stop", "models", "web_search_options"):
        with pytest.raises(ValidationError, match=name):
            defined(extra_body={name: 1})
    assert defined(extra_body={"thinking": {"type": "disabled"}, "reasoning": {"effort": "low"}})
