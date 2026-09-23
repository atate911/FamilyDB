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
    provider: str | None = None,
    cost_usd: float | None = None,
    cost_estimated: bool = False,
) -> int:
    usage = usage or {}
    cur = conn.execute(
        "INSERT INTO llm_calls (message_id, iteration, model, served_model, request_id, "
        "stop_reason, input_tokens, cache_creation_input_tokens, cache_read_input_tokens, "
        "output_tokens, duration_ms, created_at, provider, web_searches, cost_usd, "
        "cost_estimated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            provider,
            usage.get("web_searches"),
            cost_usd,
            int(cost_estimated),
        ),
    )
    return int(cur.lastrowid or 0)


def spent_since(conn: sqlite3.Connection, *, since: str) -> float:
    """Estimated dollars spent on model calls since a UTC timestamp."""
    row = conn.execute(
        "SELECT coalesce(sum(cost_usd), 0) AS spent FROM llm_calls WHERE created_at >= ?",
        (since,),
    ).fetchone()
    return float(row["spent"])


def recent_llm_calls(conn: sqlite3.Connection, limit: int = 5) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM llm_calls ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def tool_calls_for_message(conn: sqlite3.Connection, message_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM tool_calls WHERE message_id = ? ORDER BY id", (message_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def usage_since(conn: sqlite3.Connection, *, since: str) -> list[dict[str, Any]]:
    """Token totals per model since a timestamp, busiest first. For `familydb debug cost`."""
    rows = conn.execute(
        "SELECT coalesce(served_model, model) AS model, count(*) AS calls, "
        "coalesce(sum(input_tokens), 0) AS input_tokens, "
        "coalesce(sum(cache_read_input_tokens), 0) AS cache_read, "
        "coalesce(sum(cache_creation_input_tokens), 0) AS cache_write, "
        "coalesce(sum(output_tokens), 0) AS output_tokens, "
        "coalesce(sum(web_searches), 0) AS web_searches, "
        "coalesce(sum(cost_usd), 0) AS cost_usd, "
        "max(cost_estimated) AS cost_estimated "
        "FROM llm_calls WHERE created_at >= ? GROUP BY 1 ORDER BY calls DESC",
        (since,),
    ).fetchall()
    return [dict(row) for row in rows]


def troubles_since(
    conn: sqlite3.Connection, *, since: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Model calls that ended in something other than an answer or a tool call, newest first."""
    rows = conn.execute(
        "SELECT coalesce(served_model, model) AS model, stop_reason, created_at, message_id "
        "FROM llm_calls WHERE created_at >= ? AND stop_reason IS NOT NULL "
        "AND stop_reason NOT IN ('end', 'tool_use', 'paused') "
        "ORDER BY id DESC LIMIT ?",
        (since, limit),
    ).fetchall()
    return [dict(row) for row in rows]
