import json

from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.channels.console import one_shot, run_repl
from familydb.pipeline import CONFIG_REPLY, RETRY_REPLY, handle_incoming
from familydb.store import calls, ideas, messages
from tests import fakes


def _app(settings, clock) -> App:
    return App(settings, clock)


def _telegram(text: str, update_id: str, user_id: str = "1001") -> IncomingMessage:
    return IncomingMessage("telegram", update_id, "chat-1", user_id, text)


def test_happy_path_persists_everything(settings, clock, conn, family) -> None:
    app = _app(settings, clock)
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "add_idea", {"title": "Ramen place", "kind": "restaurant"})],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("Saved 🍜 #1 Ramen place.")]),
    )
    reply = handle_incoming(
        app, _telegram("we should try the ramen place", "42"), api=api, conn=conn
    )
    assert reply is not None
    assert reply.status == "ok"
    assert reply.text == "Saved 🍜 #1 Ramen place."
    assert reply.actions == [{"tool": "add_idea", "ok": True, "id": 1}]
    inbound = messages.get(conn, reply.in_message_id)
    outbound = messages.get(conn, reply.out_message_id)
    assert inbound.status == "processed"
    assert inbound.actions == reply.actions
    assert inbound.member_id == family["sam"].id
    assert outbound.reply_to == inbound.id and outbound.direction == "out"
    assert ideas.get(conn, 1).source_message_id == inbound.id
    assert ideas.get(conn, 1).suggested_by == family["sam"].id
    assert len(calls.recent_llm_calls(conn)) == 2
    logged = calls.tool_calls_for_message(conn, inbound.id)
    assert [t["tool_name"] for t in logged] == ["add_idea"]
    # the request carried the sender's name and the date line
    first_user = api.requests[0]["messages"][0]["content"]
    assert first_user[1]["text"] == "[Sam] we should try the ramen place"
    assert first_user[0]["text"].startswith("Today is Sunday 20 September 2026")


def test_duplicate_update_is_ignored(settings, clock, conn, family) -> None:
    app = _app(settings, clock)
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("ok")]))
    assert handle_incoming(app, _telegram("hi", "7"), api=api, conn=conn) is not None
    assert handle_incoming(app, _telegram("hi", "7"), api=api, conn=conn) is None
    assert len(api.requests) == 1


def test_unknown_sender_is_refused_and_not_stored(settings, clock, conn, family) -> None:
    app = _app(settings, clock)
    api = fakes.FakeMessagesAPI()
    reply = handle_incoming(app, _telegram("let me in", "8", user_id="5555"), api=api, conn=conn)
    assert reply.status == "unknown_sender"
    assert "5555" in reply.text
    assert api.requests == []
    assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_api_failure_keeps_the_message_and_replies(settings, clock, conn, family) -> None:
    app = _app(settings, clock)
    api = fakes.FakeMessagesAPI(fakes.rate_limit_error())
    reply = handle_incoming(app, _telegram("we should go hiking", "9"), api=api, conn=conn)
    assert reply.status == "failed"
    assert reply.text == RETRY_REPLY
    inbound = messages.get(conn, reply.in_message_id)
    assert inbound.status == "failed"
    assert "rate limited" in inbound.error
    assert [m.id for m in messages.failed(conn)] == [inbound.id]
    assert messages.get(conn, reply.out_message_id).text == RETRY_REPLY


def test_history_carries_across_turns(settings, clock, conn, family) -> None:
    app = _app(settings, clock)
    api = fakes.FakeMessagesAPI(
        fakes.message([fakes.text("Saved #1.")]),
        fakes.message([fakes.text("#1 is the ramen place.")]),
    )
    first = one_shot(app, "we should try the ramen place", "Sam", api=api)
    second = one_shot(app, "tell me about the first one", "alex", api=api)
    assert first.status == "ok" and second.status == "ok"
    transcript = api.requests[1]["messages"]
    assert [m["role"] for m in transcript] == ["user", "assistant", "user"]
    assert transcript[0]["content"] == "[Sam] we should try the ramen place"
    assert transcript[1]["content"] == "Saved #1."
    assert transcript[2]["content"][1]["text"] == "[Alex] tell me about the first one"


def test_refusal_is_a_processed_turn(settings, clock, conn, family) -> None:
    app = _app(settings, clock)
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [], stop_reason="refusal", stop_details={"type": "refusal", "category": "general_harms"}
        )
    )
    reply = one_shot(app, "something odd", "Sam", api=api)
    assert reply.status == "refused"
    assert messages.get(conn, reply.in_message_id).status == "processed"


def test_repl_commands_and_messages(settings, clock, conn, family) -> None:
    app = _app(settings, clock)
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Hi Alex.")]))
    script = iter(["", "/ideas", "/as Alex", "hello", "/quit"])
    output: list[str] = []
    run_repl(app, "Sam", api=api, input_fn=lambda _prompt: next(script), output_fn=output.append)
    assert output[0].startswith("FamilyDB console. Talking as Sam.")
    assert output[1] == "(no ideas yet)"
    assert output[2] == "now talking as Alex"
    assert output[3] == "Hi Alex."
    assert (
        json.loads(json.dumps(api.requests[0]["messages"][0]["content"]))[1]["text"]
        == "[Alex] hello"
    )


def test_configuration_errors_get_the_admin_reply(settings, clock, conn, family) -> None:
    app = _app(settings, clock)
    api = fakes.FakeMessagesAPI(fakes.bad_request_error())
    reply = handle_incoming(app, _telegram("hi", "10"), api=api, conn=conn)
    assert reply.status == "failed"
    assert reply.text == CONFIG_REPLY
    assert messages.get(conn, reply.in_message_id).status == "failed"
