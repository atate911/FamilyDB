"""What the status page shows: what is connected, what it has cost, and what is stuck.

Reads only. Everything here is a query and a sentence; no decision is taken from it. The point
is that someone can answer "is it working, and what is it costing us?" without opening a log.
"""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from typing import Any

from familydb.agent import providers
from familydb.app import App
from familydb.availability import (
    calendar_available,
    enrichment_available,
    weather_available,
    web_is_public,
)
from familydb.dates import utc_iso
from familydb.store import calls, ideas, messages
from familydb.store import settings as settings_store
from familydb.store.settings import SECRETS
from familydb.web import views

DAYS = 30
TROUBLE_LIMIT = 6
WAITING_LIMIT = 5
LOOKUP_STATES = {
    "pending": "waiting to be looked up",
    "done": "looked up",
    "failed": "the lookup failed",
    "skipped": "nothing to look up",
}
PROVIDER_LABELS = {"anthropic": "Claude (Anthropic)", "openai": "OpenAI", "gemini": "Google Gemini"}
KEY_FOR = {
    "anthropic": "anthropic_api_key",
    "openai": "openai_api_key",
    "gemini": "gemini_api_key",
}


def _row(label: str, on: bool | None, detail: str) -> dict[str, Any]:
    """One line of the "what is connected" table. `on` of None means partly, or unknown."""
    return {"label": label, "on": on, "detail": detail}


def _where(name: str, live: Any, stored: dict[str, Any]) -> str:
    """Where a key came from, without ever saying what it is."""
    if name in stored:
        return "set on this page"
    return "set in the environment" if getattr(live, name) else "no key"


def models(app: App) -> list[dict[str, Any]]:
    """Who answers what, and on which model. The same question `debug cost` answers."""
    rows = []
    for surface, what in (("chat", "Chat messages"), ("worker", "Web lookups and discovery")):
        provider = app.provider(surface)
        rows.append(
            _row(
                what,
                provider.configured(),
                f"{PROVIDER_LABELS.get(provider.name, provider.name)}, "
                f"{provider.model_for(surface)}"
                + ("" if provider.configured() else " — but there is no key for it"),
            )
        )
    chat = app.provider("chat")
    spare = app.fallback("chat", chat.name)
    rows.append(
        _row(
            "If that one cannot",
            spare is not None,
            f"{PROVIDER_LABELS.get(spare.name, spare.name)} answers instead"
            if spare is not None
            else "nowhere else to go: one key, or the fallback is switched off",
        )
    )
    return rows


def keys(app: App, stored: dict[str, Any]) -> list[dict[str, Any]]:
    live = app.settings
    rows = [
        _row(
            PROVIDER_LABELS[name],
            bool(getattr(live, KEY_FOR[name])),
            _where(KEY_FOR[name], live, stored),
        )
        for name in providers.NAMES
    ]
    rows.append(
        _row(
            "Telegram bot token",
            bool(live.telegram_bot_token),
            _where("telegram_bot_token", live, stored),
        )
    )
    return rows


def services(app: App) -> list[dict[str, Any]]:
    live = app.settings
    calendar = "not configured"
    if live.google_calendar_id and not calendar_available(live):
        calendar = "calendar named, but nobody has signed in: run `familydb auth google`"
    elif calendar_available(live):
        calendar = live.google_calendar_id or ""
    weather = (
        f"{live.home_lat}, {live.home_lon} ({live.weather_units})"
        if weather_available(live)
        else "no home coordinates, so no forecast and no travel estimates"
    )
    page = "no password: anyone who can reach it is in" if not live.web_password else "password set"
    if web_is_public(live):
        page += "; reachable from other machines"
        page += ", behind a proxy" if live.web_trust_proxy else ", with no proxy declared"
    return [
        _row("Google Calendar", calendar_available(live), calendar),
        _row("Weather and travel", weather_available(live), weather),
        _row(
            "Reading the web",
            enrichment_available(live),
            "ideas are looked up automatically"
            if enrichment_available(live)
            else "switched off, or no key for the lookup model",
        ),
        _row("Weekend digest", bool(live.digest_chat_id), live.digest_chat_id or "not sent"),
        _row("This page", None if not live.web_password else True, page),
    ]


def spending(conn: sqlite3.Connection, since: str) -> dict[str, Any]:
    """Tokens per model, and how much of the input came from the cache at a tenth of the price."""
    rows = calls.usage_since(conn, since=since)
    fresh = sum(row["input_tokens"] for row in rows)
    cached = sum(row["cache_read"] for row in rows)
    written = sum(row["cache_write"] for row in rows)
    served = fresh + cached + written
    return {
        "rows": rows,
        "calls": sum(row["calls"] for row in rows),
        "input": fresh,
        "cached": cached,
        "written": written,
        "output": sum(row["output_tokens"] for row in rows),
        "cache_share": round(cached / served * 100) if served else 0,
    }


def last_call(conn: sqlite3.Connection, tz: Any) -> dict[str, Any] | None:
    """The most recent model call, and who served it."""
    recent = calls.recent_llm_calls(conn, limit=1)
    if not recent:
        return None
    call = recent[0]
    model = call["served_model"] or call["model"]
    name = providers.owner(model)
    return {
        "when": views.local_moment(call["created_at"], tz),
        "model": model,
        "provider": PROVIDER_LABELS.get(name or "", "an unfamiliar model"),
        "stop": call["stop_reason"] or "unknown",
        "seconds": round((call["duration_ms"] or 0) / 1000, 1),
    }


def waiting(conn: sqlite3.Connection, tz: Any) -> dict[str, Any]:
    """What has not been dealt with: ideas not yet looked up, messages that did not go through."""
    counts = ideas.enrichment_counts(conn)
    pending = ideas.pending_enrichment(conn, limit=WAITING_LIMIT)
    stuck = messages.recent_failures(conn, limit=WAITING_LIMIT)
    return {
        "lookups": [
            {"state": LOOKUP_STATES.get(state, state), "count": counts[state]}
            for state in sorted(counts, key=lambda state: -counts[state])
        ],
        "pending": [{"id": idea.id, "title": idea.title} for idea in pending],
        "pending_total": counts.get("pending", 0),
        "messages": [
            {
                "id": message.id,
                "when": views.local_moment(message.received_at, tz),
                "text": message.text,
                "error": message.error,
                "tries": message.retries,
                "given_up": bool(message.give_up),
            }
            for message in stuck
        ],
    }


def troubles(conn: sqlite3.Connection, since: str, tz: Any) -> dict[str, Any]:
    """The failures worth a person's attention, rather than everything in the log."""
    return {
        "calls": [
            {
                "when": views.local_moment(row["created_at"], tz),
                "model": row["model"],
                "stop": row["stop_reason"],
            }
            for row in calls.troubles_since(conn, since=since, limit=TROUBLE_LIMIT)
        ],
        "lookups": [
            {
                "id": idea.id,
                "title": idea.title,
                "note": idea.enrichment_note or "no reason recorded",
                "when": views.local_moment(idea.enriched_at, tz) if idea.enriched_at else None,
            }
            for idea in ideas.failed_enrichment(conn, limit=TROUBLE_LIMIT)
        ],
    }


def status(app: App, conn: sqlite3.Connection) -> dict[str, Any]:
    """Everything the status page shows, in one pass over a handful of small queries."""
    tz = app.settings.tzinfo
    since = utc_iso(app.clock.now() - timedelta(days=DAYS))
    stored = settings_store.overrides(conn)
    return {
        "days": DAYS,
        "models": models(app),
        "keys": keys(app, {name: stored[name] for name in SECRETS if name in stored}),
        "services": services(app),
        "spending": spending(conn, since),
        "last": last_call(conn, tz),
        "waiting": waiting(conn, tz),
        "troubles": troubles(conn, since, tz),
    }
