"""A daily look at what the calls themselves cost and do, with no model call.

A bill also grows when a model reads more, writes longer, takes more steps, slows or ends badly
more often. Each day the last week of each kind of call is set beside the four weeks before
(`llm_calls`), and a long way moved is told to admins (alerts.py "shift"), at most once in seven
days per kind, naming a changed model. A kind with too few calls to mean anything is left alone.
"""

from __future__ import annotations

from contextlib import closing
from datetime import timedelta
from typing import Any

from familydb import alerts
from familydb.agent import gateway
from familydb.base.dates import utc_iso
from familydb.store import alerts as alert_store
from familydb.store import calls

RECENT_DAYS = 7
BEFORE_DAYS = 28
FEWEST = 20
MORE = 1.5
SLOWER = 2.0
BAD_POINTS = 0.05


def check(app: Any) -> int:
    with closing(app.connect()) as conn:
        now = app.clock.now()
        split = now - timedelta(days=RECENT_DAYS)
        recent = calls.figures_between(conn, since=utc_iso(split), until=utc_iso(now))
        before = calls.figures_between(
            conn, since=utc_iso(split - timedelta(days=BEFORE_DAYS)), until=utc_iso(split)
        )
        lately = alert_store.current(conn, since=utc_iso(split))
        quiet = {alert.subject.split(":")[0] for alert in lately if alert.kind == "shift"}
        told = 0
        for kind, now_is in sorted(recent.items()):
            was = before.get(kind)
            if kind in quiet or was is None or min(now_is["calls"], was["calls"]) < FEWEST:
                continue
            moved = shifts(now_is, was)
            if not moved:
                continue
            if now_is.get("model") and was.get("model") and now_is["model"] != was["model"]:
                moved.append(f"answered mostly by {now_is['model']} now, was {was['model']}")
            alerts.note(
                conn,
                "shift",
                f"{kind}:{now.date().isoformat()}",
                f"{gateway.purpose(kind)}: " + "; ".join(moved),
                now,
                once=True,
            )
            told += 1
        return told


def shifts(now_is: dict[str, Any], was: dict[str, Any]) -> list[str]:
    found: list[str] = []

    def per(figures: dict[str, Any], what: str, by: str) -> float:
        return figures[what] / figures[by] if figures[by] else 0.0

    cost_now, cost_was = per(now_is, "cost", "asks"), per(was, "cost", "asks")
    if _far(cost_now, cost_was, MORE):
        how_much = _how_much(cost_now, cost_was)
        found.append(f"costs {how_much} an answer (${cost_now:.4f}, was ${cost_was:.4f})")
    for what, words in (("sent", "tokens read"), ("back", "tokens written")):
        a, b = per(now_is, what, "calls"), per(was, what, "calls")
        if _far(a, b, MORE):
            found.append(f"{a / b:.1f}x the {words} a call ({a:,.0f}, was {b:,.0f})")
    steps_now, steps_was = per(now_is, "calls", "asks"), per(was, "calls", "asks")
    if _far(steps_now, steps_was, MORE):
        found.append(f"{steps_now:.1f} calls an answer, was {steps_was:.1f}")
    if _far(now_is["ms"], was["ms"], SLOWER):
        found.append(f"{now_is['ms'] / 1000:.1f}s a call, was {was['ms'] / 1000:.1f}s")
    bad_now, bad_was = per(now_is, "bad", "calls"), per(was, "bad", "calls")
    if bad_now - bad_was >= BAD_POINTS and bad_now >= 2 * bad_was:
        found.append(f"{bad_now:.0%} of calls ended badly, was {bad_was:.0%}")
    return found


def _far(now: float, was: float, factor: float) -> bool:
    if not was or not now:
        return False
    return now / was >= factor or now / was <= 1 / factor


def _how_much(now: float, was: float) -> str:
    change = now / was - 1
    return f"{change:.0%} more" if change > 0 else f"{-change:.0%} less"
