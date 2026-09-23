"""Settings the family can change without touching a file.

An override here wins over the environment, which wins over the default. Only the keys in
`EDITABLE` can be set, so a typo or a crafted form cannot reach a setting that was never meant
to move. Values are JSON, so a number comes back a number.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb.store.db import from_json, to_json, utcnow_iso

# What the page may change. Anything not named here stays wherever it already lives.
BEHAVIOUR = (
    "provider",
    "worker_provider",
    "provider_fallback",
    "anthropic_model",
    "worker_model",
    "openai_model",
    "openai_worker_model",
    "gemini_model",
    "gemini_worker_model",
    "effort",
    "worker_effort",
    "max_output_tokens",
    "daily_spend_limit",
    "anthropic_cache_ttl",
    "agent_max_iterations",
    "worker_max_iterations",
    "web_tools_enabled",
    "enrich_interval_minutes",
    "enrich_batch",
    "enrichment_notes",
    "place_stale_days",
    "prompt_idea_limit",
    "history_limit",
    "history_hours",
    "home_area",
    "home_lat",
    "home_lon",
    "weather_units",
    "travel_speed_kmh",
    "road_factor",
    "digest_chat_id",
    "digest_day",
    "digest_hour",
    "follow_up_hour",
    "retry_interval_minutes",
    "retry_max_attempts",
    "web_title",
    "web_session_days",
    "google_calendar_id",
    "log_level",
)
SECRETS = ("anthropic_api_key", "openai_api_key", "gemini_api_key", "telegram_bot_token")
EDITABLE = frozenset(BEHAVIOUR) | frozenset(SECRETS)


def overrides(conn: sqlite3.Connection) -> dict[str, Any]:
    """Every stored setting, ready to be layered over the environment."""
    rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    return {row["key"]: from_json(row["value"]) for row in rows if row["key"] in EDITABLE}


def stamp(conn: sqlite3.Connection) -> str:
    """A marker that moves whenever a setting does. Cheap enough to check before every read.

    Two numbers, because either can stand still while the other moves: the newest line in the
    log, which a removed override also writes, and the newest value still stored.
    """
    row = conn.execute(
        "SELECT (SELECT max(id) FROM settings_log) AS change, "
        "(SELECT max(updated_at) FROM app_settings) AS stored"
    ).fetchone()
    return f"{row['change'] or 0}:{row['stored'] or ''}"


def get(conn: sqlite3.Connection, key: str) -> Any:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return from_json(row["value"]) if row else None


def set_many(
    conn: sqlite3.Connection,
    values: dict[str, Any],
    *,
    changed_by: int | None = None,
    source: str = "web",
    now: str | None = None,
) -> list[str]:
    """Store these settings and log what moved. Returns the keys that actually changed.

    A value equal to what is already in force is not written, so the log stays meaningful. A
    secret's value never reaches the log, only the fact that it was replaced.
    """
    stamped = now or utcnow_iso()
    changed: list[str] = []
    for key, value in values.items():
        if key not in EDITABLE:
            raise ValueError(f"{key} is not a setting the page may change")
        previous = get(conn, key)
        if previous == value:
            continue
        if value is None:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
        else:
            conn.execute(
                "INSERT INTO app_settings (key, value, updated_at, updated_by) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at, updated_by = excluded.updated_by",
                (key, to_json(value), stamped, changed_by),
            )
        secret = key in SECRETS
        conn.execute(
            "INSERT INTO settings_log (key, old_value, new_value, secret, changed_at, changed_by, "
            "source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                key,
                None if secret else to_json(previous),
                None if secret else to_json(value),
                int(secret),
                stamped,
                changed_by,
                source,
            ),
        )
        changed.append(key)
    return changed


def clear(conn: sqlite3.Connection, key: str, *, changed_by: int | None = None) -> bool:
    """Drop an override so the environment's value applies again."""
    return bool(set_many(conn, {key: None}, changed_by=changed_by))


def history(conn: sqlite3.Connection, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT l.*, m.display_name AS changed_by_name FROM settings_log l "
        "LEFT JOIN members m ON m.id = l.changed_by ORDER BY l.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]
