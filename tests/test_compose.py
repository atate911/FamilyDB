"""The composer: requests built from labelled parts, and what each part is found to cost."""

from __future__ import annotations

import json

from familydb.agent import compose, gateway
from familydb.agent.prompt import chat_prefix
from familydb.agent.worker import run_worker_turn
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.pipeline import handle_incoming
from familydb.store import ideas
from familydb.store.db import transaction
from familydb.web import create_app
from tests import fakes


def _sections(conn) -> list[dict[str, int]]:
    rows = conn.execute("SELECT sections FROM llm_calls ORDER BY id").fetchall()
    return [json.loads(row[0]) for row in rows]


def _say(app, conn, text: str, update: str, *replies) -> None:
    api = fakes.FakeMessagesAPI(*replies)
    handle_incoming(app, IncomingMessage("telegram", update, "c", "1001", text), api=api, conn=conn)


def test_each_chat_call_records_the_size_of_every_part(settings, clock, conn, family) -> None:
    with transaction(conn):
        ideas.insert(conn, title="Ramen place", kind="restaurant")
    app = App(settings, clock)
    _say(app, conn, "hello", "1", fakes.message([fakes.text("Hi.")]))
    _say(
        app,
        conn,
        "what's on the list?",
        "2",
        fakes.message(
            [fakes.tool_use("t1", "search_ideas", {"query": "ramen"})], stop_reason="tool_use"
        ),
        fakes.message([fakes.text("The ramen place.")]),
    )
    first, second, third = _sections(conn)
    instructions, family_text, idea_list = chat_prefix(conn, settings)
    assert first["instructions"] == len(instructions)
    assert first["family"] == len(family_text) and first["ideas"] == len(idea_list)
    assert first["tools"] > 1000 and first["message"] > len("hello")
    assert "history" not in first  # nothing said before it
    assert second["history"] > 0  # "hello" and "Hi." came before
    assert "earlier steps" not in second
    assert third["earlier steps"] > 0  # the search and its result are sent again


def test_a_lookup_records_its_own_parts(settings, clock, conn, registry, family) -> None:
    with transaction(conn):
        idea = ideas.insert(conn, title="Hopscotch, Portland", kind="outing")
    api = fakes.FakeMessagesAPI(*fakes.enrich_script({"idea_id": idea.id, "name": "Hopscotch"}))
    run_worker_turn(
        kind="enrich",
        api=api,
        settings=settings,
        clock=clock,
        registry=registry,
        conn=conn,
        request="Idea #1: Hopscotch, Portland",
        geocoder=fakes.FakeGeocoder(),
        idea_id=idea.id,
    )
    first = _sections(conn)[0]
    assert set(first) == {"instructions", "home", "tools", "message"}


def test_the_real_total_is_shared_out_by_size() -> None:
    rows = [
        {"sections": json.dumps({"ideas": 300, "tools": 100}), "sent": 1000},
        {"sections": json.dumps({"ideas": 100, "tools": 100}), "sent": 600},
        {"sections": None, "sent": 5000},  # an older call, measured before sections were
    ]
    ideas_part, tools_part = compose.breakdown(rows)
    assert ideas_part["section"] == "ideas" and ideas_part["label"] == "the idea list"
    assert ideas_part["tokens"] == (750 + 300) // 2 and tools_part["tokens"] == (250 + 300) // 2
    assert ideas_part["share"] + tools_part["share"] == 100
    assert ideas_part["calls"] == 2
    assert compose.breakdown([]) == []


def test_the_status_page_says_where_the_input_went(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    _say(app, conn, "hello", "1", fakes.message([fakes.text("Hi.")]))
    page = create_app(app).test_client().get("/status").text
    assert "Where the input of answering the family went" in page
    assert "tool definitions" in page and "the idea list" in page
    assert gateway.KINDS["chat"].purpose == "answering the family"
