"""Settings the family changes without a file: an override wins over the environment, which wins
over the default. Only `EDITABLE` keys can be set, so a crafted form cannot reach any other."""

from __future__ import annotations

import sqlite3
from typing import Any

from familydb.store.db import from_json, to_json, utcnow_iso

BEHAVIOUR = (
    "provider",
    "worker_provider",
    "provider_fallback",
    "chat_level",
    "digest_level",
    "lookup_level",
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
    "kid_daily_spend",
    "wish_daily_count",
    "occasion_list_size",
    "parent_asks_per_week",
    "wording_daily_after",
    "kid_daily_messages",
    "anthropic_cache_ttl",
    "agent_max_iterations",
    "worker_max_iterations",
    "web_tools_enabled",
    "enrich_interval_minutes",
    "lookups_when",
    "lookup_hour",
    "enrich_batch",
    "enrichment_notes",
    "place_stale_days",
    "prompt_idea_limit",
    "history_limit",
    "history_hours",
    "family_tz",
    "home_area",
    "home_lat",
    "home_lon",
    "weather_units",
    "travel_speed_kmh",
    "road_factor",
    "digest_chat_id",
    "digest_day",
    "digest_hour",
    "follow_ups",
    "follow_up_hour",
    "task_nudges",
    "tidy_ideas",
    "find_places",
    "admin_alerts",
    "model_watch",
    "judgements",
    "judgement_level",
    "judgement_acts",
    "judgement_budget",
    "choosing",
    "choose_level",
    "choose_budget",
    "openai_better_model",
    "openai_best_model",
    "anthropic_better_model",
    "anthropic_best_model",
    "gemini_better_model",
    "gemini_best_model",
    "plan_checks",
    "plan_check_hour",
    "morning_hour",
    "morning_agenda",
    "chase_missed",
    "deadline_heads_up",
    "forgotten_roundup",
    "roundup_day",
    "web_push",
    "retry_interval_minutes",
    "retry_max_attempts",
    "telegram_require_mention",
    "private_when_personal",
    "family_chat_id",
    "gather_seconds",
    "voice_notes",
    "voice_max_minutes",
    "photos",
    "transcribe_provider",
    "openai_transcribe_model",
    "gemini_transcribe_model",
    "web_title",
    "web_dictation",
    "web_session_days",
    "keep_messages_days",
    "google_calendar_id",
    "log_level",
    "problem_log_level",
    "log_areas",
    "keep_ai_text_days",
    "event_feeds",
    "happening_radius_km",
    "happening_search",
    "happening_refind_days",
    "happening_budget",
)
SECRETS = (
    "anthropic_api_key",
    "openai_api_key",
    "gemini_api_key",
    "telegram_bot_token",
    "ticketmaster_api_key",
)
# Companies without a module of their own, and their keys (config.CompanyDef); written by the
# companies form alone. The keys never reach the change log.
COMPANIES = ("companies", "company_keys")
# The page's choice of company and model for each use, and how much each thinks
# (agent/uses.py); written by the models form alone.
MODELS = ("model_choices", "use_effort", "company_options")
HIDDEN = ("company_keys",)
# Who the assistant and the family are (/settings/personality); long texts show as "rewritten"
# in the change list (web/views.py `LONG_SETTINGS`).
PROFILE = (
    "persona",
    "persona_name",
    "persona_text",
    "persona_notes",
    "about_family",
    "voice_lines",
)
# The shared family password hash: set only by its own form and `familydb password`, never a
# settings form; it opens nothing once an admin has their own (store/logins.py).
LOCK = ("web_password_hash",)
EDITABLE = (
    frozenset(BEHAVIOUR)
    | frozenset(SECRETS)
    | frozenset(PROFILE)
    | frozenset(LOCK)
    | frozenset(COMPANIES)
    | frozenset(MODELS)
)


def overrides(conn: sqlite3.Connection) -> dict[str, Any]:
    """Every stored setting, ready to be layered over the environment."""
    rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    return {row["key"]: from_json(row["value"]) for row in rows if row["key"] in EDITABLE}


def stamp(conn: sqlite3.Connection) -> str:
    """A marker that moves whenever a setting does: the newest log line (a removed override
    writes one) and the newest stored value, since either can stand still."""
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
    """Store these settings and log what moved; returns the keys that changed. An unchanged value
    is not written. A secret's value never reaches the log, only that it was replaced."""
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
        secret = key in SECRETS or key in LOCK or key in HIDDEN
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
