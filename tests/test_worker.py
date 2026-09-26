from familydb.agent.prompt import load_prompt
from familydb.agent.worker import home_location, run_worker_turn
from familydb.integrations.geocode import GeoPoint
from familydb.store import ideas
from tests import fakes
from tests.conftest import call
from tests.fakes import FakeMessagesAPI, message, text, tool_use

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
        conn.execute("SELECT COUNT(*) FROM llm_calls WHERE message_id IS NULL").fetchone()[0] == 2
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
    assert turn.result.iterations == 2  # paused web turn, then the hand-back ends it


def test_worker_budget_is_separate_from_the_chat_budget(settings, clock, conn, registry) -> None:
    capped = settings.model_copy(update={"worker_max_iterations": 2, "agent_max_iterations": 8})
    # A hand-back that fails goes back to the model, so this one loops until the cap.
    looping = fakes.message(
        [fakes.tool_use("tu", "report_finds", {"finds": "not a list"})], stop_reason="tool_use"
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


def test_worker_turns_use_the_cheaper_model_and_less_thinking(settings, clock, conn, registry):
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("done")]))
    _run("enrich", api, settings, clock, registry, conn)
    request = api.requests[0]
    assert request["model"] == settings.worker_model == "claude-haiku-4-5"
    assert "output_config" not in request and "thinking" not in request
    assert request["model"] != settings.anthropic_model  # chat keeps the bigger one

    # An empty WORKER_MODEL means "use the chat model for these too".
    same = settings.model_copy(update={"worker_model": "", "worker_effort": "medium"})
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("done")]))
    _run("enrich", api, same, clock, registry, conn)
    assert api.requests[0]["model"] == same.anthropic_model


def test_a_hand_back_ends_the_turn_and_a_failed_one_goes_back(
    settings, clock, conn, registry
) -> None:
    from familydb.store.db import transaction

    with transaction(conn):
        idea = ideas.insert(conn, title="A picnic", kind="outing", now="2026-09-20T21:03:00Z")

    def skip(idea_id):
        args = {"idea_id": idea_id, "status": "skipped", "reason": "not a place"}
        return fakes.message([fakes.tool_use("tu", "skip_place", args)], stop_reason="tool_use")

    # The first hand-back names no idea and fails: that goes back to the model. The second
    # succeeds and ends the turn; the text queued after it is never asked for.
    api = fakes.FakeMessagesAPI(skip(999), skip(idea.id), fakes.message([fakes.text("Done.")]))
    turn = _run("enrich", api, settings, clock, registry, conn)
    assert turn.result.status == "ok" and turn.handed_back("skip_place")
    assert len(api.requests) == 2 and turn.result.iterations == 2
    assert api.requests[1]["messages"][-1]["content"][0]["is_error"] is True
    assert ideas.get(conn, idea.id).enrichment == "skipped"


def test_workers_get_a_small_output_cap(settings, clock, conn, registry) -> None:
    from familydb.agent.gateway import WORKER_MAX_TOKENS

    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("done")]))
    _run("discover", api, settings, clock, registry, conn)
    assert api.requests[0]["max_tokens"] == WORKER_MAX_TOKENS < settings.max_output_tokens
    # Never above the ceiling set for every call.
    low = settings.model_copy(update={"max_output_tokens": 1000})
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("done")]))
    _run("enrich", api, low, clock, registry, conn)
    assert api.requests[0]["max_tokens"] == 1000


def test_worker_rejects_undeclared_mutation_and_wrong_idea(env):
    _, data = call(env, "add_idea", title="Keep this idea", kind="activity")
    for name, args in [
        ("update_idea", {"id": data["id"], "status": "dropped"}),
        ("skip_place", {"idea_id": data["id"], "status": "skipped", "reason": "wrong"}),
    ]:
        api = FakeMessagesAPI(
            message([tool_use("injected", name, args)], stop_reason="tool_use"),
            message([text("Done")]),
        )
        turn = run_worker_turn(
            kind="enrich",
            api=api,
            settings=env.settings,
            clock=env.app.clock,
            registry=env.registry,
            conn=env.conn,
            request="Look up another venue",
            idea_id=999,
        )
        assert not turn.result.actions[0]["ok"]
        assert ideas.get(env.conn, data["id"]).status == "idea"
        assert ideas.get(env.conn, data["id"]).enrichment == "pending"
