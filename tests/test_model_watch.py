"""The daily check of models and prices: what it reads, what it keeps, and what it tells."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

import pytest

from familydb import alerts, model_watch
from familydb.agent.providers import prices
from familydb.app import App
from familydb.clock import FixedClock
from familydb.integrations.price_lists import (
    Listed,
    PriceListError,
    parse_litellm,
    parse_openrouter,
)
from familydb.store import alerts as alert_store
from familydb.store import model_watch as store
from tests.conftest import TZ


def _listed(inp: float, out: float, *, tools: bool = True, retires_on: str | None = None) -> Listed:
    return Listed(input=inp, output=out, cached=inp / 10, tools=tools, retires_on=retires_on)


class Lists:
    """Both price lists, as a test sets them; either may be made to fail."""

    def __init__(self, litellm=None, openrouter=None):
        self.prices = {"litellm": litellm, "openrouter": openrouter}

    def _read(self, source):
        found = self.prices[source]
        if isinstance(found, Exception):
            raise found
        return found

    def litellm(self):
        return self._read("litellm")

    def openrouter(self):
        return self._read("openrouter")


# The family's settings answer on Claude: Haiku 4.5 for everything, the fixture's Opus 5 to chat.
CLAUDE = {
    "claude-haiku-4-5": _listed(1.0, 5.0),
    "claude-opus-5": _listed(5.0, 25.0),
    "claude-sonnet-5": _listed(2.0, 10.0),
}
OPENAI = {"gpt-6-luna": _listed(0.1, 0.5), "gpt-6-sol": _listed(2.0, 10.0)}


def _both(anthropic=None, openai=None):
    table = {"anthropic": dict(anthropic or CLAUDE), "openai": dict(openai or OPENAI)}
    return Lists(litellm=table, openrouter={k: dict(v) for k, v in table.items()})


def _app(settings, day=20, hour=5):
    watching = settings.model_copy(update={"model_watch": True})
    return App(watching, FixedClock(datetime(2026, 9, day, hour, 17), TZ))


def _claude(*names):
    return {"anthropic": lambda: list(names)}


def _alerts(conn):
    return {(a.kind, a.subject): a.detail for a in alert_store.current(conn, since="2000")}


# -- reading the lists ---------------------------------------------------------------------------


def test_each_list_is_read_by_the_company_s_own_names() -> None:
    litellm = parse_litellm(
        {
            "claude-opus-5": {
                "litellm_provider": "anthropic",
                "mode": "chat",
                "input_cost_per_token": 5e-06,
                "output_cost_per_token": 2.5e-05,
                "cache_read_input_token_cost": 5e-07,
                "supports_function_calling": True,
                "deprecation_date": "2027-03-01",
            },
            "gemini/gemini-3.8-flash": {
                "litellm_provider": "gemini",
                "mode": "chat",
                "input_cost_per_token": 7.5e-07,
                "output_cost_per_token": 3.75e-06,
            },
            "azure/gpt-6-luna": {"litellm_provider": "azure", "mode": "chat"},  # a reseller's
            "text-embedding-3-small": {"litellm_provider": "openai", "mode": "embedding"},
            "ft:gpt-5-mini": {"litellm_provider": "openai", "mode": "chat"},
            "sample_spec": "not a model",
        }
    )
    assert litellm["anthropic"]["claude-opus-5"] == Listed(5.0, 25.0, 0.5, True, "2027-03-01")
    assert litellm["gemini"]["gemini-3.8-flash"].output == 3.75
    assert "openai" not in litellm  # neither the reseller's, an embedding nor a fine-tune

    openrouter = parse_openrouter(
        {
            "data": [
                {
                    "id": "anthropic/claude-sonnet-4.5",
                    "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                    "supported_parameters": ["tools", "max_tokens"],
                    "created": 1759190400,  # 30 September 2025
                },
                {"id": "google/gemini-3.8-flash", "pricing": {"prompt": "0.00000075"}},
                {"id": "openai/gpt-6-luna:free", "pricing": {"prompt": "0"}},
                {"id": "mistralai/mistral-large", "pricing": {"prompt": "0.000002"}},
            ]
        }
    )
    assert openrouter["anthropic"]["claude-sonnet-4-5"] == Listed(
        3.0, 15.0, None, True, None, released="2025-09-30"
    )
    assert openrouter["gemini"]["gemini-3.8-flash"].output is None
    assert "openai" not in openrouter  # OpenRouter's own free offer is not the company's price
    with pytest.raises(PriceListError):
        parse_openrouter({"error": "rate limited"})


def test_each_company_is_asked_what_the_key_may_use_and_a_failure_is_no_answer(
    settings, monkeypatch
) -> None:
    from types import SimpleNamespace

    from familydb.agent import providers
    from familydb.agent.providers import anthropic as claude
    from familydb.agent.providers import gemini
    from familydb.agent.providers import openai as oa

    class Client:
        def __init__(self, listed):
            self.models = SimpleNamespace(list=lambda **kwargs: self._list(listed))
            self.closed = False

        @staticmethod
        def _list(listed):
            if isinstance(listed, Exception):
                raise listed
            return listed

        def with_options(self, **options):
            return self

        def close(self):
            self.closed = True

    def ids(*names):
        return [SimpleNamespace(id=name) for name in names]

    keys = {"openai_api_key": "sk-test", "gemini_api_key": "g-test"}
    for module, name, listed, expected in (
        (
            claude,
            "anthropic",
            ids("claude-opus-5", "claude-haiku-4-5"),
            ["claude-opus-5", "claude-haiku-4-5"],
        ),
        (oa, "openai", ids("gpt-6-luna"), ["gpt-6-luna"]),
        (gemini, "gemini", [SimpleNamespace(name="models/gemini-3.8-flash")], ["gemini-3.8-flash"]),
        (oa, "openai", RuntimeError("unreachable"), None),
    ):
        client = Client(listed)
        monkeypatch.setattr(module, "make_client", lambda *args, _c=client, **kwargs: _c)
        provider = providers.build(name, settings.model_copy(update=keys))
        assert provider.listed_models() == expected, name


# -- what is kept, and put in force ----------------------------------------------------------------


def test_the_first_check_learns_what_there_is_and_puts_it_in_force(settings, conn) -> None:
    new_model = {**CLAUDE, "claude-sonnet-6": _listed(1.5, 7.5)}
    counts = model_watch.check(
        _app(settings),
        lists=_both(anthropic=new_model),
        listers=_claude("claude-haiku-4-5", "claude-opus-5", "claude-sonnet-6"),
    )
    assert counts["changes"] == 0  # everything is new the first time, so nothing is told
    assert _alerts(conn) == {}
    assert prices.price("anthropic", "claude-sonnet-6").output == 7.5  # counted at its price
    # Offered cheapest first: listed for the key and priced; Sonnet 5 is not listed for it.
    assert prices.suggestions("anthropic") == (
        "claude-haiku-4-5",
        "claude-sonnet-6",
        "claude-opus-5",
    )
    # A company with no key here is not asked, and what the lists say of it is offered: a model
    # only the built-in table knows of (gpt-5, say) is still counted at its price, not offered.
    assert prices.suggestions("openai") == ("gpt-6-luna", "gpt-6-sol")
    assert prices.price("openai", "gpt-5") is not None

    # Another process picks it up from the store on its next refresh.
    prices.use({}, {})
    assert prices.price("anthropic", "claude-sonnet-6") is None
    _app(settings, hour=9).refresh()
    assert prices.price("anthropic", "claude-sonnet-6").output == 7.5

    # Switched off, the prices this version shipped with are back; on again, what was found.
    App(settings, FixedClock(datetime(2026, 9, 20, 10), TZ)).refresh()  # model_watch off
    assert prices.price("anthropic", "claude-sonnet-6") is None
    assert prices.suggestions("anthropic")[0] == "claude-haiku-4-5"
    _app(settings, hour=11).refresh()
    assert prices.price("anthropic", "claude-sonnet-6").output == 7.5


def test_a_model_no_list_names_any_more_stops_being_offered_after_a_week(settings, conn) -> None:
    model_watch.check(_app(settings, day=1), lists=_both(), listers={})
    assert "gpt-6-sol" in prices.suggestions("openai")
    dropped = _both(openai={"gpt-6-luna": _listed(0.1, 0.5)})
    model_watch.check(_app(settings, day=5), lists=dropped, listers={})
    assert "gpt-6-sol" in prices.suggestions("openai")  # a list may miss a day
    model_watch.check(_app(settings, day=9), lists=dropped, listers={})
    assert prices.suggestions("openai") == ("gpt-6-luna",)
    assert prices.price("openai", "gpt-6-sol").output == 10.0  # still counted if it is used


def test_what_is_offered_is_this_year_s_models_and_the_lineup_not_every_old_one(
    settings, conn
) -> None:
    def out(day: str) -> Listed:
        return Listed(0.5, 1.5, None, True, None, released=day)

    old = {
        "gpt-6-luna": out("2026-06-01"),
        "gpt-6-sol": out("2025-02-01"),  # older than a year, but in this version's lineup
        "gpt-3.5-turbo": out("2023-05-28"),
        "gpt-3.5-turbo-0125": out("2024-01-25"),
        "gpt-7-nova": out("2026-09-01"),
        "gpt-7-nova-0901": out("2026-09-01"),  # a dated copy of the one above
        "chatgpt-4o-latest": out("2026-08-01"),  # an alias that moves
        "gpt-7-nova-instruct": out("2026-09-01"),
    }
    lists = Lists(litellm={"openai": old}, openrouter={"openai": old})
    model_watch.check(_app(settings, day=20), lists=lists, listers={})
    assert set(prices.suggestions("openai")) == {"gpt-6-luna", "gpt-6-sol", "gpt-7-nova"}
    # Every one is still counted at its price, offered or not.
    assert prices.price("openai", "gpt-3.5-turbo").output == 1.5


def test_what_changes_for_the_models_in_use_is_told(settings, conn, family) -> None:
    listers = _claude("claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5")
    model_watch.check(_app(settings, day=20), lists=_both(), listers=listers)

    # The next day Opus costs more, by both lists; Sonnet 6 is new; Haiku is gone for the key.
    dearer = {**CLAUDE, "claude-opus-5": _listed(6.0, 30.0), "claude-sonnet-6": _listed(1.5, 7.5)}
    counts = model_watch.check(
        _app(settings, day=21),
        lists=_both(anthropic=dearer),
        listers=_claude("claude-opus-5", "claude-sonnet-5", "claude-sonnet-6"),
    )
    assert counts["changes"] == 3
    told = _alerts(conn)
    assert (
        "claude-opus-5 (Anthropic) now costs $6 in, $30 out a million tokens, was $5 in, "
        in (told[("price", "anthropic:claude-opus-5:$6 in, $30 out")])
    )
    assert "no longer offers claude-haiku-4-5" in told[("model", "anthropic:claude-haiku-4-5")]
    assert told[("new", "anthropic:2026-09-21")] == "Anthropic: claude-sonnet-6 ($1.5 in, $7.5 out)"
    assert prices.price("anthropic", "claude-opus-5").output == 30.0
    whats = {(c.model, c.what) for c in store.changes_since(conn, since="2000")}
    assert whats == {
        ("claude-opus-5", "price"),
        ("claude-haiku-4-5", "gone"),
        ("claude-sonnet-6", "new"),
    }

    # Haiku back: its notice is forgotten.
    model_watch.check(
        _app(settings, day=22),
        lists=_both(anthropic=dearer),
        listers=_claude("claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5", "claude-sonnet-6"),
    )
    assert ("model", "anthropic:claude-haiku-4-5") not in _alerts(conn)


def test_a_price_the_lists_do_not_agree_on_or_that_leaps_is_held(settings, conn) -> None:
    listers = _claude("claude-haiku-4-5", "claude-opus-5")
    model_watch.check(_app(settings, day=20), lists=_both(), listers=listers)

    odd = Lists(
        litellm={"anthropic": {**CLAUDE, "claude-opus-5": _listed(5.0, 26.0)}},
        openrouter={"anthropic": {**CLAUDE, "claude-opus-5": _listed(5.0, 40.0)}},
    )
    model_watch.check(_app(settings, day=21), lists=odd, listers=listers)
    assert prices.price("anthropic", "claude-opus-5").output == 25.0  # the last good price
    assert (
        "the price lists disagree about claude-opus-5"
        in (_alerts(conn)[("prices", "anthropic:claude-opus-5")])
    )

    # One list alone, the other unreadable, with a price a hundredth of the last: held too.
    leap = Lists(
        litellm={"anthropic": {**CLAUDE, "claude-haiku-4-5": _listed(0.01, 0.05)}},
        openrouter=PriceListError("OpenRouter could not be reached"),
    )
    model_watch.check(_app(settings, day=22), lists=leap, listers=listers)
    assert prices.price("anthropic", "claude-haiku-4-5").output == 5.0
    assert "the old price is kept" in _alerts(conn)[("prices", "anthropic:claude-haiku-4-5")]


def test_a_list_that_cannot_be_read_is_told_of_after_three_days(settings, conn) -> None:
    listers = _claude("claude-haiku-4-5", "claude-opus-5")
    down = Lists(litellm=_both().prices["litellm"], openrouter=PriceListError("HTTP 503"))
    for day in (20, 21):
        model_watch.check(_app(settings, day=day), lists=down, listers=listers)
    assert ("prices", "openrouter") not in _alerts(conn)
    model_watch.check(_app(settings, day=22), lists=down, listers=listers)
    assert "could not be read for 3 days running" in _alerts(conn)[("prices", "openrouter")]
    model_watch.check(_app(settings, day=23), lists=_both(), listers=listers)
    assert ("prices", "openrouter") not in _alerts(conn)  # reading again


def test_a_model_in_use_that_is_going_is_told_of_once_and_again_near_the_day(settings, conn):
    listers = _claude("claude-haiku-4-5", "claude-opus-5")
    model_watch.check(_app(settings, day=1), lists=_both(), listers=listers)
    going = _both(
        anthropic={**CLAUDE, "claude-haiku-4-5": _listed(1.0, 5.0, retires_on="2026-10-01")}
    )
    model_watch.check(_app(settings, day=2), lists=going, listers=listers)
    subject = "anthropic:claude-haiku-4-5:2026-10-01"
    assert (
        _alerts(conn)[("model", subject)]
        == "Anthropic retires claude-haiku-4-5 on 2026-10-01, in 29 days"
    )
    model_watch.check(_app(settings, day=3), lists=going, listers=listers)
    assert len([k for k in _alerts(conn) if k[0] == "model"]) == 1  # not again the next day
    model_watch.check(_app(settings, day=20), lists=going, listers=listers)
    assert ("model", f"{subject}:soon") in _alerts(conn)  # eleven days to go


def test_admins_hear_of_it_on_telegram(settings, conn, family) -> None:
    listers = _claude("claude-haiku-4-5", "claude-opus-5")
    model_watch.check(_app(settings, day=20), lists=_both(), listers=listers)
    model_watch.check(_app(settings, day=21), lists=_both(), listers=_claude("claude-opus-5"))
    app = _app(settings, day=21, hour=6)
    sent: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat, text: sent.append((chat, text))
    app.settings = app.settings.model_copy(update={"admin_alerts": True})
    assert alerts.run_alerts(app) == 1
    assert sent[0][0] == "1001" and sent[0][1].startswith("A model I use is going away: Anthropic")


def test_the_check_is_off_when_the_family_turns_it_off(settings, conn) -> None:
    app = App(settings, FixedClock(datetime(2026, 9, 20, 5), TZ))  # model_watch off
    assert model_watch.check(app, lists=_both(), listers=_claude("claude-opus-5")) == {}
    assert store.all_seen(conn) == {}


def test_a_catch_up_after_a_day_away_checks_again(settings, conn) -> None:
    app = _app(settings, day=20)
    assert model_watch.due(conn, app.clock.now())
    model_watch.check(app, lists=_both(), listers=_claude("claude-opus-5"))
    assert not model_watch.due(conn, app.clock.now() + timedelta(hours=5))
    assert model_watch.due(conn, app.clock.now() + timedelta(hours=24))


# -- on the page -------------------------------------------------------------------------------


def test_the_status_page_says_where_it_read_and_what_changed(settings, conn, family) -> None:
    from familydb.web import create_app

    listers = _claude("claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5")
    model_watch.check(_app(settings, day=20), lists=_both(), listers=listers)
    dearer = {**CLAUDE, "claude-opus-5": _listed(6.0, 30.0), "claude-sonnet-6": _listed(1.5, 7.5)}
    down = Lists(litellm={"anthropic": dearer, "openai": OPENAI}, openrouter=PriceListError("503"))
    more = _claude("claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5", "claude-sonnet-6")
    model_watch.check(_app(settings, day=21), lists=down, listers=more)

    later = _app(settings, day=21, hour=9)
    client = create_app(later).test_client()
    text = client.get("/status").text
    panel = text[text.index('id="models"') : text.index("</section>", text.index('id="models"'))]
    assert "LiteLLM&#39;s price list" in panel and "Read 21 Sep, 05:17" in panel
    assert (
        "OpenRouter&#39;s price list" in panel and "Could not be read 21 Sep, 05:17: 503" in panel
    )
    assert "Anthropic&#39;s list for the key" in panel
    assert "$5 in, $25 out → $6 in, $30 out a million tokens" in panel
    assert "new, $1.5 in, $7.5 out" in panel
    # The price of one in use is a trouble; a new model to choose from is only news.
    attention = text[text.index('id="attention"') : text.index('id="models"')]
    assert "The price of a model in use changed" in attention
    assert "New models to choose from" not in attention

    # And the box to choose one says which is new.
    page = client.get("/settings/model").text
    assert re.search(r'<option value="claude-sonnet-6">[^<]*· new</option>', page)


def test_the_status_page_says_when_the_check_is_off(settings, clock, conn) -> None:
    from familydb.web import create_app

    text = create_app(App(settings, clock)).test_client().get("/status").text
    assert "The daily check is switched off" in text
