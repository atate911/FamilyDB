"""What a model call costs, and the daily limit that stops the next one."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta

import pytest

from familydb.agent import spending
from familydb.agent.providers import prices
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.integrations.geocode import GeoPoint
from familydb.jobs.enrich import run_enrichment
from familydb.pipeline import handle_incoming
from familydb.store import calls, db, ideas, messages
from tests import fakes

# The fixture clock is Sunday 20 September, 14:03 in Vancouver: the family's day began at 07:00Z.
MIDNIGHT_UTC = "2026-09-20T07:00:00Z"


def _telegram(text: str, update_id: str) -> IncomingMessage:
    return IncomingMessage("telegram", update_id, "chat-1", "1001", text)


def _spent(conn, dollars: float, when: str = "2026-09-20T20:00:00Z") -> None:
    with db.transaction(conn):
        calls.log_llm_call(
            conn,
            message_id=None,
            iteration=1,
            model="gpt-6-luna",
            served_model=None,
            request_id=None,
            stop_reason="end",
            usage={},
            duration_ms=1,
            now=when,
            provider="openai",
            cost_usd=dollars,
        )


# -- prices -------------------------------------------------------------------------------------


def test_a_dated_snapshot_costs_what_its_family_does() -> None:
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    dollars, listed = prices.cost("anthropic", "claude-haiku-4-5-20251001", usage)
    assert listed and dollars == pytest.approx(6.0)


def test_luna_counts_its_cache_and_its_searches() -> None:
    usage = {
        "input_tokens": 2_000_000,
        "cache_read_input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "web_searches": 3,
    }
    dollars, listed = prices.cost("openai", "gpt-6-luna", usage)
    assert listed and dollars == pytest.approx(0.20 + 0.01 + 0.50 + 0.03)


def test_an_unlisted_model_is_counted_dearer_than_any_listed_one() -> None:
    # gpt-5.6-luna is a real model, but not gpt-5 by another name: it must not match that prefix.
    dollars, listed = prices.cost("openai", "gpt-5.6-luna", {"output_tokens": 1_000_000})
    dearest = max(price.output for table in prices.PRICES.values() for price in table.values())
    assert not listed and dollars > dearest


def test_a_claude_cache_write_costs_by_how_long_it_lasts() -> None:
    usage = {"cache_creation_input_tokens": 1_000_000}
    assert prices.cost("anthropic", "claude-sonnet-5", usage, cache_ttl="1h")[0] == 4.0
    assert prices.cost("anthropic", "claude-sonnet-5", usage, cache_ttl="5m")[0] == 2.5


def test_the_page_suggests_the_cheapest_first() -> None:
    assert prices.suggestions("openai")[0] == "gpt-6-luna"


def test_every_call_records_who_answered_and_what_it_cost(settings, clock, conn, family) -> None:
    api = fakes.FakeMessagesAPI(
        fakes.message([fakes.text("Hi Sam.")], usage={"input_tokens": 1000, "output_tokens": 100})
    )
    handle_incoming(App(settings, clock), _telegram("hello", "1"), api=api, conn=conn)
    row = calls.recent_llm_calls(conn)[0]
    assert row["provider"] == "anthropic"
    assert row["cost_usd"] == pytest.approx((1000 * 5.0 + 100 * 25.0) / 1_000_000)
    assert row["cost_estimated"] == 0


def test_an_openai_call_counts_its_searches(settings, clock, conn, family) -> None:
    from familydb.agent.providers.openai import OpenAIProvider

    reply = OpenAIProvider(settings).reply(
        fakes.oa_response([fakes.oa_web_call("ws_1"), fakes.oa_web_call("ws_2")])
    )
    assert reply.usage["web_searches"] == 2


# -- the daily limit ----------------------------------------------------------------------------


def test_the_day_is_the_family_s(settings, clock, conn) -> None:
    _spent(conn, 50.0, when="2026-09-20T06:59:00Z")  # 23:59 the night before, in Vancouver
    assert spending.spent_today(conn, settings, clock.now()) == 0
    _spent(conn, 1.25, when=MIDNIGHT_UTC)
    assert spending.spent_today(conn, settings, clock.now()) == pytest.approx(1.25)


def test_a_used_up_limit_stops_the_call_and_says_why(settings, clock, conn, family) -> None:
    _spent(conn, settings.daily_spend_limit)
    api = fakes.FakeMessagesAPI()  # any request would fail the test: none is scripted
    reply = handle_incoming(App(settings, clock), _telegram("what now?", "2"), api=api, conn=conn)
    assert api.requests == []
    assert reply is not None and reply.status == "failed"
    assert "spending limit" in reply.text and "$2.00" in reply.text
    assert messages.get(conn, reply.in_message_id).give_up


def test_zero_means_no_limit(settings, clock, conn, family) -> None:
    _spent(conn, 1000.0)
    unlimited = settings.model_copy(update={"daily_spend_limit": 0})
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Still here.")]))
    reply = handle_incoming(App(unlimited, clock), _telegram("hi", "3"), api=api, conn=conn)
    assert reply is not None and reply.text == "Still here."


def test_lookups_wait_for_tomorrow_rather_than_fail(settings, clock, conn, family) -> None:
    configured = settings.model_copy(
        update={"web_tools_enabled": True, "home_lat": 45.63, "home_lon": -122.67}
    )
    app = App(
        configured,
        clock,
        geocoder=fakes.FakeGeocoder(default=GeoPoint(45.5, -122.6, "Hopscotch", "nominatim")),
    )
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Hopscotch, Portland", kind="outing", now=MIDNIGHT_UTC)
    _spent(conn, configured.daily_spend_limit)
    api = fakes.FakeMessagesAPI()
    counts = run_enrichment(app, api=api)
    assert api.requests == [] and counts["failed"] == 0
    assert idea.id in [pending.id for pending in ideas.pending_enrichment(conn, limit=10)]


def test_spending_limit_after_write_reports_saved_idea(settings, conn, clock, family):
    limited = settings.model_copy(update={"daily_spend_limit": 0.001})
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "tool_review", "add_idea", {"title": "Budget crossing idea", "kind": "outing"}
                )
            ],
            usage={"input_tokens": 1000, "output_tokens": 100},
        )
    )
    reply = handle_incoming(
        App(limited, clock),
        IncomingMessage("telegram", "budget", "chat", "1001", "save an idea"),
        api=api,
        conn=conn,
    )
    assert ideas.list_all(conn)[0].title == "Budget crossing idea"
    assert "Saved idea #1" in reply.text and "Ask again" not in reply.text
    assert messages.get(conn, reply.in_message_id).status == "processed"
    assert reply.actions[0]["tool"] == "add_idea"


def test_budget_interruption_reports_calendar_success(calendar_settings, conn, clock, family):
    limited = calendar_settings.model_copy(update={"daily_spend_limit": 0.001})
    calendar = fakes.FakeCalendar(clock.tz)
    app = App(limited, clock, calendar=calendar)
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "calendar_review",
                    "create_event",
                    {"title": "Festival", "start": "2026-09-26T10:00"},
                )
            ],
            usage={"input_tokens": 1000, "output_tokens": 100},
        )
    )
    first = handle_incoming(
        app,
        IncomingMessage("telegram", "first", "chat", "1001", "schedule festival"),
        api=api,
        conn=conn,
    )
    assert "Created calendar plan #1" in first.text and len(calendar.events) == 1
    assert "nothing happens twice" in first.text  # Vera's line for it (personas/default/lines.toml)
    assert messages.get(conn, first.in_message_id).status == "processed"
    assert len(api.requests) == 1


# -- what a call in flight holds back -----------------------------------------------------------


def test_concurrent_model_calls_cannot_spend_same_remaining_allowance(
    settings, conn, clock, family
):
    limited = settings.model_copy(update={"daily_spend_limit": 0.001})
    app = App(limited, clock)
    entered, release = threading.Event(), threading.Event()

    class SlowAPI:
        requests = 0

        def create(self, **kwargs):
            self.requests += 1
            entered.set()
            assert release.wait(10)
            return fakes.message(
                [fakes.text("Answered.")], usage={"input_tokens": 1000, "output_tokens": 100}
            )

    api = SlowAPI()

    def ask(number):
        return handle_incoming(
            app, IncomingMessage("telegram", str(number), "chat", "1001", "hello"), api=api
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(ask, 1)
        assert entered.wait(10)
        others = [pool.submit(ask, number) for number in (2, 3)]
        release.set()
        results = [first.result(), *(future.result() for future in others)]
    assert api.requests == 1
    assert sum(result.status == "ok" for result in results) == 1
    assert sum("spending limit" in result.text for result in results) == 2


def test_a_slow_call_does_not_hold_up_the_others(settings, conn, clock, family):
    app = App(settings, clock)
    first_in, second_done = threading.Event(), threading.Event()

    class SlowFirst:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                first_in.set()
                # The second call must finish while this one is still waiting on the network.
                assert second_done.wait(10)
            return fakes.message([fakes.text("Answered.")])

    api = SlowFirst()

    def ask(number):
        reply = handle_incoming(
            app, IncomingMessage("telegram", str(number), "chat", "1001", "hello"), api=api
        )
        if number == 2:
            second_done.set()
        return reply

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(ask, 1)
        assert first_in.wait(10)
        second = pool.submit(ask, 2)
        assert second.result(timeout=10).status == "ok"
        assert first.result(timeout=10).status == "ok"
    with closing(db.connect(settings.familydb_path)) as check:
        assert check.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0


def test_holds_are_given_back_and_a_crashed_one_expires(settings, conn, clock):
    limited = settings.model_copy(update={"daily_spend_limit": 1.0})
    now = clock.now()
    crashed = spending.admit(conn, limited, now - timedelta(minutes=40), 5.0)
    assert crashed
    # Forty minutes old: longer than any call runs, so it no longer counts.
    held = spending.admit(conn, limited, now, 5.0)
    # This one is in flight and holds more than the limit, so the next is refused.
    with pytest.raises(spending.SpendingLimitReached):
        spending.admit(conn, limited, now, 0.01)
    with db.transaction(conn):
        spending.settle(conn, held, now)
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0
    assert spending.admit(conn, limited, now, 0.01)


def test_a_failed_call_gives_its_hold_back(settings, conn, clock, family):
    class Down:
        def create(self, **kwargs):
            raise fakes.server_error()

    app = App(settings, clock)
    reply = handle_incoming(
        app, IncomingMessage("telegram", "down", "chat", "1001", "hello"), api=Down(), conn=conn
    )
    assert reply.status != "ok"
    assert conn.execute("SELECT count(*) FROM spend_holds").fetchone()[0] == 0
