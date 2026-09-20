"""The console channel: talk to the bot from a terminal through the same pipeline as a chat app."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from uuid import uuid4

from familydb.agent.loop import MessagesAPI
from familydb.agent.render import render_idea_line
from familydb.app import App
from familydb.channels.base import IncomingMessage, OutgoingMessage
from familydb.pipeline import handle_incoming
from familydb.store import ideas

CHANNEL = "console"
DEFAULT_CHAT = "console"
HELP = "Commands: /as NAME to speak as someone else, /ideas to list ideas, /quit to leave."


def incoming(text: str, member_name: str, chat_id: str = DEFAULT_CHAT) -> IncomingMessage:
    """Console messages identify the sender by display name and never repeat an update id."""
    return IncomingMessage(
        channel=CHANNEL,
        channel_update_id=uuid4().hex,
        chat_id=chat_id,
        channel_user_id=member_name,
        text=text,
    )


def one_shot(
    app: App,
    text: str,
    member_name: str,
    chat_id: str = DEFAULT_CHAT,
    *,
    api: MessagesAPI | None = None,
) -> OutgoingMessage | None:
    return handle_incoming(app, incoming(text, member_name, chat_id), api=api)


def run_repl(
    app: App,
    member_name: str,
    chat_id: str = DEFAULT_CHAT,
    *,
    api: MessagesAPI | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """A read-eval-print loop over the pipeline. `input_fn` and `output_fn` exist for tests."""
    current = member_name
    output_fn(f"FamilyDB console. Talking as {current}. {HELP}")
    while True:
        try:
            line = input_fn(f"{current}> ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            return
        if not line:
            continue
        if line in {"/quit", "/exit", "/q"}:
            return
        if line.startswith("/as "):
            current = line[4:].strip() or current
            output_fn(f"now talking as {current}")
            continue
        if line == "/ideas":
            with closing(app.connect()) as conn:
                rows = ideas.list_all(conn)
            output_fn("\n".join(render_idea_line(idea) for idea in rows) or "(no ideas yet)")
            continue
        reply = one_shot(app, line, current, chat_id, api=api)
        output_fn(reply.text if reply else "(duplicate message ignored)")
