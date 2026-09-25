"""The one door to a model: every turn goes through `agent.gateway.ask`, declared by kind."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from familydb.agent import compose, gateway
from familydb.agent.prompt import load_prompt
from familydb.agent.worker import run_worker_turn, worker_turn
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.channels.console import one_shot
from familydb.jobs.enrich import render_enrich_request
from familydb.pipeline import handle_incoming, handle_synthetic, retry_message
from familydb.store import ideas
from familydb.store.db import transaction
from tests import fakes

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "familydb"


def _calls_named(tree: ast.AST, name: str, *, methods_only: bool = False) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                called = func.attr
            else:
                called = None if methods_only else getattr(func, "id", None)
            if called == name:
                lines.append(node.lineno)
    return lines


def test_nothing_but_the_gateway_starts_a_turn() -> None:
    """A model call made anywhere else would escape the declarations, and the kind records."""
    starts, sends, hears = [], [], []
    for path in sorted(PACKAGE.rglob("*.py")):
        where = path.relative_to(PACKAGE).as_posix()
        tree = ast.parse(path.read_text("utf-8"))
        starts += [f"{where}:{line}" for line in _calls_named(tree, "run_turn")]
        hears += [f"{where}:{line}" for line in _calls_named(tree, "transcribe", methods_only=True)]
        if where != "agent/loop.py" and not where.startswith("agent/providers/"):
            # provider.send(request); a channel's `send(chat_id, text)` is a plain function
            sends += [f"{where}:{line}" for line in _calls_named(tree, "send", methods_only=True)]
    assert [s.split(":")[0] for s in starts] == ["agent/gateway.py"], starts
    assert sends == [], "only the loop sends a request to a provider"
    # Hearing a voice note is paid for too: it goes through the gateway's `listen`, and only there.
    assert [h.split(":")[0] for h in hears] == ["agent/gateway.py"], hears


@pytest.mark.parametrize("kind", sorted(gateway.KINDS))
def test_each_kind_is_declared_whole(kind, registry, settings) -> None:
    call = gateway.spec(kind)
    assert load_prompt(call.prompt)  # the prompt file exists
    assert isinstance(getattr(settings, call.iterations), int)
    if call.effort:
        assert getattr(settings, call.effort)
    specs = {spec.name: spec for spec in registry.specs()}
    if call.tools is None:  # the chat tools: never the ones a worker hands back with
        assert call.web_searches is None and not call.hand_back
        assert all(not specs[t.name].worker_only for t in compose.tool_defs(call, registry))
        # A tool that may close a chat turn is one of the chat's own, and writes something.
        assert all(specs[name].writes and not specs[name].worker_only for name in call.closes)
    else:  # a worker: its own tools, its hand-back among them, and a cap on the web
        assert set(call.tools) <= set(specs) and set(call.hand_back) <= set(call.tools)
        assert all(specs[name].worker_only for name in call.tools)
        assert call.web_searches and call.surface == "worker"


def _kinds(conn) -> list[str]:
    return [row[0] for row in conn.execute("SELECT kind FROM llm_calls ORDER BY id")]


def test_chat_digest_and_retry_are_recorded_by_kind(settings, clock, conn, family) -> None:
    app = App(settings, clock)
    answer = fakes.FakeMessagesAPI(fakes.message([fakes.text("Sounds good.")]))
    handle_incoming(app, IncomingMessage("telegram", "1", "c", "1001", "hi"), api=answer, conn=conn)
    digest = IncomingMessage("telegram", "digest:2026-09-24", "-100", "1001", "Weekend digest")
    again = fakes.FakeMessagesAPI(fakes.message([fakes.text("Here is the weekend.")]))
    handle_synthetic(app, digest, family["sam"], api=again, conn=conn)

    failed = one_shot(
        app, "anything on?", "Sam", api=fakes.FakeMessagesAPI(fakes.rate_limit_error())
    )
    app.senders["console"] = lambda chat_id, text: None
    later = fakes.FakeMessagesAPI(fakes.message([fakes.text("Sorry for the wait.")]))
    retry_message(app, failed.in_message_id, api=later, conn=conn)
    assert _kinds(conn) == ["chat", "digest", "retry"]  # the failed call was never answered


def test_a_lookup_is_recorded_as_one_and_sends_what_debug_prompt_shows(
    settings, clock, conn, registry, family
) -> None:
    with transaction(conn):
        idea = ideas.insert(conn, title="Hopscotch, Portland", kind="outing")
    request = render_enrich_request(idea, None, settings)
    api = fakes.FakeMessagesAPI(*fakes.enrich_script({"idea_id": idea.id, "name": "Hopscotch"}))
    turn = run_worker_turn(
        kind="enrich",
        api=api,
        settings=settings,
        clock=clock,
        registry=registry,
        conn=conn,
        request=request,
        geocoder=fakes.FakeGeocoder(),
        idea_id=idea.id,
    )
    assert turn.handed_back() and set(_kinds(conn)) == {"enrich"}

    provider = App(settings, clock).provider("worker", api=api)
    shown = gateway.build_request(
        "enrich",
        conn=conn,
        settings=settings,
        registry=registry,
        provider=provider,
        current=worker_turn(clock, request),
    )
    assert provider.payload(shown.request) == api.requests[0]


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError, match="no such kind"):
        gateway.spec("gossip")
    assert gateway.purpose(None) == "not recorded (older calls)"
    assert gateway.purpose("enrich") == "looking ideas up"


def test_what_was_spent_is_told_apart_by_purpose(settings, clock, conn, family) -> None:
    from familydb.store import calls
    from familydb.web import create_app

    with transaction(conn):
        for kind, dollars in (("enrich", 0.02), ("enrich", 0.01), ("chat", 0.05), (None, 0.5)):
            calls.log_llm_call(
                conn,
                message_id=None,
                iteration=1,
                model="gpt-6-luna",
                served_model=None,
                request_id=None,
                stop_reason="end",
                usage={"input_tokens": 100, "output_tokens": 10},
                duration_ms=1,
                now="2026-09-20T10:00:00Z",
                cost_usd=dollars,
                kind=kind,
            )
    rows = {row["kind"]: row for row in calls.usage_by_kind(conn, since="2026-09-01")}
    assert rows["enrich"]["calls"] == 2 and round(rows["enrich"]["cost_usd"], 2) == 0.03
    assert rows["chat"]["sent"] == 100

    page = create_app(App(settings, clock)).test_client().get("/status").text
    assert "looking ideas up" in page and "answering the family" in page
    assert "not recorded (older calls)" in page
