"""What the family can say of each company (config.CompanyOptions): let it answer, let it stand in,
and the most to spend on it in a month."""

from datetime import timedelta

import pytest

from familydb import config
from familydb.agent import gateway, providers, spending, uses
from familydb.agent.providers import Withheld, companies
from familydb.config import CompanyOptions
from familydb.dates import utc_iso
from familydb.store import calls


def keyed(settings, **more):
    return settings.model_copy(
        update={"openai_api_key": "sk-o", "gemini_api_key": "g-1", "provider": "openai", **more}
    )


def options(**by_company):
    return {slug: CompanyOptions(**said) for slug, said in by_company.items()}


def spend(conn, clock, company, dollars, *, days_ago=0):
    when = clock.now() - timedelta(days=days_ago)
    calls.log_llm_call(
        conn,
        message_id=None,
        iteration=1,
        model="m",
        served_model=None,
        request_id=None,
        stop_reason="end",
        usage={},
        duration_ms=1,
        now=utc_iso(when),
        provider=company,
        cost_usd=dollars,
        kind="chat",
    )


# -- reading what the page stored ----------------------------------------------------------------


def test_options_that_cannot_be_read_are_dropped_not_refused():
    loaded = config.Settings(
        _env_file=None,
        company_options={
            "openai": {"allowed": False, "monthly_limit": 12.5},
            "gemini": {"monthly_limit": -3},  # not a limit
            "claude": "nonsense",
        },
    )
    assert set(loaded.company_options) == {"openai"}
    assert loaded.company_options["openai"].monthly_limit == 12.5
    assert config.Settings(_env_file=None, company_options="[]").company_options == {}


def test_a_company_nobody_said_anything_of_is_allowed_with_no_limit(settings):
    assert companies.allowed("openai", settings)
    assert companies.monthly_limit("openai", settings) is None
    assert companies.may_stand_in("openai", settings)  # as provider_fallback says, by default
    assert not companies.may_stand_in(
        "openai", settings.model_copy(update={"provider_fallback": False})
    )


# -- let it answer -------------------------------------------------------------------------------


def test_a_company_not_let_answer_cannot_be_asked_and_a_stand_in_answers(settings):
    live = keyed(settings, company_options=options(openai={"allowed": False}))
    chosen = providers.build("openai", live)
    assert isinstance(chosen, Withheld) and not chosen.configured() and chosen.name == "openai"
    assert providers.build("anthropic", live).configured()  # the others are as they were
    provider, _ = gateway.answering(live, "chat")
    assert provider.name == "openai" and not provider.configured()
    assert providers.fallback_for(live, "chat", "openai").name == "anthropic"  # Claude, the spare
    assert gateway.can_ask(live, "chat")  # something can still answer


def test_with_every_company_withheld_nothing_can_be_asked(settings):
    live = keyed(
        settings,
        company_options=options(
            openai={"allowed": False}, anthropic={"allowed": False}, gemini={"allowed": False}
        ),
    )
    assert not gateway.can_ask(live, "chat")
    assert not gateway.can_listen(live)


def test_a_chosen_company_that_is_withheld_is_answered_by_the_stand_in(
    settings, registry, ctx, monkeypatch
):
    seen = {}
    monkeypatch.setattr(gateway, "run_turn", lambda **kwargs: seen.update(kwargs) or "done")
    live = keyed(
        settings,
        model_choices={"chat": "openai:gpt-6-sol"},
        company_options=options(openai={"allowed": False}),
    )
    gateway.ask("chat", settings=live, registry=registry, ctx=ctx, current=["hi"])
    assert not seen["provider"].configured()  # the loop sees it cannot be asked...
    assert seen["fallback"].name == "anthropic"  # ...and goes to the stand-in
    assert seen["level"] == "better"  # at the strength of the model chosen (Sol)


# -- stand in ------------------------------------------------------------------------------------


def test_each_company_says_for_itself_whether_it_stands_in(settings):
    live = keyed(settings, company_options=options(anthropic={"stand_in": False}))
    assert providers.fallback_for(live, "chat", "openai").name == "gemini"  # Claude is skipped
    none = keyed(
        settings, company_options=options(anthropic={"stand_in": False}, gemini={"stand_in": False})
    )
    assert providers.fallback_for(none, "chat", "openai") is None
    # The family's word for a company beats the one switch that used to say it for all.
    only = keyed(
        settings,
        provider_fallback=False,
        company_options=options(gemini={"stand_in": True}),
    )
    assert providers.fallback_for(only, "chat", "openai").name == "gemini"
    assert (
        providers.fallback_for(keyed(settings, provider_fallback=False), "chat", "openai") is None
    )


def test_a_lookup_goes_only_to_a_company_that_may_stand_in(settings):
    from familydb.config import CompanyDef

    one = CompanyDef(slug="acme", label="Acme", base_url="https://api.acme.example/v1", model="m")
    live = keyed(
        settings,
        companies=[one],
        company_keys={"acme": "k"},
        provider="acme",
        company_options=options(openai={"stand_in": False}, anthropic={"stand_in": False}),
    )
    companies.use(live.companies)
    assert gateway.answering(live, "enrich")[0].name == "gemini"
    assert gateway.answering(live, "chat")[0].name == "acme"


def test_voices_and_photos_are_offered_only_to_those_that_may_stand_in(settings):
    live = keyed(settings, company_options=options(gemini={"stand_in": False}))
    assert [p.name for p in providers.hearers(keyed(settings))] == ["openai", "gemini"]
    assert [p.name for p in providers.hearers(live)] == ["openai"]  # Claude hears nothing
    assert [p.name for p in providers.lookers(keyed(settings))] == ["openai", "anthropic", "gemini"]
    assert [p.name for p in providers.lookers(live)] == ["openai", "anthropic"]


# -- the most to spend a month -------------------------------------------------------------------


def test_a_company_over_its_month_is_not_admitted_and_another_is(settings, conn, clock):
    live = keyed(settings, company_options=options(openai={"monthly_limit": 1.0}))
    spend(conn, clock, "openai", 0.6)
    assert not spending.company_full(conn, live, clock.now(), "openai")
    spending.settle(
        conn, spending.admit(conn, live, clock.now(), 0.01, company="openai"), clock.now()
    )
    spend(conn, clock, "openai", 0.5)
    assert spending.company_full(conn, live, clock.now(), "openai")
    with pytest.raises(spending.CompanyLimitReached) as stopped:
        spending.admit(conn, live, clock.now(), 0.01, company="openai")
    assert not stopped.value.retryable and "monthly limit for openai" in str(stopped.value)
    spending.settle(
        conn, spending.admit(conn, live, clock.now(), 0.01, company="anthropic"), clock.now()
    )


def test_last_months_calls_do_not_count_toward_this_months(settings, conn, clock):
    live = keyed(settings, company_options=options(openai={"monthly_limit": 1.0}))
    spend(conn, clock, "openai", 5.0, days_ago=40)
    assert not spending.company_full(conn, live, clock.now(), "openai")


def test_a_limit_of_nothing_means_the_company_is_not_asked_this_month(settings, conn, clock):
    live = keyed(settings, company_options=options(openai={"monthly_limit": 0}))
    assert spending.company_full(conn, live, clock.now(), "openai")


def test_a_company_with_no_limit_is_never_full(settings, conn, clock):
    spend(conn, clock, "openai", 500.0)
    assert not spending.company_full(conn, keyed(settings), clock.now(), "openai")


def test_a_company_over_its_month_hands_the_turn_to_its_stand_in(
    settings, registry, ctx, conn, clock, monkeypatch
):
    seen = {}
    monkeypatch.setattr(gateway, "run_turn", lambda **kwargs: seen.update(kwargs) or "done")
    live = keyed(settings, company_options=options(openai={"monthly_limit": 1.0}))
    spend(conn, clock, "openai", 2.0)
    gateway.ask("chat", settings=live, registry=registry, ctx=ctx, current=["hi"])
    assert isinstance(seen["provider"], Withheld) and seen["fallback"].name == "anthropic"
    # Under its limit it answers as before.
    seen.clear()
    gateway.ask("chat", settings=keyed(settings), registry=registry, ctx=ctx, current=["hi"])
    assert seen["provider"].configured()


def test_the_use_resolution_is_not_changed_by_a_limit(settings):
    live = keyed(settings, company_options=options(openai={"monthly_limit": 0.0}))
    assert uses.resolve(live, "chat").company == "openai"  # who is chosen is the family's; who
    # answers when it is spent is the stand-in's business, decided at the call.


# -- what a company switched off is never sent ---------------------------------------------------


def test_a_company_not_let_answer_is_never_sent_the_familys_words(
    settings, registry, ctx, monkeypatch
):
    """Chosen for a row and switched off, with nobody to stand in: the turn fails, and nothing is
    sent to the company the family said no to."""
    from familydb.agent.providers.anthropic import AnthropicProvider
    from familydb.errors import AgentError

    sent = []
    monkeypatch.setattr(AnthropicProvider, "send", lambda self, request: sent.append(request))
    live = keyed(
        settings,
        gemini_api_key=None,
        model_choices={"chat": "anthropic:claude-haiku-4-5"},
        company_options=options(anthropic={"allowed": False}, openai={"stand_in": False}),
    )
    with pytest.raises(AgentError) as stopped:
        gateway.ask("chat", settings=live, registry=registry, ctx=ctx, current=["hi"])
    assert sent == [] and not stopped.value.retryable
    assert "not let to answer" in str(stopped.value)


def test_a_withheld_company_sends_no_recording_and_no_photo(settings):
    from familydb.errors import AgentError

    live = keyed(settings, company_options=options(openai={"allowed": False}))
    withheld = providers.build("openai", live)
    for send in (
        lambda: withheld.send(None),
        lambda: withheld.transcribe(None, ""),
        lambda: withheld.describe(None, ""),
    ):
        with pytest.raises(AgentError):
            send()


# -- the readiness gates read what the family chose ----------------------------------------------


def test_a_message_is_answered_by_the_company_chosen_not_the_one_the_old_setting_names(settings):
    """provider names a company with no key; the chat row names one that has: the app can answer."""
    from familydb.app import App

    live = settings.model_copy(
        update={
            "provider": "openai",
            "openai_api_key": None,
            "model_choices": {"chat": "anthropic:claude-haiku-4-5"},
            "company_options": options(anthropic={"stand_in": False}),
        }
    )
    assert not providers.ready(live, "chat")  # what the gate asked, before
    assert App(live).can_ask("chat")
    # And not when what was chosen is the one switched off.
    off = live.model_copy(update={"company_options": options(anthropic={"allowed": False})})
    assert not App(off).can_ask("chat")


# -- a company's month is not a way to fail a message --------------------------------------------


def test_a_company_over_its_month_reports_what_was_written_not_a_failure(
    settings, registry, ctx, conn, clock, monkeypatch
):
    """The company's month runs out between two calls of one turn: what the first wrote is said."""
    from familydb.agent.providers.base import ModelReply, ToolCall
    from familydb.agent.providers.openai import OpenAIProvider

    live = keyed(
        settings,
        gemini_api_key=None,
        daily_spend_limit=0,
        company_options=options(openai={"monthly_limit": 1.0}, anthropic={"stand_in": False}),
    )

    def reply(self, request):
        spend(conn, clock, "openai", 2.0)  # the call that used the month up
        idea = {"title": "Month's end idea", "kind": "outing"}
        return ModelReply(
            stop="tool_use",
            tool_calls=[ToolCall("t1", "add_idea", idea)],
            usage={"input_tokens": 10, "output_tokens": 10},
            model="gpt-6-luna",
        )

    monkeypatch.setattr(OpenAIProvider, "send", reply)
    result = gateway.ask("chat", settings=live, registry=registry, ctx=ctx, current=["save one"])
    assert "Saved idea" in result.text and result.actions[0]["tool"] == "add_idea"


def test_a_stand_in_over_its_month_is_not_switched_to(
    settings, registry, ctx, conn, clock, monkeypatch
):
    from familydb.agent.providers.anthropic import AnthropicProvider
    from familydb.agent.providers.openai import OpenAIProvider
    from familydb.errors import AgentError

    live = keyed(
        settings,
        provider="anthropic",
        gemini_api_key=None,
        daily_spend_limit=0,
        company_options=options(openai={"monthly_limit": 1.0}),
    )
    spend(conn, clock, "openai", 5.0)  # the stand-in has had its month's worth
    asked = []

    def down(self, request):
        raise AgentError("busy", retryable=True)

    monkeypatch.setattr(AnthropicProvider, "send", down)
    monkeypatch.setattr(OpenAIProvider, "send", lambda self, request: asked.append(request))
    with pytest.raises(AgentError, match="busy"):
        gateway.ask("chat", settings=live, registry=registry, ctx=ctx, current=["hi"])
    assert asked == []


def test_a_message_that_meets_a_companys_month_is_told_so_not_that_the_model_is_unreachable(
    settings, clock, conn, family
):
    from familydb.app import App
    from familydb.channels.base import IncomingMessage
    from familydb.pipeline import handle_incoming
    from familydb.store import messages
    from tests import fakes

    live = settings.model_copy(
        update={
            "company_options": options(anthropic={"monthly_limit": 1.0}),
            "daily_spend_limit": 0,
        }
    )
    spend(conn, clock, "anthropic", 2.0)
    api = fakes.FakeMessagesAPI()  # asked nothing: any request would fail the test
    reply = handle_incoming(
        App(live, clock),
        IncomingMessage("telegram", "u1", "chat-1", "1001", "hi"),
        api=api,
        conn=conn,
    )
    assert api.requests == [] and reply is not None and reply.status == "failed"
    assert "The most set for Anthropic this month ($1.00) is used up" in reply.text
    assert messages.get(conn, reply.in_message_id).give_up
