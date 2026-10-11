"""An evening's work on her back pocket (docs/FINDS.md, "A night"): a find filled in as an idea is,
by a lookup that may write that find alone, and the pocket judged by a call that may only choose
among the finds it was shown; what it chose is recommended, and what it no longer chooses is
offered as before."""

from __future__ import annotations

import json
from datetime import date

from familydb.integrations.geocode import GeoPoint
from familydb.store import db, finds
from familydb.tools import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO

TODAY = date(2026, 9, 20)

POINT = GeoPoint(45.5262, -122.6836, "Rose garden, Portland", "nominatim")


def _kept(conn, *titles: str) -> list[finds.Find]:
    with db.transaction(conn):
        kept, _ = finds.keep(
            conn,
            "web:near-home",
            "web",
            [finds.NewFind(title=t, url=f"https://x.example/{n}") for n, t in enumerate(titles)],
            now=NOW_ISO,
        )
    return kept


def _call(registry, ctx, tool, **payload):
    result = registry.dispatch(tool, payload, ctx)
    return result, json.loads(result.content)


def test_a_find_is_filled_in_as_an_idea_is_and_only_that_find(
    registry, conn, full_settings, clock
) -> None:
    roses, market = _kept(conn, "Rose garden", "Night market")
    ctx = ToolContext(
        conn=conn,
        settings=full_settings,
        clock=clock,
        geocoder=fakes.FakeGeocoder(default=POINT),
        worker_find_id=roses.id,
    )
    result, said = _call(registry, ctx, "skip_find", find_id=market.id, reason="no")
    assert result.is_error and said["error"] == "worker may only write its assigned find"
    result, said = _call(
        registry,
        ctx,
        "save_find",
        find_id=roses.id,
        name="International Rose Test Garden",
        address="400 SW Kingston Ave, Portland, OR",
        hours=[{"day": "sat", "open": "07:30", "close": "21:00"}],
        setting="outdoor",
        cost_level=0,
        visit_minutes=90,
        min_age=40,
        max_age=3,  # no age range a page could mean: neither is kept
    )
    assert not result.is_error, said
    assert said["geocoded"] is True and said["travel"]["minutes"] > 0
    filled = finds.get(conn, roses.id)
    assert filled.place_id == said["place"]["id"] and filled.filled_at == ctx.now_iso()
    assert (filled.setting, filled.cost_level, filled.duration_min) == ("outdoor", 0, 90)
    assert (filled.min_age, filled.max_age) == (None, None)
    # Tried, it is not tried again; nothing tried is judged until it has been.
    assert [one.id for one in finds.to_fill(conn, today=TODAY, limit=5)] == [market.id]


def test_the_pocket_is_judged_from_what_it_was_shown(registry, conn, settings, clock) -> None:
    roses, market, gig = _kept(conn, "Rose garden", "Night market", "Gig")
    ctx = ToolContext(conn=conn, settings=settings, clock=clock)
    ctx.scratch["pocket"] = [roses.id, market.id]
    result, said = _call(
        registry, ctx, "recommend_finds", picks=[{"find_id": gig.id, "why": "x", "when": "y"}]
    )
    assert result.is_error and "not in the pocket" in said["error"]
    result, said = _call(
        registry,
        ctx,
        "recommend_finds",
        picks=[
            {
                "find_id": roses.id,
                "why": "They loved  the tulips.",
                "when": "a dry afternoon",
                "put_from": "2026-10-10",
                "put_until": "2026-10-01",  # before it starts: no days at all
            }
        ],
    )
    assert said == {"recorded": 1}
    assert ctx.scratch["recommended"] == {
        roses.id: {
            "why": "They loved the tulips.",
            "when": "a dry afternoon",
            "put_from": None,
            "put_until": None,
        }
    }


def test_judging_recommends_and_lets_go_of_what_it_no_longer_chooses(conn) -> None:
    roses, market = _kept(conn, "Rose garden", "Night market")
    assert finds.judging_due(conn, today=TODAY)
    with db.transaction(conn):
        finds.judged(conn, [roses.id, market.id], {roses.id: {"why": "w", "when": "soon"}}, now="1")
    assert (finds.get(conn, roses.id).state, finds.get(conn, market.id).state) == (
        "recommended",
        "new",
    )
    assert not finds.judging_due(conn, today=TODAY)
    with db.transaction(conn):
        finds.mark_filled(conn, market.id, place_id=None, facts={}, note="n", now="2")
    assert finds.judging_due(conn, today=TODAY)  # filled in since it was judged
    with db.transaction(conn):
        finds.judged(conn, [roses.id, market.id], {market.id: {"why": "w", "when": "now"}}, now="3")
    again = finds.get(conn, roses.id)
    assert (again.state, again.judged_why) == ("new", None)
    assert finds.get(conn, market.id).state == "recommended"
