"""Each company's models by level: its cheapest by default, a stronger one in the situations the
family chooses, and the same level on the fallback company."""

from pathlib import Path

from familydb.agent.loop import run_turn
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.providers import NAMES, build, catalog, model_at, prices
from familydb.agent.providers.anthropic import thinks
from familydb.agent.providers.openai import reasoning_effort
from familydb.agent.render import render_user_turn
from familydb.agent.worker import run_worker_turn
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.config import Settings
from familydb.jobs.enrich import render_enrich_request
from familydb.pipeline import DIGEST_UPDATE, handle_incoming, handle_synthetic, retry_message
from familydb.store import ideas
from familydb.store.db import transaction
from tests import fakes

# -- the catalog --------------------------------------------------------------------------------


def test_every_company_has_a_model_at_each_level_and_each_costs_more() -> None:
    for company in NAMES:
        lineup = catalog.lineup(company)
        assert tuple(model.level for model in lineup) == catalog.LEVELS
        assert all(model.provider == company for model in lineup)
        # Priced, or the daily limit would count it as the dearest model there is.
        costs = [model.price for model in lineup]
        assert all(costs), company
        assert [cost.output for cost in costs] == sorted(cost.output for cost in costs)
        assert costs[0].output < costs[-1].output


def test_everyday_is_the_cheapest_model_the_price_table_knows() -> None:
    for company in NAMES:
        cheapest = min(prices.PRICES[company].values(), key=lambda one: (one.output, one.input))
        assert catalog.at(company, "everyday").price == cheapest


def test_by_default_every_company_answers_with_its_everyday_model(tmp_path: Path) -> None:
    defaults = Settings(_env_file=None, familydb_path=tmp_path / "x.db")
    for company in NAMES:
        provider = build(company, defaults)
        everyday = catalog.at(company, "everyday").name
        assert provider.model_for("chat") == provider.model_for("worker") == everyday


def test_the_page_offers_each_lineup_model_by_the_name_its_company_takes() -> None:
    for company in NAMES:
        offered = prices.suggestions(company)
        assert all(model.name in offered for model in catalog.lineup(company)), company


def test_the_catalog_agrees_with_what_each_provider_sends() -> None:
    """What the catalog says a model can do is what its provider module shapes the request for."""
    for model in catalog.lineup("anthropic"):
        assert thinks(model.name) == model.thinks, model.name
    for model in catalog.lineup("openai"):
        assert model.thinks and reasoning_effort(model.name, "xhigh") == "xhigh", model.name
    for model in catalog.lineup("gemini"):
        # Only Gemini 3 searches alongside our own tools, and any level may be asked to look up.
        assert model.thinks and model.name.startswith("gemini-3"), model.name


def test_a_name_is_known_by_its_family_but_not_by_a_longer_name() -> None:
    assert catalog.known("anthropic", "claude-haiku-4-5-20251001").label == "Claude Haiku 4.5"
    assert catalog.known("openai", "gpt-6-sol-2026-09-01").level == "better"
    assert catalog.known("anthropic", "claude-opus-5-5") is None  # a model of its own
    assert catalog.known("openai", "gpt-6-luna-mini") is None
    assert catalog.known("nobody", "gpt-6-luna") is None and catalog.known(None, None) is None


def test_the_stronger_models_have_prices() -> None:
    million_out = {"output_tokens": 1_000_000}
    assert prices.cost("openai", "gpt-6-sol", million_out) == (10.0, True)
    assert prices.cost("openai", "gpt-6-astra", million_out) == (50.0, True)
    assert prices.cost("gemini", "gemini-3.1-pro-preview", million_out) == (12.0, True)
    # The lookup model Gemini installs had was counted as unlisted, twenty times too dear.
    assert prices.cost("gemini", "gemini-3.8-flash", million_out) == (3.75, True)


# -- choosing by level --------------------------------------------------------------------------


# Claude's everyday as it is by default, where the fixture's is Opus for the sake of its scripts.
CHEAPEST = {"anthropic_model": "claude-haiku-4-5"}


def test_everyday_is_the_model_set_and_the_others_come_from_the_catalog(settings) -> None:
    pinned = settings.model_copy(update={"openai_model": "gpt-5-mini", "openai_worker_model": ""})
    openai = build("openai", pinned)
    assert model_at(openai, "chat", "everyday") == "gpt-5-mini"
    assert model_at(openai, "worker", "everyday") == "gpt-5-mini"  # empty: the chat one
    assert model_at(openai, "chat", "better") == "gpt-6-sol"
    assert model_at(openai, "worker", "best") == "gpt-6-astra"


def test_a_level_up_never_answers_with_a_cheaper_model(settings) -> None:
    """An everyday model set above the lineup's stays: Opus, as an older .env named it."""
    opus = build("anthropic", settings)  # the fixture's everyday Claude is Opus 5
    assert model_at(opus, "chat", "better") == model_at(opus, "chat", "best") == "claude-opus-5"
    fable = build("anthropic", settings.model_copy(update={"anthropic_model": "claude-fable-5-1"}))
    assert model_at(fable, "chat", "best") == "claude-fable-5-1"
    # Price is what decides, so an older model that costs more stays too.
    sonnet = build(
        "anthropic", settings.model_copy(update={"anthropic_model": "claude-sonnet-4-6"})
    )
    assert model_at(sonnet, "chat", "better") == "claude-sonnet-4-6"
    assert model_at(sonnet, "chat", "best") == "claude-opus-5"
    older = build("openai", settings.model_copy(update={"openai_model": "gpt-5"}))
    assert model_at(older, "chat", "better") == "gpt-6-sol"  # no cheaper, so the lineup's
    # A model the price table does not list counts as dearer than any it does.
    newer = build("anthropic", settings.model_copy(update={"anthropic_model": "claude-opus-6"}))
    assert model_at(newer, "chat", "better") == "claude-opus-6"


def test_each_situation_is_answered_at_its_own_level(settings, clock, conn, family) -> None:
    chosen = {**CHEAPEST, "chat_level": "better", "digest_level": "best"}
    app = App(settings.model_copy(update=chosen), clock)
    answer = fakes.FakeMessagesAPI(fakes.message([fakes.text("Sounds good.")]))
    handle_incoming(app, IncomingMessage("telegram", "1", "c", "1001", "hi"), api=answer, conn=conn)
    digest = IncomingMessage("telegram", f"{DIGEST_UPDATE}2026-09-24", "-100", "1001", "Digest")
    weekly = fakes.FakeMessagesAPI(fakes.message([fakes.text("Here is the weekend.")]))
    handle_synthetic(app, digest, family["sam"], api=weekly, conn=conn)
    assert answer.requests[0]["model"] == "claude-sonnet-5"
    assert weekly.requests[0]["model"] == "claude-opus-5"
    models = [row[0] for row in conn.execute("SELECT model FROM llm_calls ORDER BY id")]
    assert models == ["claude-sonnet-5", "claude-opus-5"]  # and recorded, so priced, as such


def test_a_digest_asked_again_is_still_the_digest(settings, clock, conn, family) -> None:
    """At the digest's level, recorded as the digest, and quiet if it gives up: nobody asked."""
    chosen = {**CHEAPEST, "digest_level": "best", "chat_level": "better", "agent_max_iterations": 1}
    app = App(settings.model_copy(update=chosen), clock)
    app.senders["telegram"] = lambda chat_id, text: None
    digest = IncomingMessage("telegram", f"{DIGEST_UPDATE}2026-09-24", "-100", "1001", "Digest")
    busy = fakes.FakeMessagesAPI(fakes.rate_limit_error())
    failed = handle_synthetic(app, digest, family["sam"], api=busy, conn=conn)
    assert failed.status == "failed"
    looping = fakes.message([fakes.tool_use("tu", "search_ideas", {})], stop_reason="tool_use")
    again = fakes.FakeMessagesAPI(looping)
    reply = retry_message(app, failed.in_message_id, api=again, conn=conn)
    assert again.requests[0]["model"] == "claude-opus-5"  # the digest's best, not the chat's
    assert reply.status == "failed" and reply.out_message_id is None  # gave up, said nothing
    assert [row[0] for row in conn.execute("SELECT kind FROM llm_calls")] == ["digest"]


def test_a_lookup_is_asked_at_the_lookup_level(settings, clock, conn, registry) -> None:
    stronger = settings.model_copy(update={"lookup_level": "better", "chat_level": "best"})
    with transaction(conn):
        idea = ideas.insert(conn, title="Hopscotch, Portland", kind="outing")
    api = fakes.FakeMessagesAPI(*fakes.enrich_script({"idea_id": idea.id, "name": "Hopscotch"}))
    run_worker_turn(
        kind="enrich",
        api=api,
        settings=stronger,
        clock=clock,
        registry=registry,
        conn=conn,
        request=render_enrich_request(idea, None, stronger),
        geocoder=fakes.FakeGeocoder(),
        idea_id=idea.id,
    )
    assert {request["model"] for request in api.requests} == {"claude-sonnet-5"}


def test_the_fallback_answers_at_the_same_level(settings, registry, ctx) -> None:
    paired = settings.model_copy(update={"openai_api_key": "sk-openai", "provider_fallback": True})
    busy = build("anthropic", paired, api=fakes.FakeMessagesAPI(fakes.rate_limit_error()))
    spare_api = fakes.FakeResponsesAPI(fakes.oa_response([fakes.oa_text("Hi Sam!")]))
    result = run_turn(
        provider=busy,
        settings=paired,
        registry=registry,
        ctx=ctx,
        system=build_system_blocks(ctx.conn, paired),
        messages=build_messages([], render_user_turn("Sam", "hello", ctx.clock)),
        fallback=build("openai", paired, api=spare_api),
        model="claude-sonnet-5",
        level="better",
    )
    assert result.status == "ok" and result.provider == "openai"
    assert spare_api.requests[0]["model"] == "gpt-6-sol"  # OpenAI's better, not its everyday
