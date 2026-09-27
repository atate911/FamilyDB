"""The weekly look at what the calls cost and do: a long way moved is told, a little is not."""

from __future__ import annotations

from datetime import datetime, timedelta

from familydb import usage_watch
from familydb.app import App
from familydb.clock import FixedClock
from familydb.dates import utc_iso
from familydb.store import alerts as alert_store
from familydb.store import calls
from familydb.store.db import transaction
from tests.conftest import TZ

NOW = datetime(2026, 9, 27, 5, 17)  # a Sunday


def _calls(conn, *, days_ago: float, count: int, cost: float, model="claude-haiku-4-5", **kw):
    """`count` chat answers of one call each, spread over a day `days_ago` before NOW."""
    start = NOW.replace(tzinfo=TZ) - timedelta(days=days_ago)
    with transaction(conn):
        for n in range(count):
            calls.log_llm_call(
                conn,
                message_id=None,
                iteration=1,
                model=model,
                served_model=None,
                request_id=None,
                stop_reason=kw.get("stop", "end"),
                usage={"input_tokens": kw.get("sent", 2000), "output_tokens": kw.get("back", 80)},
                duration_ms=kw.get("ms", 1500),
                now=utc_iso(start + timedelta(minutes=n)),
                provider="anthropic",
                cost_usd=cost,
                kind="chat",
                turn=f"{days_ago}-{n}",
            )


def _told(conn):
    return {(a.kind, a.subject): a.detail for a in alert_store.current(conn, since="2000")}


def test_an_answer_costing_twice_as_much_on_another_model_is_told_once_a_week(
    settings, conn
) -> None:
    app = App(settings, FixedClock(NOW, TZ))
    _calls(conn, days_ago=20, count=30, cost=0.002)
    _calls(conn, days_ago=3, count=25, cost=0.005, model="claude-sonnet-5", sent=5000)
    assert usage_watch.check(app) == 1
    detail = _told(conn)[("shift", "chat:2026-09-27")]
    assert "costs 150% more an answer ($0.0050, was $0.0020)" in detail
    assert "2.5x the tokens read a call (5,000, was 2,000)" in detail
    assert "answered mostly by claude-sonnet-5 now, was claude-haiku-4-5" in detail
    assert "tokens written" not in detail and "ended badly" not in detail
    # Told at most once in seven days, whatever the calendar week: not the next day, a Monday.
    usage_watch.check(App(settings, FixedClock(NOW + timedelta(days=1), TZ)))
    assert [k for k in _told(conn) if k[0] == "shift"] == [("shift", "chat:2026-09-27")]


def test_a_little_movement_says_nothing(settings, conn) -> None:
    app = App(settings, FixedClock(NOW, TZ))
    _calls(conn, days_ago=20, count=30, cost=0.002)
    _calls(conn, days_ago=3, count=25, cost=0.0025, ms=2000)  # a quarter more: nothing to say
    assert usage_watch.check(app) == 0 and _told(conn) == {}


def test_too_few_calls_to_mean_anything_says_nothing(settings, conn) -> None:
    app = App(settings, FixedClock(NOW, TZ))
    _calls(conn, days_ago=20, count=30, cost=0.002)
    _calls(conn, days_ago=3, count=10, cost=0.01)  # five times the cost, in ten calls
    assert usage_watch.check(app) == 0 and _told(conn) == {}


def test_calls_ending_badly_more_often_is_told(settings, conn) -> None:
    app = App(settings, FixedClock(NOW, TZ))
    _calls(conn, days_ago=20, count=40, cost=0.002)
    _calls(conn, days_ago=3, count=20, cost=0.002)
    _calls(conn, days_ago=3.5, count=5, cost=0.002, stop="max_tokens")
    assert usage_watch.check(app) == 1
    assert "20% of calls ended badly, was 0%" in _told(conn)[("shift", "chat:2026-09-27")]
