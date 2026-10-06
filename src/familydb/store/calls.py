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
    turn: str | None = None,
    member_id: int | None = None,
    source: str | None = None,
    undo: dict[str, Any] | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO tool_calls (message_id, iteration, tool_use_id, tool_name, input, output, "
        "is_error, duration_ms, created_at, turn, member_id, source, undo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            turn,
            member_id,
            source,
            to_json(undo) if undo is not None else None,
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
    kind: str | None = None,
    sections: dict[str, int] | None = None,
    turn: str | None = None,
    about: str | None = None,
) -> int:
    usage = usage or {}
    cur = conn.execute(
        "INSERT INTO llm_calls (message_id, iteration, model, served_model, request_id, "
        "stop_reason, input_tokens, cache_creation_input_tokens, cache_read_input_tokens, "
        "output_tokens, duration_ms, created_at, provider, web_searches, cost_usd, "
        "cost_estimated, kind, sections, turn, about) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            kind,
            to_json(sections) if sections is not None else None,
            turn,
            about,
        ),
    )
    return int(cur.lastrowid or 0)


def spent_on(conn: sqlite3.Connection, kinds: tuple[str, ...], *, since: str) -> float:
    """Estimated dollars spent on these kinds of call since a UTC timestamp."""
    marks = ", ".join("?" for _ in kinds)
    row = conn.execute(
        f"SELECT coalesce(sum(cost_usd), 0) AS spent FROM llm_calls "
        f"WHERE kind IN ({marks}) AND created_at >= ?",
        (*kinds, since),
    ).fetchone()
    return float(row["spent"])


def spent_since(conn: sqlite3.Connection, *, since: str) -> float:
    """Estimated dollars spent on model calls since a UTC timestamp."""
    row = conn.execute(
        "SELECT coalesce(sum(cost_usd), 0) AS spent FROM llm_calls WHERE created_at >= ?",
        (since,),
    ).fetchone()
    return float(row["spent"])


def usual_day(conn: sqlite3.Connection, *, since: str) -> float:
    """What a day that had any model calls cost on average since a UTC timestamp, in estimated
    dollars: the total over the days that had calls, so a quiet week does not drag it to nothing."""
    row = conn.execute(
        "SELECT coalesce(sum(cost_usd), 0) AS spent, "
        "count(DISTINCT substr(created_at, 1, 10)) AS days FROM llm_calls WHERE created_at >= ?",
        (since,),
    ).fetchone()
    return float(row["spent"]) / row["days"] if row["days"] else 0.0


def spent_since_by(conn: sqlite3.Connection, *, since: str, member_id: int) -> float:
    """Estimated dollars spent since then on calls made for somebody's own messages."""
    row = conn.execute(
        "SELECT coalesce(sum(c.cost_usd), 0) AS spent FROM llm_calls c "
        "JOIN messages m ON m.id = c.message_id WHERE c.created_at >= ? AND m.member_id = ?",
        (since, member_id),
    ).fetchone()
    return float(row["spent"])


def answered_for(
    conn: sqlite3.Connection, member_id: int, *, since: str, other_than: int | None = None
) -> int:
    """How many of a member's messages since a timestamp went to a model (commands and taps ask
    none); `other_than` is the one being asked."""
    row = conn.execute(
        "SELECT count(DISTINCT m.id) AS n FROM messages m JOIN llm_calls c ON c.message_id = m.id "
        "WHERE m.member_id = ? AND m.direction = 'in' AND m.received_at >= ? AND m.id != ?",
        (member_id, since, other_than or 0),
    ).fetchone()
    return int(row["n"])


def held_since(conn: sqlite3.Connection, *, since: str, other_than: int | None = None) -> float:
    """Estimated dollars set aside by calls still in flight, counting holds made since then."""
    row = conn.execute(
        "SELECT coalesce(sum(cost_usd), 0) AS held FROM spend_holds "
        "WHERE created_at >= ? AND id IS NOT ?",
        (since, other_than),
    ).fetchone()
    return float(row["held"])


def rehold(conn: sqlite3.Connection, hold_id: int, *, cost_usd: float) -> None:
    conn.execute("UPDATE spend_holds SET cost_usd = ? WHERE id = ?", (cost_usd, hold_id))


def hold(conn: sqlite3.Connection, *, cost_usd: float, now: str) -> int:
    cur = conn.execute(
        "INSERT INTO spend_holds (cost_usd, created_at) VALUES (?, ?)", (cost_usd, now)
    )
    return int(cur.lastrowid or 0)


def release(conn: sqlite3.Connection, hold_id: int, *, stale_before: str) -> None:
    """Give a hold back, and clear any a crashed process left older than any call runs."""
    conn.execute("DELETE FROM spend_holds WHERE id = ? OR created_at < ?", (hold_id, stale_before))


def recent_llm_calls(conn: sqlite3.Connection, limit: int = 5) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM llm_calls ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


# How a call ended badly, for the week's comparison (usage_watch.py).
ENDED_BADLY = ("refusal", "max_tokens", "error")


def figures_between(
    conn: sqlite3.Connection, *, since: str, until: str
) -> dict[str, dict[str, Any]]:
    """Per kind of call between two moments: calls, asks, dollars, tokens sent and back, time,
    bad endings, and the commonest model."""
    marks = ", ".join("?" for _ in ENDED_BADLY)
    rows = conn.execute(
        "SELECT kind, count(*) AS calls, "
        "count(DISTINCT coalesce('m' || message_id, 't' || turn, 'c' || id)) AS asks, "
        "coalesce(sum(cost_usd), 0) AS cost, "
        "coalesce(sum(coalesce(input_tokens, 0) + coalesce(cache_read_input_tokens, 0) "
        "+ coalesce(cache_creation_input_tokens, 0)), 0) AS sent, "
        "coalesce(sum(output_tokens), 0) AS back, coalesce(avg(duration_ms), 0) AS ms, "
        f"sum(CASE WHEN stop_reason IN ({marks}) THEN 1 ELSE 0 END) AS bad "
        "FROM llm_calls WHERE kind IS NOT NULL AND created_at >= ? AND created_at < ? "
        "GROUP BY kind",
        (*ENDED_BADLY, since, until),
    ).fetchall()
    found = {row["kind"]: dict(row) for row in rows}
    for row in conn.execute(
        "SELECT kind, coalesce(served_model, model) AS model, count(*) AS n FROM llm_calls "
        "WHERE kind IS NOT NULL AND created_at >= ? AND created_at < ? "
        "GROUP BY kind, 2 ORDER BY n DESC",
        (since, until),
    ):
        found.get(row["kind"], {}).setdefault("model", row["model"])
    return found


def activity_since(conn: sqlite3.Connection, *, since: str, limit: int) -> list[dict[str, Any]]:
    """What the models were asked lately, newest first: a row per message answered and per
    message-less turn (a lookup)."""
    rows = conn.execute(
        "SELECT CASE WHEN message_id IS NOT NULL THEN 'm' || message_id ELSE 't' || turn END "
        "AS key, min(created_at) AS started, max(id) AS last_id, "
        "group_concat(DISTINCT kind) AS kinds, count(*) AS calls, "
        "coalesce(sum(cost_usd), 0) AS cost_usd, "
        "coalesce(sum(input_tokens), 0) + coalesce(sum(cache_read_input_tokens), 0) "
        "+ coalesce(sum(cache_creation_input_tokens), 0) AS sent, "
        "coalesce(sum(output_tokens), 0) AS back, coalesce(sum(web_searches), 0) AS searches, "
        "max(message_id) AS message_id, max(about) AS about "
        "FROM llm_calls WHERE created_at >= ? AND (message_id IS NOT NULL OR turn IS NOT NULL) "
        "GROUP BY 1 ORDER BY last_id DESC LIMIT ?",
        (since, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def calls_in(
    conn: sqlite3.Connection, *, message_id: int | None = None, turn: str | None = None
) -> list[dict[str, Any]]:
    """Every model call for a message, or for a turn, in the order they were made."""
    column, value = ("message_id", message_id) if message_id is not None else ("turn", turn)
    rows = conn.execute(
        f"SELECT * FROM llm_calls WHERE {column} = ? ORDER BY id", (value,)
    ).fetchall()
    return [dict(row) for row in rows]


def tools_in(
    conn: sqlite3.Connection, *, message_id: int | None = None, turn: str | None = None
) -> list[dict[str, Any]]:
    """Every tool call for a message, or for a turn, in the order they were made."""
    column, value = ("message_id", message_id) if message_id is not None else ("turn", turn)
    rows = conn.execute(
        f"SELECT * FROM tool_calls WHERE {column} = ? ORDER BY id", (value,)
    ).fetchall()
    return [dict(row) for row in rows]


def last_lookup_turn(conn: sqlite3.Connection, idea_id: int) -> str | None:
    """The turn that last looked an idea up and saved or skipped it, for its history."""
    row = conn.execute(
        "SELECT turn FROM tool_calls WHERE tool_name IN ('save_place', 'skip_place') "
        "AND turn IS NOT NULL AND json_extract(input, '$.idea_id') = ? ORDER BY id DESC LIMIT 1",
        (idea_id,),
    ).fetchone()
    return row["turn"] if row else None


def get(conn: sqlite3.Connection, call_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM tool_calls WHERE id = ?", (call_id,)).fetchone()


def last_undoable(
    conn: sqlite3.Connection, *, member_id: int, message_id: int, since: str
) -> sqlite3.Row | None:
    """This person's last change that can be taken back, made since `since` in the chat
    `message_id` was said in, and before it (undo.py)."""
    return conn.execute(
        "SELECT t.* FROM tool_calls t JOIN messages m ON m.id = t.message_id "
        "JOIN messages here ON here.id = ? "
        "WHERE t.member_id = ? AND t.undo IS NOT NULL AND t.undone_at IS NULL "
        "AND t.created_at >= ? AND t.message_id != here.id "
        "AND m.channel = here.channel AND m.chat_id = here.chat_id "
        "ORDER BY t.id DESC LIMIT 1",
        (message_id, member_id, since),
    ).fetchone()


def undoable_for(
    conn: sqlite3.Connection, message_ids: list[int], *, since: str
) -> dict[int, sqlite3.Row]:
    """By message, the last change its turn made that can still be taken back: the Undo under a
    reply (the page's chat, and Telegram's button)."""
    if not message_ids:
        return {}
    marks = ",".join("?" * len(message_ids))
    rows = conn.execute(
        f"SELECT * FROM tool_calls WHERE message_id IN ({marks}) AND undo IS NOT NULL "
        "AND undone_at IS NULL AND created_at >= ? ORDER BY id",
        (*message_ids, since),
    ).fetchall()
    return {int(row["message_id"]): row for row in rows}


def claim_undo(conn: sqlite3.Connection, call_id: int, *, now: str) -> bool:
    """Mark a call undone before undoing it, so two presses undo it once. Call inside a
    transaction; False when it was undone already."""
    return (
        conn.execute(
            "UPDATE tool_calls SET undone_at = ? WHERE id = ? AND undone_at IS NULL",
            (now, call_id),
        ).rowcount
        == 1
    )


def release_undo(conn: sqlite3.Connection, call_id: int) -> None:
    """The undo did not go through: the call can be undone again."""
    conn.execute("UPDATE tool_calls SET undone_at = NULL WHERE id = ?", (call_id,))


def tool_calls_for_message(conn: sqlite3.Connection, message_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM tool_calls WHERE message_id = ? ORDER BY id", (message_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def usage_since(conn: sqlite3.Connection, *, since: str) -> list[dict[str, Any]]:
    """Token totals per model since a timestamp, busiest first (`debug cost`)."""
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


def usage_by_kind(conn: sqlite3.Connection, *, since: str) -> list[dict[str, Any]]:
    """Calls, tokens and estimated dollars per kind (`gateway.KINDS`) since a timestamp, dearest
    first."""
    rows = conn.execute(
        "SELECT kind, count(*) AS calls, "
        "coalesce(sum(input_tokens), 0) + coalesce(sum(cache_read_input_tokens), 0) "
        "+ coalesce(sum(cache_creation_input_tokens), 0) AS sent, "
        "coalesce(sum(output_tokens), 0) AS output_tokens, "
        "coalesce(sum(web_searches), 0) AS web_searches, "
        "coalesce(sum(cost_usd), 0) AS cost_usd, "
        "count(DISTINCT message_id) AS messages "
        "FROM llm_calls WHERE created_at >= ? GROUP BY kind ORDER BY cost_usd DESC, calls DESC",
        (since,),
    ).fetchall()
    return [dict(row) for row in rows]


def sections_since(conn: sqlite3.Connection, *, since: str) -> list[dict[str, Any]]:
    """Each call's kind, section sizes and input tokens."""
    rows = conn.execute(
        "SELECT kind, sections, coalesce(input_tokens, 0) + coalesce(cache_read_input_tokens, 0) "
        "+ coalesce(cache_creation_input_tokens, 0) AS sent "
        "FROM llm_calls WHERE created_at >= ? AND sections IS NOT NULL ORDER BY id",
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
