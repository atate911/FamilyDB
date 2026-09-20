from familydb.agent.prompt import load_prompt
from familydb.agent.worker import home_location, run_worker_turn
from familydb.integrations.geocode import GeoPoint
from familydb.store import ideas
from tests import fakes

POINT = GeoPoint(45.5, -122.6, "Hopscotch", "nominatim")


def _run(kind, api, settings, clock, registry, conn, **kw):
    return run_worker_turn(
        kind=kind,
        api=api,
        settings=settings,
        clock=clock,
        registry=registry,
        conn=conn,
        request="Idea #1: Hopscotch, Portland (outing). Fill in the details.",
        **kw,
    )


def test_enrich_turn_declares_subset_prompt_and_budget(
    settings, clock, conn, registry, family
) -> None:
    from familydb.store.db import transaction

    with transaction(conn):
        idea = ideas.insert(
            conn, title="Hopscotch, Portland", kind="outing", now="2026-09-20T21:03:00Z"
        )
    api = fakes.FakeMessagesAPI(
        *fakes.enrich_script({"idea_id": idea.id, "name": "Hopscotch Portland", "summary": "Art"})
    )
    turn = _run(
        "enrich", api, settings, clock, registry, conn, geocoder=fakes.FakeGeocoder(default=POINT)
    )
    assert settings.web_tools_enabled is False  # the chat agent has no web tools...
    request = api.requests[0]
    assert [t["name"] for t in request["tools"]] == [
        "save_place",
        "skip_place",
        "web_search",
        "web_fetch",
    ]
    assert request["tools"][2]["max_uses"] == 3 and request["tools"][3]["max_uses"] == 3
    assert request["system"][0]["text"] == load_prompt("enrich")
    assert "cache_control" in request["system"][0] and "Home area" in request["system"][1]["text"]
    assert request["messages"][0]["content"][1]["text"].startswith("Idea #1")
    assert turn.result.status == "ok" and turn.handed_back("save_place")
    assert not turn.handed_back("skip_place")
    assert ideas.get(conn, idea.id).enrichment == "done"
    assert (
        conn.execute("SELECT COUNT(*) FROM llm_calls WHERE message_id IS NULL").fetchone()[0] == 3
    )


def test_discover_turn_collects_finds(settings, clock, conn, registry) -> None:
    finds = [
        {
            "title": "Harvest Festival",
            "url": "https://example.com/harvest",
            "dates": "Sat 26 Sep",
            "summary": "Free entry.",
        },
        {
            "title": "Duplicate",
            "url": "https://example.com/HARVEST",
            "dates": None,
            "summary": "Same page.",
        },
        {"title": "Bad link", "url": "javascript:alert(1)", "dates": None, "summary": "Nope."},
    ]
    api = fakes.FakeMessagesAPI(*fakes.discover_script(finds))
    location = {
        "type": "approximate",
        "city": "Vancouver",
        "region": "WA",
        "timezone": "America/Vancouver",
    }
    turn = _run("discover", api, settings, clock, registry, conn, user_location=location)
    request = api.requests[0]
    assert [t["name"] for t in request["tools"]] == ["report_finds", "web_search", "web_fetch"]
    assert request["tools"][1]["user_location"] == location
    assert request["system"][0]["text"] == load_prompt("discover")
    assert turn.result.status == "ok" and turn.handed_back("report_finds")
    assert turn.ctx.scratch["finds"] == [
        {
            "title": "Harvest Festival",
            "url": "https://example.com/harvest",
            "dates": "Sat 26 Sep",
            "summary": "Free entry.",
            "source": "example.com",
        }
    ]
    assert turn.result.iterations == 3  # paused web turn, hand-back, final text


def test_worker_budget_is_separate_from_the_chat_budget(settings, clock, conn, registry) -> None:
    capped = settings.model_copy(update={"worker_max_iterations": 2, "agent_max_iterations": 8})
    looping = fakes.message(
        [fakes.tool_use("tu", "report_finds", {"finds": []})], stop_reason="tool_use"
    )
    api = fakes.FakeMessagesAPI(looping, looping, looping)
    turn = _run("discover", api, capped, clock, registry, conn)
    assert turn.result.status == "failed" and turn.result.error == "max_iterations"
    assert len(api.requests) == 2


def test_home_location(settings) -> None:
    assert home_location(settings) is None
    located = settings.model_copy(update={"home_area": "Vancouver, WA"})
    assert home_location(located) == {
        "type": "approximate",
        "city": "Vancouver",
        "region": "WA",
        "timezone": "America/Vancouver",
    }
    assert (
        home_location(settings.model_copy(update={"home_area": "Portland"}))["city"] == "Portland"
    )
