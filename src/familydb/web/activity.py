"""One message's or one lookup's history in full, for an admin: every model call and tool call.
A lookup has no message and is found by its turn. Private words from every chat, so `auth.NEEDS`
limits it to admins."""

from __future__ import annotations

import re
from contextlib import closing
from typing import Any

from flask import Blueprint, abort, current_app, render_template

from familydb.agent import gateway
from familydb.app import App
from familydb.store import ai_texts, calls, members, messages
from familydb.web import views

bp = Blueprint("activity", __name__)

KEY = re.compile(r"m[0-9]{1,18}|t[0-9a-f]{16}")


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


@bp.get("/status/activity/<key>")
def show(key: str) -> str:
    if not KEY.fullmatch(key):
        abort(404)
    app = _app()
    tz = app.settings.tzinfo
    with closing(app.connect()) as conn:
        names = {
            person.id: person.display_name for person in members.list_all(conn, active_only=False)
        }
        if key[0] == "m":
            message_id = int(key[1:])
            asked = messages.get(conn, message_id)
            model_calls = calls.calls_in(conn, message_id=message_id)
            tool_calls = calls.tools_in(conn, message_id=message_id)
            replies = messages.replies_to(conn, message_id)
            failed = ai_texts.failed_in(conn, message_id=message_id)
        else:
            asked, replies = None, []
            model_calls = calls.calls_in(conn, turn=key[1:])
            tool_calls = calls.tools_in(conn, turn=key[1:])
            failed = ai_texts.failed_in(conn, turn=key[1:])
        words = ai_texts.for_calls(conn, [row["id"] for row in model_calls])
    if asked is None and not model_calls:
        abort(404)
    kinds = list(dict.fromkeys(row["kind"] for row in model_calls if row["kind"]))
    about = next((row["about"] for row in model_calls if row.get("about")), None)
    if asked is not None:
        who = names.get(asked.member_id or -1, "someone")
        title = "Weekend ideas" if "digest" in kinds else f"A message from {who}"
    else:
        title = f"Looking up {about}" if about and "enrich" in kinds else (about or "A lookup")
    started = model_calls[0]["created_at"] if model_calls else asked.received_at  # type: ignore[union-attr]
    return render_template(
        "activity.html",
        title=title,
        when=views.local_moment(started, tz),
        asked=asked,
        said=messages.as_said(asked.text) if asked is not None else None,
        replies=[reply.text for reply in replies],
        model_calls=[_call_row(row, tz, words.get(row["id"])) for row in model_calls],
        failed_calls=[
            {
                "id": row["id"],
                "when": views.local_moment(row["created_at"], tz),
                "model": row["model"],
                "error": row["error"] or "",
            }
            for row in failed
        ],
        tool_calls=[_tool_row(row) for row in tool_calls],
        found=[found for found in (views.found_by_lookup(row) for row in tool_calls) if found],
        totals=_totals(model_calls),
    )


def _call_row(row: dict[str, Any], tz: Any, words: int | None = None) -> dict[str, Any]:
    return {
        "words": words,
        "when": views.local_moment(row["created_at"], tz),
        "what": gateway.purpose(row["kind"]),
        "about": row.get("about"),
        "provider": row.get("provider") or "",
        "model": row.get("served_model") or row["model"],
        "stop": row.get("stop_reason") or "",
        "sent": row.get("input_tokens") or 0,
        "cached": row.get("cache_read_input_tokens") or 0,
        "written": row.get("cache_creation_input_tokens") or 0,
        "back": row.get("output_tokens") or 0,
        "searches": row.get("web_searches") or 0,
        "cost": row.get("cost_usd") or 0.0,
        "estimated": bool(row.get("cost_estimated")),
        "ms": row.get("duration_ms"),
    }


def _tool_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": row["tool_name"],
        "error": bool(row["is_error"]),
        "ms": row.get("duration_ms"),
        "given": views.pretty_json(row.get("input")),
        "answer": views.pretty_json(row.get("output")),
    }


def _totals(model_calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "calls": len(model_calls),
        "sent": sum(
            (row.get("input_tokens") or 0)
            + (row.get("cache_read_input_tokens") or 0)
            + (row.get("cache_creation_input_tokens") or 0)
            for row in model_calls
        ),
        "back": sum(row.get("output_tokens") or 0 for row in model_calls),
        "searches": sum(row.get("web_searches") or 0 for row in model_calls),
        "cost": sum(row.get("cost_usd") or 0.0 for row in model_calls),
        "ms": sum(row.get("duration_ms") or 0 for row in model_calls),
    }
