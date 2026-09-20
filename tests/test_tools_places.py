import json

from familydb.integrations.geocode import GeoPoint
from familydb.store import db, ideas, places
from familydb.tools import ToolContext
from tests import fakes
from tests.conftest import NOW_ISO

POINT = GeoPoint(45.5262, -122.6836, "Hopscotch, Portland", "nominatim")


def _ctx(conn, settings, clock, family, geocoder=None) -> ToolContext:
    return ToolContext(
        conn=conn, settings=settings, clock=clock, member=family["sam"], geocoder=geocoder
    )


def _call(registry, ctx, tool_name, **payload):
    result = registry.dispatch(tool_name, payload, ctx)
    return result, json.loads(result.content)


def _idea(conn, title="Hopscotch, Portland", location=None):
    with db.transaction(conn):
        return ideas.insert(conn, title=title, kind="outing", location_name=location, now=NOW_ISO)


def test_save_place_geocodes_estimates_and_marks_done(
    registry, conn, full_settings, clock, family
) -> None:
    idea = _idea(conn)
    geocoder = fakes.FakeGeocoder(default=POINT)
    ctx = _ctx(conn, full_settings, clock, family, geocoder)
    result, data = _call(
        registry,
        ctx,
        "save_place",
        idea_id=idea.id,
        name="Hopscotch Portland",
        summary="Immersive art experience",
        address="1030 NW 12th Ave, Portland, OR",
        website="https://example.com/hopscotch",
        booking_url="https://example.com/tickets",
        hours=[
            {"day": "sat", "open": "10:00", "close": "20:00"},
            {"day": "sat", "open": "21:00", "close": "23:00"},
        ],
        closed_days=["mon"],
        price_note="adults $28",
        source_urls=["https://example.com/hopscotch"],
    )
    assert not result.is_error, data
    assert data["geocoded"] is True and geocoder.queries == ["1030 NW 12th Ave, Portland, OR"]
    assert data["travel"]["estimate"] is True and data["travel"]["minutes"] > 0
    place = data["place"]
    assert place["hours"] == {
        "sat": [{"open": "10:00", "close": "20:00"}, {"open": "21:00", "close": "23:00"}],
        "mon": [],
    }
    assert place["lat"] == 45.5262 and place["last_checked_at"] == ctx.now_iso()
    assert data["idea"]["enrichment"] == "done" and data["idea"]["place_id"] == place["id"]
    assert data["idea"]["location_name"] == "Hopscotch Portland"
    assert result.summary["place_id"] == place["id"] and result.summary["idea_id"] == idea.id


def test_save_place_upserts_by_idea_then_by_name(
    registry, conn, full_settings, clock, family
) -> None:
    idea = _idea(conn)
    ctx = _ctx(conn, full_settings, clock, family, fakes.FakeGeocoder(default=POINT))
    _, first = _call(
        registry, ctx, "save_place", idea_id=idea.id, name="Hopscotch Portland", summary="v1"
    )
    _, second = _call(
        registry, ctx, "save_place", idea_id=idea.id, name="Hopscotch Portland", summary="v2"
    )
    assert second["place"]["id"] == first["place"]["id"] and second["place"]["summary"] == "v2"
    other = _idea(conn, title="Hopscotch again")
    _, third = _call(
        registry, ctx, "save_place", idea_id=other.id, name="hopscotch portland", summary="v3"
    )
    assert third["place"]["id"] == first["place"]["id"]  # same place, reused by name
    assert conn.execute("SELECT COUNT(*) FROM places").fetchone()[0] == 1


def test_save_place_without_geocoder_or_coordinates(
    registry, conn, settings, clock, family
) -> None:
    idea = _idea(conn)
    ctx = _ctx(conn, settings, clock, family, geocoder=None)
    _, data = _call(registry, ctx, "save_place", idea_id=idea.id, name="Somewhere")
    assert data["geocoded"] is False and data["travel"] is None
    assert data["note"] == "no geocoder configured" and data["idea"]["enrichment"] == "done"
    ctx = _ctx(conn, settings, clock, family, fakes.FakeGeocoder())
    _, data = _call(registry, ctx, "save_place", idea_id=idea.id, name="Somewhere")
    assert data["note"] == "could not geocode" and data["place"]["lat"] is None
    result, data = _call(
        registry,
        ctx,
        "save_place",
        idea_id=idea.id,
        name="X",
        hours=[{"day": "sat", "open": "10am", "close": "20:00"}],
    )
    assert result.is_error and "invalid time" in data["error"]


def test_skip_place(registry, conn, settings, clock, family) -> None:
    idea = _idea(conn, title="A picnic somewhere")
    ctx = _ctx(conn, settings, clock, family)
    _, data = _call(
        registry,
        ctx,
        "skip_place",
        idea_id=idea.id,
        status="skipped",
        reason="not a specific place",
    )
    assert data["idea"]["enrichment"] == "skipped"
    assert ideas.get(conn, idea.id).enrichment_note == "not a specific place"
    result, data = _call(registry, ctx, "skip_place", idea_id=999, status="failed", reason="x")
    assert result.is_error and "no idea #999" in data["error"]


def test_check_open_and_lookup(registry, conn, full_settings, clock, family) -> None:
    idea = _idea(conn)
    ctx = _ctx(conn, full_settings, clock, family, fakes.FakeGeocoder(default=POINT))
    _call(
        registry,
        ctx,
        "save_place",
        idea_id=idea.id,
        name="Hopscotch Portland",
        hours=[{"day": "sat", "open": "10:00", "close": "20:00"}],
        closed_days=["sun"],
    )
    _, sat = _call(registry, ctx, "check_open", idea_id=idea.id, date="2026-09-26")
    assert (
        sat["open"] == "open"
        and sat["hours"] == "10:00-20:00"
        and sat["known"]
        and sat["stale"] is False
    )
    _, sun = _call(registry, ctx, "check_open", idea_id=idea.id, date="2026-09-27")
    assert sun["open"] == "closed" and sun["hours"] is None
    _, mon = _call(registry, ctx, "check_open", idea_id=idea.id, date="2026-09-28")
    assert mon["open"] == "unknown" and mon["known"] is False
    _, found = _call(registry, ctx, "lookup_place", idea_id=idea.id)
    assert found["found"] is True and found["place"]["checked_days_ago"] == 0
    _, by_name = _call(registry, ctx, "lookup_place", name="hopscotch portland")
    assert by_name["found"] is True and by_name["idea_id"] is None
    place_id = found["place"]["id"]
    with db.transaction(conn):
        places.update(conn, place_id, {"last_checked_at": "2026-01-01T00:00:00Z"}, now=NOW_ISO)
    _, stale = _call(registry, ctx, "check_open", idea_id=idea.id, date="2026-09-26")
    assert stale["stale"] is True and stale["checked_days_ago"] > 200


def test_lookup_place_queues_missing_details(registry, conn, settings, clock, family) -> None:
    idea = _idea(conn)
    ctx = _ctx(conn, settings, clock, family)
    _, data = _call(registry, ctx, "lookup_place", idea_id=idea.id)
    assert data == {"found": False, "queued": True, "enrichment": "pending", "note": None}
    with db.transaction(conn):
        ideas.update(
            conn, idea.id, {"enrichment": "failed", "enrichment_note": "no luck"}, now=NOW_ISO
        )
    _, data = _call(registry, ctx, "lookup_place", idea_id=idea.id)
    assert data["queued"] is False and data["note"] == "no luck"  # web tools off: nothing re-queued
    web_on = settings.model_copy(update={"web_tools_enabled": True})
    _, data = _call(registry, _ctx(conn, web_on, clock, family), "lookup_place", idea_id=idea.id)
    assert data["queued"] is True and ideas.get(conn, idea.id).enrichment == "pending"
    result, data = _call(registry, ctx, "lookup_place")
    assert result.is_error


def test_save_place_drops_links_that_are_not_web_addresses(
    registry, conn, full_settings, clock, family
) -> None:
    idea = _idea(conn)
    ctx = _ctx(conn, full_settings, clock, family, fakes.FakeGeocoder(default=POINT))
    _, data = _call(
        registry,
        ctx,
        "save_place",
        idea_id=idea.id,
        name="Hopscotch Portland",
        website="javascript:alert(1)",
        booking_url=" https://example.com/tickets ",
        source_urls=["https://example.com/about", "ftp://example.com/x", "not a url"],
    )
    place = data["place"]
    assert place["website"] is None and place["booking_url"] == "https://example.com/tickets"
    assert place["source_urls"] == ["https://example.com/about"]
    assert data["idea"]["enrichment"] == "done"
