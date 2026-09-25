"""What the status page shows: what is connected, what it has cost, and what is stuck.

Reads only. Everything here is a query and a sentence; no decision is taken from it. The point
is that someone can answer "is it working, and what is it costing us?" without opening a log.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from familydb.agent import compose, gateway, providers
from familydb.agent.spending import spent_today
from familydb.app import App
from familydb.availability import (
    calendar_available,
    enrichment_available,
    weather_available,
    web_is_public,
)
from familydb.dates import utc_iso
from familydb.store import calls, ideas, members, messages
from familydb.store import settings as settings_store
from familydb.store.settings import SECRETS
from familydb.web import views
from familydb.web.auth import own_passwords, password_chosen, password_in_use

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
    telegram = _where("telegram_bot_token", live, stored)
    state = app.channel_states.get("telegram")
    if live.telegram_bot_token and state:
        telegram = f"{telegram}; {state}"
    rows.append(_row("Telegram bot token", telegram_working(app), telegram))
    return rows


def telegram_working(app: App) -> bool:
    """A token is set and Telegram has not refused it or been out of reach, as far as is known."""
    state = app.channel_states.get("telegram", "")
    return bool(app.settings.telegram_bot_token) and not state.startswith(("the token", "cannot"))


def services(app: App, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    live = app.settings
    calendar = "not configured"
    if live.google_calendar_id and not calendar_available(live):
        calendar = "calendar named, but not connected yet: connect it on the settings page"
    elif calendar_available(live):
        calendar = live.google_calendar_id or ""
    weather = (
        f"{live.home_lat}, {live.home_lon} ({live.weather_units})"
        if weather_available(live)
        else "no home coordinates, so no forecast and no travel estimates"
    )
    personal = own_passwords(conn)
    if personal:
        page = "everybody signs in as themselves"
    elif not password_in_use(live):
        page = "no password: anyone who can reach it is in"
    elif password_chosen(live):
        page = "one password the family shares; give each person their own on the setup page"
    else:
        page = "the installer's password; choose your own on the setup page"
    if web_is_public(live):
        page += "; reachable from other machines"
        page += ", behind a proxy" if live.web_trust_proxy else ", with no proxy declared"
    return [
        _row("Google Calendar", calendar_available(live), calendar),
        _row("Weather and travel", weather_available(live), weather),
        _row("Reading the web", *_lookups(app)),
        _row("Weekend digest", *_digest(app)),
        _row("This page", (personal or password_in_use(live)) or None, page),
    ]


def spending(
    conn: sqlite3.Connection, since: str, settings: Any = None, now: Any = None
) -> dict[str, Any]:
    """Tokens and estimated dollars per model, how much of the input came from the cache, and
    how much of today's limit is used."""
    rows = calls.usage_since(conn, since=since)
    kinds = [
        {**row, "purpose": gateway.purpose(row["kind"])}
        for row in calls.usage_by_kind(conn, since=since)
    ]
    measured = calls.sections_since(conn, since=since)
    where = [
        {"purpose": gateway.purpose(kind), "parts": parts}
        for kind in gateway.KINDS
        if (parts := compose.breakdown(row for row in measured if row["kind"] == kind))
    ]
    today = spent_today(conn, settings, now) if settings is not None else 0.0
    fresh = sum(row["input_tokens"] for row in rows)
    cached = sum(row["cache_read"] for row in rows)
    written = sum(row["cache_write"] for row in rows)
    served = fresh + cached + written
    return {
        "rows": rows,
        "kinds": kinds,
        "where": where,
        "calls": sum(row["calls"] for row in rows),
        "input": fresh,
        "cached": cached,
        "written": written,
        "output": sum(row["output_tokens"] for row in rows),
        "cache_share": round(cached / served * 100) if served else 0,
        "dollars": sum(row["cost_usd"] for row in rows),
        "estimated": any(row["cost_estimated"] for row in rows),
        "today": today,
        "limit": getattr(settings, "daily_spend_limit", 0),
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
            for state in sorted(counts, key=lambda state: (-counts[state], state))
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
        "services": services(app, conn),
        "spending": spending(conn, since, app.settings, app.clock.now()),
        "last": last_call(conn, tz),
        "waiting": waiting(conn, tz),
        "troubles": troubles(conn, since, tz),
    }


@dataclass(frozen=True)
class SetupStep:
    """One step of setting FamilyDB up, and how far it has got, read from what is configured.

    Nothing records that a step was done or skipped: each is done when the thing it sets up is
    there, so leaving half way, or doing it on the settings page instead, is never out of step.
    """

    name: str
    title: str
    short: str  # a word or two, for the row of steps along the top of each one
    need: str  # "needed" (it cannot answer without it), "recommended" or "optional"
    minutes: int
    done: bool
    detail: str  # what is set up, or what is missing, in a few words
    todo: str  # the line on the home page while it is not done


SETUP_ORDER = ("you", "password", "model", "home", "telegram", "family", "calendar")


def setup_progress(app: App, conn: sqlite3.Connection) -> list[SetupStep]:
    """Every setup step in order, each done or not. A few small reads, no network."""
    live = app.settings
    everyone = members.list_all(conn)
    admin = next((person for person in everyone if person.role == "admin"), None)
    linked = [person for person in everyone if person.channel_user_id]
    chat = app.provider("chat")
    bot = telegram_name(app)
    if own_passwords(conn):
        password = (True, "Everybody signs in as themselves.")
    elif not password_in_use(live):
        password = (True, "No password: the page is only reachable from this machine.")
    elif password_chosen(live):
        password = (False, "Everybody still shares one password.")
    else:
        password = (False, "Still the password the installer made up.")
    telegram_state = app.channel_states.get("telegram", "")
    if telegram_working(app) and linked:
        telegram = f"@{bot}, and it knows {linked[0].display_name}." if bot else "Connected."
    elif telegram_working(app):
        telegram = f"@{bot} is connected; link your phone to it." if bot else "Connected."
    elif live.telegram_bot_token and telegram_state.startswith("the token"):
        telegram = "Telegram refused the bot token."
    elif live.telegram_bot_token:
        telegram = "A bot token is saved; connecting."
    else:
        telegram = "Not set up; the family can use the Chat page meanwhile."
    return [
        SetupStep(
            "you",
            "Add yourself",
            "You",
            "needed",
            1,
            admin is not None,
            f"On the list as {admin.display_name}." if admin else "Nobody is on the list yet.",
            "Add yourself, as an admin, then the rest of the family.",
        ),
        SetupStep(
            "password",
            "Your own password",
            "Password",
            "recommended",
            1,
            password[0],
            password[1],
            "Choose your own password, so everybody signs in as themselves.",
        ),
        SetupStep(
            "model",
            "Connect an AI model",
            "AI model",
            "needed",
            5,
            app.can_ask("chat"),
            f"{PROVIDER_LABELS.get(chat.name, chat.name)} answers, with {chat.model_for('chat')}."
            if app.can_ask("chat")
            else "No AI key yet, so it cannot answer.",
            "Give it a model key. Until then it saves what it is told but cannot answer.",
        ),
        SetupStep(
            "home",
            "Where home is",
            "Home",
            "recommended",
            1,
            bool(live.home_area) and live.home_lat is not None,
            live.home_area or "Not set, so no forecast and no travel times.",
            "Say where home is, for the weather and for what is on nearby.",
        ),
        SetupStep(
            "telegram",
            "Telegram on your phone",
            "Telegram",
            "optional",
            5,
            telegram_working(app) and bool(linked),
            telegram,
            "Link your phone to the Telegram bot, so it knows who is writing."
            if live.telegram_bot_token
            else "Add a Telegram bot, so the family can message it from their phones.",
        ),
        SetupStep(
            "family",
            "The rest of the family",
            "Family",
            "optional",
            2,
            len(everyone) > 1,
            f"{len(everyone)} on the list." if everyone else "Nobody yet.",
            "Add the rest of the family, so plans can include them.",
        ),
        SetupStep(
            "calendar",
            "Google Calendar",
            "Calendar",
            "optional",
            15,
            calendar_available(live),
            live.google_calendar_id
            if calendar_available(live)
            else "Not connected, so plans stay on this page.",
            "Connect Google Calendar, so plans land on the family calendar.",
        ),
    ]


def ready_to_answer(steps: list[SetupStep]) -> bool:
    """Whether the steps it cannot answer without are done: somebody to answer, and a model."""
    return all(step.done for step in steps if step.need == "needed")


def setup_steps(app: App, conn: sqlite3.Connection) -> list[dict[str, str]]:
    """What is left before the bot can do all it is for, most important first. Empty when done.

    Each is a sentence and the setup page where it is done: nothing here needs a file.
    """
    return [
        {"text": step.todo, "link": f"/setup/{step.name}"}
        for step in setup_progress(app, conn)
        if not step.done
    ]


def telegram_name(app: App) -> str | None:
    """The bot's @name, as Telegram gave it when the channel connected, or None."""
    state = app.channel_states.get("telegram", "")
    prefix = "connected as @"
    return state[len(prefix) :] if state.startswith(prefix) else None


def _lookups(app: App) -> tuple[bool | None, str]:
    if not enrichment_available(app.settings):
        return False, "off: no idea is filled in and nothing new is discovered"
    if not app.can_ask("worker"):
        return None, "on, and waiting for a model key: new ideas are looked up once there is one"
    return True, "ideas are looked up automatically, and discovery may search"


def _digest(app: App) -> tuple[bool | None, str]:
    chat = app.settings.digest_chat_id
    if not chat:
        return False, "not sent"
    if not app.can_ask("chat"):
        return None, f"{chat}, once there is a model key to write it"
    return True, chat


def digest_chats(conn: sqlite3.Connection, tz: Any, limit: int = 10) -> list[tuple[str, str]]:
    """Chats the digest could go to, as (chat id, what it is), so nobody has to dig for an id.

    A Telegram group appears once somebody on the family list has written in it.
    """
    offers = [("web", "the chat on this page")]
    for chat in messages.chats(conn, "telegram")[:limit]:
        chat_id = chat["chat_id"]
        if chat_id.startswith("-"):
            what = "Telegram group"
        else:
            member = members.resolve(conn, "telegram", chat_id)
            what = f"Telegram, private chat with {member.display_name}" if member else "Telegram"
        offers.append((chat_id, f"{what}, last message {views.local_moment(chat['last_at'], tz)}"))
    return offers
