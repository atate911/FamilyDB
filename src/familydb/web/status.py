"""What the status page shows (what is connected, what it has cost, what is stuck) and how far
setting up has got (`setup_progress`, read by setup, Home and Settings too). Reads only."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from familydb import alerts, happening, personas, presents, upkeep, whatsnew
from familydb import model_watch as watch
from familydb.agent import compose, gateway, providers
from familydb.agent.spending import spent_today
from familydb.app import App
from familydb.availability import (
    calendar_available,
    digest_configured,
    enrichment_available,
    happening_available,
    happening_search_available,
    weather_available,
    web_is_public,
)
from familydb.dates import hour_words, utc_iso
from familydb.integrations.google_calendar import service_account_email
from familydb.store import alerts as alert_store
from familydb.store import backups as backup_store
from familydb.store import calls, ideas, members, messages, mornings
from familydb.store import finds as find_store
from familydb.store import judgements as judgement_store
from familydb.store import model_watch as model_store
from familydb.store import settings as settings_store
from familydb.store.settings import SECRETS
from familydb.web import fields, views
from familydb.web.auth import own_passwords, password_chosen, password_in_use

DAYS = 30
CHANGES_DAYS = 30
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
    """One line of the "what is connected" table; `on` None means partly or unknown."""
    return {"label": label, "on": on, "detail": detail}


def _where(name: str, live: Any, stored: dict[str, Any]) -> str:
    """Where a key came from, without ever saying what it is."""
    if name in stored:
        return "set on this page"
    return "set in the environment" if getattr(live, name) else "no key"


SITUATIONS = (
    ("chat", "Chat messages"),
    ("digest", "The weekend digest"),
    ("enrich", "Web lookups and discovery"),
)


def models(app: App) -> list[dict[str, Any]]:
    """Who answers what, and on which model (as `debug cost` does)."""
    rows = []
    for kind, what in SITUATIONS:
        provider, model = gateway.answering(app.settings, kind)
        level = getattr(app.settings, gateway.spec(kind).level)
        keyed = provider.configured()
        rows.append(
            _row(
                what,
                keyed,
                f"{PROVIDER_LABELS.get(provider.name, provider.name)}, "
                f"{views.model_text(provider.name, model, level)}"
                + ("" if keyed else " — but there is no key for it"),
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
    rows.append(
        _row(
            "Ticketmaster key",
            bool(live.ticketmaster_api_key) or None,
            _where("ticketmaster_api_key", live, stored)
            if live.ticketmaster_api_key
            else "no key, which is fine: it only adds shows and games near home",
        )
    )
    return rows


def telegram_working(app: App) -> bool:
    """A token is set and Telegram has not refused it or been out of reach, as far as known."""
    state = app.channel_states.get("telegram", "")
    return bool(app.settings.telegram_bot_token) and not state.startswith(("the token", "cannot"))


def services(app: App, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    live = app.settings
    calendar = "not configured"
    if live.google_calendar_id and not calendar_available(live):
        calendar = "calendar named, but not connected yet: connect it on the settings page"
    elif calendar_available(live):
        calendar = live.google_calendar_id or ""
        if email := service_account_email(Path(live.google_key_path)):
            calendar += f", reached as {email}"
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
        page = "the password FamilyDB started with; choose your own on the setup page"
    if web_is_public(live):
        page += "; reachable from other machines"
        page += ", behind a proxy" if live.web_trust_proxy else ", with no proxy declared"
    return [
        _row("Google Calendar", calendar_available(live), calendar),
        _row("Weather and travel", weather_available(live), weather),
        _row("Reading the web", *_lookups(app)),
        _row("Weekend digest", *_digest(app)),
        _row("This page", (personal or password_in_use(live)) or None, page),
        _row("Backups", *_backups(app, conn)),
    ]


def _backups(app: App, conn: sqlite3.Connection) -> tuple[bool | None, str]:
    """When the last good backup was made, from what `familydb db backup` recorded."""
    good = backup_store.latest(conn, good=True)
    trouble = upkeep.backup_trouble(conn, app.clock.now())
    if good is None and trouble is None:
        return None, "none recorded; the installer schedules one each night (RUNBOOK section 7)"
    if trouble:
        return False, trouble
    assert good is not None
    size = f"{good.bytes / (1024 * 1024):.1f} MB"
    when = views.local_moment(good.made_at, app.settings.tzinfo)
    return True, f"the last good one {when}, {size}"


def spending(
    conn: sqlite3.Connection, since: str, settings: Any = None, now: Any = None
) -> dict[str, Any]:
    """Tokens and estimated dollars per model, the cache share, and today's use of the limit."""
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
    """Ideas not yet looked up and messages that did not go through."""
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


ACTIVITY_DAYS = 7
ACTIVITY_SHOWN = 25


def activity(app: App, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """What the models were asked lately, newest first; each line opens `web/activity.py`."""
    tz = app.settings.tzinfo
    since = utc_iso(app.clock.now() - timedelta(days=ACTIVITY_DAYS))
    names = {person.id: person.display_name for person in members.list_all(conn, active_only=False)}
    rows = []
    for row in calls.activity_since(conn, since=since, limit=ACTIVITY_SHOWN):
        kinds = [kind for kind in (row["kinds"] or "").split(",") if kind]
        what = ", ".join(dict.fromkeys(gateway.purpose(kind) for kind in kinds))
        asked = messages.get(conn, row["message_id"]) if row["message_id"] is not None else None
        if "digest" in kinds:
            title = "Weekend ideas"
        elif asked is not None:
            title = views.asked_line(asked.text, names.get(asked.member_id or -1, "someone"))
        elif "enrich" in kinds and row["about"]:
            title = f"Looking up {row['about']}"
        else:
            title = row["about"] or what or "a model call"
        rows.append(
            {
                "key": row["key"],
                "when": views.local_moment(row["started"], tz),
                "title": title,
                "what": what,
                "calls": row["calls"],
                "tokens": row["sent"] + row["back"],
                "searches": row["searches"],
                "cost": row["cost_usd"],
            }
        )
    return rows


# Alert kinds (familydb/alerts.py) that stop the family being answered, and others worth a look.
# Price moves, usage shifts, new models and judgements are news and leave the light alone.
STOPPING = frozenset({"credit", "key", "limit"})
WORRYING = frozenset({"calendar", "model", "prices", "api", "refused", "happening"})


def light(app: App, conn: sqlite3.Connection) -> str | None:
    """The Status tile's light: "bad" while the family cannot be answered, "warn" while something
    else only an admin can fix goes on, else None."""
    since = utc_iso(app.clock.now() - alerts.KEEP)
    kinds = {one.kind for one in alert_store.current(conn, since=since)}
    if kinds & STOPPING:
        return "bad"
    if kinds & WORRYING:
        return "warn"
    return None


@dataclass(frozen=True)
class Pill:
    """How the assistant stands, said once for the sidebar, the phone's top bar and Status: one of
    ready, busy (writing back), rest (the day's limit is spent) or down (cannot answer)."""

    state: str
    long: str
    short: str


def pill(app: App, conn: sqlite3.Connection, *, name: str, busy: bool = False) -> Pill:
    """Built from what Status already reads, so the pill and the page cannot disagree. `busy` is
    whether a reply is being written (the chat's own `standing`); asked by the caller, which knows
    whose chat it is."""
    live = app.settings
    if not ready_to_answer(setup_progress(app, conn)):
        return Pill("down", f"{name} can\u2019t answer yet", "Can\u2019t answer yet")
    limit = live.daily_spend_limit
    if limit and spent_today(conn, live, app.clock.now()) >= limit:
        return Pill("rest", f"{name} is resting until midnight", "Resting")
    if light(app, conn) == "bad":
        return Pill("down", f"{name} can\u2019t answer right now", "Can\u2019t answer")
    if busy:
        return Pill("busy", f"{name} is writing back", "Writing back")
    return Pill("ready", f"{name} is ready", "Ready")


USUAL_DAYS = 30


def vera_today(app: App, conn: sqlite3.Connection) -> dict[str, Any]:
    """Home's small card for a grown-up: what was spent today against the limit, and what a usual
    day costs (the last 30 days). An estimate, as everywhere (agent/providers/prices.py)."""
    live = app.settings
    now = app.clock.now()
    since = utc_iso(now - timedelta(days=USUAL_DAYS))
    return {
        "spent": views.money_text(spent_today(conn, live, now)),
        "limit": views.money_text(live.daily_spend_limit) if live.daily_spend_limit else None,
        "usual": views.money_text(calls.usual_day(conn, since=since)),
    }


def _action(label: str, endpoint: str, **values: Any) -> dict[str, Any]:
    """A button beside a part that needs something: where it goes is a page's name, not a URL."""
    return {"label": label, "endpoint": endpoint, "values": values}


def _health_row(
    area: str, glyph: str, state: str, tag: str, words: str, action: dict[str, Any] | None = None
) -> dict[str, Any]:
    """One part of "How each part is doing". `state` is ok, look, broken, better (not connected
    yet, which is a choice) or off; with `tag`, the words that say it, it is never colour alone."""
    return {
        "area": area,
        "glyph": glyph,
        "state": state,
        "tag": tag,
        "words": words,
        "action": action,
    }


def health(app: App, conn: sqlite3.Connection, *, name: str) -> list[dict[str, Any]]:
    """How each part stands, in plain words: what the page, the verdict and the family read
    alike, from the same signals as the pill (`pill`). No network, no model."""
    live = app.settings
    steps = {one.name: one for one in setup_progress(app, conn)}
    standing = pill(app, conn, name=name)
    limit = live.daily_spend_limit
    spent = spent_today(conn, live, app.clock.now())
    linked = telegram_working(app)
    rows: list[dict[str, Any]] = []

    # The assistant herself.
    if standing.state == "down":
        missing = [
            one.title.lower() for one in steps.values() if one.need == "needed" and not one.done
        ]
        if missing:
            words = f"Not ready to answer yet: it still needs {', '.join(missing)}."
            action = _action("Open setup", "setup.overview")
        else:
            words = "Something only an admin can fix is stopping her: see Needs a look below."
            action = None
        rows.append(_health_row(name, "presence", "broken", "Can\u2019t answer", words, action))
    elif standing.state == "rest":
        rows.append(
            _health_row(
                name,
                "presence",
                "look",
                "Resting",
                "Resting until midnight: the day\u2019s limit is spent.",
            )
        )
    else:
        where = "here on the website and on Telegram" if linked else "here on the website"
        tag = "Writing back" if standing.state == "busy" else "Ready"
        rows.append(_health_row(name, "presence", "ok", tag, f"Ready to answer {where}."))

    # What it may spend.
    if not limit:
        rows.append(
            _health_row(
                "Spending",
                "dollar",
                "off",
                "No limit",
                "There is no daily limit, so nothing stops it spending.",
                _action("Set a limit", "settings.section", name="spending"),
            )
        )
    elif spent >= limit:
        rows.append(
            _health_row(
                "Spending",
                "dollar",
                "look",
                "Limit reached",
                f"The {views.money_text(limit)} daily limit is reached; nothing more is asked of "
                "a model until midnight.",
            )
        )
    elif spent >= limit * 0.75:
        rows.append(
            _health_row(
                "Spending",
                "dollar",
                "look",
                "Near the limit",
                f"About {views.money_text(spent)} of the {views.money_text(limit)} daily limit "
                "is spent.",
            )
        )
    else:
        rows.append(
            _health_row(
                "Spending",
                "dollar",
                "ok",
                "Working",
                f"Well under the {views.money_text(limit)} daily limit.",
            )
        )

    # Who may sign in.
    password = steps["password"]
    rows.append(
        _health_row(
            "Sign-in",
            "lock",
            "ok" if password.done else "look",
            "Working" if password.done else "Needs a look",
            password.detail,
            None if password.done else _action("Set up sign-ins", "setup.step", name="password"),
        )
    )

    # A second company to fall back on.
    spare = app.fallback("chat", app.provider("chat").name)
    if spare is not None:
        rows.append(
            _health_row(
                "Backup",
                "sparkle",
                "ok",
                "Ready",
                f"If the first company is down, {PROVIDER_LABELS.get(spare.name, spare.name)} "
                "answers instead.",
            )
        )
    else:
        rows.append(
            _health_row(
                "Backup",
                "sparkle",
                "off",
                "Optional",
                f"A second AI company {name} can switch to if the first is down. It only costs "
                "when used.",
                _action("Add a backup key", "settings.section", name="model", _anchor="keys"),
            )
        )

    # Telegram.
    telegram = steps["telegram"]
    if telegram.done:
        rows.append(_health_row("Telegram", "send", "ok", "Working", telegram.detail))
    elif live.telegram_bot_token:
        rows.append(
            _health_row(
                "Telegram",
                "send",
                "look",
                "Needs a look",
                telegram.detail,
                _action("Open the Telegram step", "setup.step", name="telegram"),
            )
        )
    else:
        rows.append(
            _health_row(
                "Telegram",
                "send",
                "better",
                "Not connected",
                f"The family can\u2019t text {name} from their phones. Reminders still appear in "
                "the chat.",
                _action("Connect Telegram", "setup.step", name="telegram"),
            )
        )

    # Google Calendar.
    if calendar_available(live):
        rows.append(
            _health_row(
                "Google Calendar", "cal", "ok", "Connected", "Plans are put on the family calendar."
            )
        )
    elif live.google_calendar_id:
        rows.append(
            _health_row(
                "Google Calendar",
                "cal",
                "look",
                "Needs a look",
                "A calendar is named but not connected yet.",
                _action("Connect Google Calendar", "setup.step", name="calendar"),
            )
        )
    else:
        rows.append(
            _health_row(
                "Google Calendar",
                "cal",
                "better",
                "Not connected",
                "Plans stay inside FamilyDB.",
                _action("Connect Google Calendar", "setup.step", name="calendar"),
            )
        )

    # Reading the web for new ideas.
    if enrichment_available(live):
        rows.append(
            _health_row(
                "Looking things up",
                "compass",
                "ok",
                "On",
                "New ideas get hours, prices and drive times.",
            )
        )
    else:
        rows.append(
            _health_row(
                "Looking things up",
                "compass",
                "off",
                "Off",
                "New ideas don\u2019t get hours, prices or drive times.",
                _action("Turn it on", "settings.section", name="lookups"),
            )
        )
    return rows


def verdict(
    parts: list[dict[str, Any]], *, name: str, standing: Pill, spent: float, thirty: float
) -> dict[str, str]:
    """The line at the top of Status: whether she is ready, said with what is worth a look. Built
    from `health` and the pill, so it cannot say something the rows below do not."""
    limit_spoken = {
        "ready": f"{name} is ready, and well under budget.",
        "busy": f"{name} is writing back.",
        "rest": f"{name} is resting until midnight.",
        "down": f"{name} can\u2019t answer right now.",
    }
    heading = limit_spoken[standing.state]
    if standing.state == "ready" and any(
        one["area"] == "Spending" and one["state"] != "ok" for one in parts
    ):
        heading = f"{name} is ready."
    today = "Nothing spent today" if spent <= 0 else f"About {views.money_text(spent)} spent today"
    words = [f"{today}; the last 30 days cost {views.money_text(thirty)}."]
    looks = [
        one["area"] for one in parts if one["state"] in ("look", "broken") and one["area"] != name
    ]
    if looks:
        words.append(
            f"{presents.join_names(looks)} {'needs' if len(looks) == 1 else 'need'} a look."
        )
    absent = [one["area"] for one in parts if one["state"] == "better"]
    if absent:
        isnt = "isn\u2019t" if len(absent) == 1 else "aren\u2019t"
        words.append(f"{presents.join_names(absent)} {isnt} connected yet.")
    tone = {"ready": "ok", "busy": "ok", "rest": "warn", "down": "alert"}[standing.state]
    return {"tone": tone, "heading": heading, "text": " ".join(words)}


def attention(app: App, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """What only an admin can fix, while it lasts. New models are under Models and prices."""
    now = app.clock.now()
    found = [
        one
        for one in alert_store.current(conn, since=utc_iso(now - alerts.KEEP))
        if one.kind not in ("new", "advice", "calendars")
    ]
    if not found:
        return []
    admins = len(alerts.admins_on_telegram(conn))
    rows = []
    for one in found:
        row = views.alert_row(
            one, app.settings.tzinfo, telling=app.settings.admin_alerts, admins=admins
        )
        if one.kind == "model":
            row["switch"] = switch_for(app, conn, one.subject)
        rows.append(row)
    return rows


def switch_for(app: App, conn: sqlite3.Connection, subject: str) -> dict[str, Any] | None:
    """For a model going or gone, the settings boxes naming it and what to set them to. None when
    no box names it (a level's model, which the daily check swaps itself) or nothing is offered."""
    company, _, rest = subject.partition(":")
    name = rest.split(":")[0]
    live = app.settings
    boxes = [
        one.key
        for one in fields.FIELDS
        if one.company == company and str(getattr(live, one.key, "") or "").lower() == name
    ]
    instead = watch.replacement_for(conn, company, name, app.clock.today())
    if not boxes or instead is None:
        return None
    return {"boxes": boxes, "to": instead.model, "words": views.model_offer(company, instead.model)}


def model_watch(app: App, conn: sqlite3.Connection) -> dict[str, Any]:
    tz = app.settings.tzinfo
    since = utc_iso(app.clock.now() - timedelta(days=CHANGES_DAYS))
    return {
        "on": app.settings.model_watch,
        "sources": [views.source_row(one, tz) for one in model_store.sources(conn)],
        "changes": [
            views.model_change_row(one, tz) for one in model_store.changes_since(conn, since=since)
        ],
        "days": CHANGES_DAYS,
        "judgements": [
            views.judgement_row(one, tz, app.settings)
            for one in judgement_store.recent(conn, since=since)
        ],
        "judging": app.settings.judgements,
    }


def happening_status(app: App, conn: sqlite3.Connection) -> dict[str, Any]:
    """How each source of what is on near home last answered, what they list in the weeks
    ahead, and what its model calls have cost this month against its budget."""
    live = app.settings
    tz = live.tzinfo
    today = app.clock.now().astimezone(tz).date()
    ahead = today + timedelta(days=happening.HORIZON_DAYS)
    return {
        "name": happening.NAME,
        "on": happening_available(live),
        "sources": [views.find_source_row(one, tz) for one in find_store.sources(conn)],
        "upcoming": find_store.count_upcoming(conn, start=today, end=ahead),
        "days": happening.HORIZON_DAYS,
        "spent": happening.spent_this_month(conn, live, app.clock.now()),
        "budget": live.happening_budget,
        "searching": happening_search_available(live),
    }


def happening_settings(app: App, conn: sqlite3.Connection) -> dict[str, Any]:
    """What the settings page for things near home shows besides its boxes: the calendars the
    app found near home, ticked when the settings read them, the newest marked, and what its
    model calls have cost this month."""
    live = app.settings
    tz = live.tzinfo
    reading = set(happening.feed_urls(live))
    run = find_store.source(conn, happening.proposals_source(live.home_area))
    proposed = find_store.proposals(conn, live.home_area) if live.home_area else []
    return {
        "proposals": [
            {
                "url": one.url,
                "title": one.title,
                "note": one.note,
                "site": happening.host(one.url),
                "events": one.events,
                "ticked": one.url in reading,
                "new": run is not None
                and one.found_at == run.checked_at
                and one.url not in reading,
            }
            for one in proposed
        ],
        "looked": views.local_moment(run.checked_at, tz) if run else None,
        "looked_ok": run.ok if run else None,
        "spent": happening.spent_this_month(conn, live, app.clock.now()),
    }


def status(app: App, conn: sqlite3.Connection) -> dict[str, Any]:
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
        "waiting": {
            **waiting(conn, tz),
            "when": views.lookups_when(app.settings),
            "can_look_up": enrichment_available(app.settings),
        },
        "troubles": troubles(conn, since, tz),
        "attention": attention(app, conn),
        "model_watch": model_watch(app, conn),
        "happening": happening_status(app, conn),
        "activity": activity(app, conn),
        "activity_days": ACTIVITY_DAYS,
        "whats_new": whatsnew.latest(),
        **overview(app, conn, since),
    }


def overview(app: App, conn: sqlite3.Connection, since: str) -> dict[str, Any]:
    """The top of the page: the verdict, how each part is doing, and the month in figures."""
    name = personas.active(app.settings).name
    now = app.clock.now()
    spent = spent_today(conn, app.settings, now)
    thirty = sum(row["cost_usd"] for row in calls.usage_since(conn, since=since))
    parts = health(app, conn, name=name)
    standing = pill(app, conn, name=name)
    usual = calls.usual_day(conn, since=utc_iso(now - timedelta(days=USUAL_DAYS)))
    answered = sum(
        row["calls"] for row in calls.usage_by_kind(conn, since=since) if row["kind"] == "chat"
    )
    return {
        "health": parts,
        "verdict": verdict(parts, name=name, standing=standing, spent=spent, thirty=thirty),
        "thirty": {"dollars": thirty, "usual": usual, "answered": answered},
    }


@dataclass(frozen=True)
class SetupStep:
    """One setup step, done when what it sets up is there (nothing records progress)."""

    name: str
    title: str
    short: str  # for the row of steps along the top
    need: str  # "needed" (it cannot answer without it), "recommended" or "optional"
    minutes: int
    done: bool
    detail: str
    todo: str  # the home page line while not done


SETUP_ORDER = ("you", "password", "model", "home", "telegram", "family", "calendar")


def setup_progress(app: App, conn: sqlite3.Connection) -> list[SetupStep]:
    """Every setup step in order, each done or not. No network."""
    live = app.settings
    everyone = members.list_all(conn)
    admin = next((person for person in everyone if person.role == "admin"), None)
    linked = [person for person in everyone if person.channel_user_id]
    chat, chat_model = gateway.answering(live, "chat")
    bot = telegram_name(app)
    if own_passwords(conn):
        password = (True, "Everybody signs in as themselves.")
    elif not password_in_use(live):
        password = (True, "No password: the page is only reachable from this machine.")
    elif password_chosen(live):
        password = (False, "Everybody still shares one password.")
    else:
        password = (False, "Still the password FamilyDB started with.")
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
            f"{PROVIDER_LABELS.get(chat.name, chat.name)} answers, with {chat_model}."
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
            10,
            calendar_available(live),
            live.google_calendar_id
            if calendar_available(live)
            else "Not connected, so plans stay on this page.",
            "Connect Google Calendar, so plans land on the family calendar.",
        ),
    ]


def ready_to_answer(steps: list[SetupStep]) -> bool:
    """Whether the steps it cannot answer without are done."""
    return all(step.done for step in steps if step.need == "needed")


def setup_steps(app: App, conn: sqlite3.Connection) -> list[dict[str, str]]:
    """What is left to set up, most important first: a sentence and its setup page."""
    return [
        {"text": step.todo, "link": f"/setup/{step.name}"}
        for step in setup_progress(app, conn)
        if not step.done
    ]


def telegram_name(app: App) -> str | None:
    """The bot's @name as Telegram gave it on connecting, or None."""
    state = app.channel_states.get("telegram", "")
    prefix = "connected as @"
    return state[len(prefix) :] if state.startswith(prefix) else None


def telegram_reads_groups(app: App) -> bool | None:
    """Whether the bot reads every group message (BotFather's privacy off); None when unknown."""
    return app.channel_facts.get("telegram", {}).get("reads_groups")


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


AUTOMATIC_DAYS = 30
AUTOMATIC_RECENT = 20


def automatic(app: App, conn: sqlite3.Connection) -> dict[str, Any]:
    """What she sends of her own accord: each kind's state, cost and count, and the latest few."""
    settings, tz = app.settings, app.settings.tzinfo
    since = utc_iso(app.clock.now() - timedelta(days=AUTOMATIC_DAYS))
    counts = {
        **messages.sent_on_their_own_counts(conn, since=since),
        **mornings.part_counts(conn, since=since),
    }
    hour = hour_words
    digest_chat = dict(digest_chats(conn, tz)).get(settings.digest_chat_id, settings.digest_chat_id)
    state = {
        "weekend": (
            digest_configured(settings),
            f"{views.DAY_NAMES.get(settings.digest_day, settings.digest_day)} at "
            f"{hour(settings.digest_hour)}, to {digest_chat.split(', last message')[0]}"
            if settings.digest_chat_id
            else "nowhere chosen, so none is sent",
        ),
        "reminders": (True, "when a reminder somebody asked for is due"),
        "follow_ups": (
            settings.follow_ups,
            f"the day after a plan, at {hour(settings.follow_up_hour)}",
        ),
        "checks": (
            settings.plan_checks,
            f"the evening before a plan, at {hour(settings.plan_check_hour)}, only when "
            "something is off",
        ),
        "nudges": (
            settings.task_nudges,
            "when the part of the week a task was kept for comes round, and the calendar is free",
        ),
        "morning_agenda": (
            settings.morning_agenda,
            f"each morning at {hour(settings.morning_hour)}: the day's plans, reminders and "
            "deadlines, in each chat they are for",
        ),
        "chase_missed": (
            settings.chase_missed,
            "in the morning message, once, the day after a reminder went and nobody acted on it",
        ),
        "deadline_heads_up": (
            settings.deadline_heads_up,
            "in the morning message, the day before something is due",
        ),
        "forgotten_roundup": (
            settings.forgotten_roundup,
            f"in {views.DAY_NAMES.get(settings.roundup_day, settings.roundup_day)}'s morning "
            "message: to-dos a week old with nothing to bring them up",
        ),
        "lookups": (
            settings.enrichment_notes and enrichment_available(settings),
            f"after ideas are looked up, {views.lookups_when(settings)}",
        ),
        "alerts": (
            settings.admin_alerts,
            "when something only an admin can fix goes wrong, to each admin with a Telegram id",
        ),
        "kids_asks": (
            True,
            "when a kid asks for something that isn't OK, or asks for a parent, to each parent "
            "with a Telegram id",
        ),
        "kids_answers": (True, "when a parent answers a wish, in the kid's own chat"),
    }
    kinds = []
    for key, group, title, cost, events in views.AUTOMATIC:
        sent = [counts[event] for event in events if event in counts]
        on, when = state[key]
        last = max((stamp for _, stamp in sent), default=None)
        kinds.append(
            {
                "key": key,
                "group": group,
                "title": title,
                "on": on,
                "when": when,
                "cost": cost,
                "sent": sum(count for count, _ in sent),
                "last": views.local_moment(last, tz) if last else None,
            }
        )
    names = {
        str(person.channel_user_id): person.display_name
        for person in members.list_all(conn, active_only=False)
        if person.channel == "telegram"
    }
    recent = [
        {
            "when": views.local_moment(message.received_at, tz),
            "kind": views.AUTOMATIC_BY_EVENT.get(message.sent_as or "", message.sent_as),
            "chat": views.chat_words(message.chat_id, names.get(message.chat_id)),
            "text": message.text,
            "delivered": message.delivered_at is not None,
        }
        for message in messages.sent_on_their_own(conn, since=since, limit=AUTOMATIC_RECENT)
    ]
    return {"kinds": kinds, "recent": recent, "days": AUTOMATIC_DAYS}


def digest_chats(conn: sqlite3.Connection, tz: Any, limit: int = 10) -> list[tuple[str, str]]:
    """Chats the digest could go to, as (chat id, what it is). A group appears once somebody on
    the family list has written in it."""
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
