"""A model call in words, for the Troubleshooting pages: what was sent and what came back, as an
admin would read it. Kept by `store/ai_texts.py` for `keep_ai_text_days`; recording it never
breaks a turn."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime

from familydb import logs
from familydb.agent.providers.base import ModelReply, TurnRequest
from familydb.base.config import Settings
from familydb.store import ai_texts, problems
from familydb.store.db import transaction

log = logging.getLogger(__name__)

RULE = "\n\n──────── next part ────────\n\n"


def system_text(request: TurnRequest) -> str:
    return RULE.join(block.text for block in request.system)


def tools_text(request: TurnRequest) -> str:
    return "\n\n".join(
        f"{tool.name}: {tool.description}\n{json.dumps(tool.schema, sort_keys=True)}"
        for tool in request.tools
    )


def _call_line(name: str, arguments: object) -> str:
    return f"[asks for {name}] {json.dumps(arguments, sort_keys=True, ensure_ascii=False)}"


def request_text(request: TurnRequest) -> str:
    """Everything the call carried but the system prompt and tool list: the settings it ran
    with, the conversation, and the earlier steps of this turn."""
    web = f", up to {request.web.max_uses} web searches" if request.web else ""
    lines = [
        f"[model] {request.model or 'the default'}, effort {request.effort or 'default'}, "
        f"up to {request.max_tokens or 'the usual'} tokens back{web}"
    ]
    for message in request.messages:
        lines.append(
            f"[{message.role}]\n" + "\n\n".join(ai_texts.cut(part) for part in message.parts)
        )
    for number, exchange in enumerate(request.exchanges, 1):
        lines.append(f"[model, step {number}]\n{reply_text(exchange.reply, stop=False)}")
        for outcome in exchange.outcomes:
            bad = " (failed)" if outcome.is_error else ""
            lines.append(f"[result of {outcome.name}{bad}]\n{ai_texts.cut(outcome.content)}")
    return "\n\n".join(lines)


def reply_text(reply: ModelReply, *, stop: bool = True) -> str:
    parts = [reply.text] if reply.text else []
    parts += [_call_line(call.name, call.arguments) for call in reply.tool_calls]
    if stop:
        ended = f"[ended: {reply.stop}" + (f", {reply.refusal}" if reply.refusal else "") + "]"
        parts.append(ended)
    return "\n".join(parts)


def keep_answer(
    conn: sqlite3.Connection,
    settings: Settings,
    request: TurnRequest,
    reply: ModelReply,
    *,
    call_id: int,
    message_id: int | None,
    turn: str | None,
    iteration: int,
    kind: str | None,
    about: str | None,
    provider: str,
    model: str,
    now: datetime,
) -> None:
    if not settings.keep_ai_text_days:
        return
    try:
        with transaction(conn):
            ai_texts.record(
                conn,
                call_id=call_id,
                message_id=message_id,
                turn=turn,
                iteration=iteration,
                kind=kind,
                about=about,
                provider=provider,
                model=model,
                error=None,
                system=system_text(request),
                tools=tools_text(request),
                request=request_text(request),
                reply=reply_text(reply),
                now=now,
            )
    except Exception:
        log.warning("could not keep the words of a model call", exc_info=True)


def keep_failure(
    conn: sqlite3.Connection,
    settings: Settings,
    request: TurnRequest | None,
    exc: Exception,
    *,
    message_id: int | None,
    turn: str | None,
    iteration: int,
    kind: str | None,
    about: str | None,
    provider: str,
    model: str,
    now: datetime,
) -> None:
    """A call that got no answer: always in the problem log, and in words when those are kept."""
    trouble = getattr(exc, "trouble", None)
    retry = getattr(exc, "retryable", None)
    facts = [
        f"provider: {provider}",
        f"model: {model}",
        f"kind of call: {kind or 'not recorded'}",
        f"trouble: {trouble or 'none named'}",
        f"worth trying again: {retry}",
        f"company's request id: {getattr(exc, 'request_id', None) or 'none'}",
    ]
    message = logs.redact(f"{provider} did not answer ({kind or 'a call'}): {exc}")
    try:
        with transaction(conn):
            problems.record(
                conn,
                level="ERROR",
                source="model",
                message=message,
                detail=logs.redact("\n".join(facts)),
                now=now,
            )
            if settings.keep_ai_text_days and request is not None:
                ai_texts.record(
                    conn,
                    call_id=None,
                    message_id=message_id,
                    turn=turn,
                    iteration=iteration,
                    kind=kind,
                    about=about,
                    provider=provider,
                    model=model,
                    error=logs.redact(f"{exc}"),
                    system=system_text(request),
                    tools=tools_text(request),
                    request=request_text(request),
                    reply="\n".join(facts),
                    now=now,
                )
    except Exception:
        log.warning("could not keep a failed model call", exc_info=True)


def keep_heard(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    call_id: int,
    message_id: int | None,
    turn: str,
    kind: str,
    provider: str,
    model: str,
    sent: str,
    heard: str,
    now: datetime,
) -> None:
    """A voice note or a photo, in words: what was sent is described (the recording and the
    picture are never kept), and what came back is the words."""
    if not settings.keep_ai_text_days:
        return
    try:
        with transaction(conn):
            ai_texts.record(
                conn,
                call_id=call_id,
                message_id=message_id,
                turn=turn,
                iteration=1,
                kind=kind,
                about=None,
                provider=provider,
                model=model,
                error=None,
                system=None,
                tools=None,
                request=sent,
                reply=heard,
                now=now,
            )
    except Exception:
        log.warning("could not keep the words of a model call", exc_info=True)
