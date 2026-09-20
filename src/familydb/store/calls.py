"""Audit log of tool calls and model calls."""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb.store.db import to_json, utcnow_iso

USAGE_KEYS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


def log_tool_call(
    conn: sqlite3.Connection,
    *,
    message_id: int | None,
    iteration: int,
    tool_use_id: str | None,
    tool_name: str,
    input: Any,  # noqa: A002
    output: str | None,
    is_error: bool,
    duration_ms: int | None,
    now: str | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO tool_calls (message_id, iteration, tool_use_id, tool_name, input, output, "
        "is_error, duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            message_id,
            iteration,
            tool_use_id,
            tool_name,
            to_json(input),
            output,
            int(is_error),
            duration_ms,
            now or utcnow_iso(),
        ),
    )
    return int(cur.lastrowid or 0)


def log_llm_call(
    conn: sqlite3.Connection,
    *,
    message_id: int | None,
    iteration: int,
    model: str,
    served_model: str | None,
    request_id: str | None,
    stop_reason: str | None,
    usage: dict[str, Any] | None,
    duration_ms: int | None,
    now: str | None = None,
) -> int:
    usage = usage or {}
    cur = conn.execute(
        "INSERT INTO llm_calls (message_id, iteration, model, served_model, request_id, "
        "stop_reason, input_tokens, cache_creation_input_tokens, cache_read_input_tokens, "
        "output_tokens, duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            message_id,
            iteration,
            model,
            served_model,
            request_id,
            stop_reason,
            *(usage.get(key) for key in USAGE_KEYS),
            duration_ms,
            now or utcnow_iso(),
        ),
    )
    return int(cur.lastrowid or 0)


def recent_llm_calls(conn: sqlite3.Connection, limit: int = 5) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM llm_calls ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def tool_calls_for_message(conn: sqlite3.Connection, message_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM tool_calls WHERE message_id = ? ORDER BY id", (message_id,)
    ).fetchall()
    return [dict(row) for row in rows]
