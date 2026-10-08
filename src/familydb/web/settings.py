"""The settings pages: the only web module that writes settings, through `store.settings`, plus
two files (the session key via `keys.rotate`, the Google key via `google.save_key`). Every change
is logged; a key's value never is.

/settings summarises each part; each has a page, /settings/<name> (`fields.SECTIONS`), and every
form says which page it came from so its answer is shown there.

The Personality page writes the `PROFILE` settings. A rewrite of her description is kept for the
persona in force when the page was drawn (see `PersonaRewrite.of`); the family's name for her
and notes are theirs whoever she is.

A page's behaviour form carries every box on that page, so an emptied box means "back to the
default" and other pages' boxes are left alone. The keys form carries only what was typed: an
empty key box means "leave it alone", since a password box is always drawn empty.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    get_flashed_messages,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pydantic import ValidationError

from familydb import export, passwords, personas, voice
from familydb.agent import gateway, providers
from familydb.agent.providers import prices
from familydb.agent.spending import spent_today
from familydb.app import App
from familydb.availability import (
    enrichment_available,
    happening_available,
    happening_search_available,
    ticketmaster_available,
    weather_available,
    web_is_public,
    web_tools_available,
)
from familydb.config import PersonaRewrite, Settings, apply_overrides
from familydb.dates import hour_words
from familydb.integrations import google_calendar as google
from familydb.store import settings as settings_store
from familydb.store.db import transaction
from familydb.store.settings import SECRETS
from familydb.web import auth, fields, keys, troubleshooting, views
from familydb.web import status as status_page

log = logging.getLogger(__name__)

bp = Blueprint("settings", __name__)

HISTORY_LIMIT = 50
NOTICE = "settings"
SAVED = "Saved. {what}"
NOTHING_CHANGED = "Nothing was different, so nothing was written."
NEEDS_PASSWORD = "Type the family password to see a key."
WRONG_PASSWORD = "That password is not right."
LOCKED_OUT = "Too many tries. Wait a quarter of an hour."
KEY_HAS_SPACES = "A key has no spaces in it. Check what was pasted."
UNKNOWN_KEY = "There is no such key."
UNKNOWN_MODEL = "{company} says it has no model called {name}. Check the spelling."
COMPANIES = fields.COMPANIES
# So a new name can be checked with its company.
MODEL_BOXES = {
    one.key: (one.company, COMPANIES[one.company]) for one in fields.FIELDS if one.company
}
LEVEL_BOXES = {call.level: call.surface for call in gateway.KINDS.values()}
KEY_LABELS = {
    "anthropic_api_key": "Anthropic key",
    "openai_api_key": "OpenAI key",
    "gemini_api_key": "Google key",
    "telegram_bot_token": "Telegram bot token",
    "ticketmaster_api_key": "Ticketmaster key",
}
# The keys that are not a model company's, each on the page that uses it rather than among the
# companies' keys, and listed after them.
KEY_PAGES = {"telegram_bot_token": "connections", "ticketmaster_api_key": "happening"}


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _section(name: str | None) -> str | None:
    """The settings page a form said it was on, if it is one."""
    return name if name in fields.SECTION_BY_NAME else None


def _address(section: str | None) -> str:
    return url_for("settings.section", name=section) if section else url_for("settings.show")


def _answer(
    back: str | None,
    section: str | None,
    *,
    said: str | None = None,
    error: str | None = None,
    status: int = 400,
    otherwise: str | None = None,
) -> Response | tuple[str, int]:
    """Back to the setup page that sent the form, or the settings page it came from; a complaint
    from a form that named no page is drawn on `otherwise`, the page its boxes are on."""
    if back is not None:
        return auth.back_to_setup(back, said=said, problem=error)
    if error is not None:
        return page(section or otherwise, error=error, status=status)
    flash(said or NOTHING_CHANGED, NOTICE)
    return redirect(_address(section))


def _stored() -> dict[str, Any]:
    with closing(_app().connect()) as conn:
        return settings_store.overrides(conn)


def _save(values: dict[str, Any]) -> list[str]:
    """Write and log the changes. Returns the keys that actually moved."""
    app = _app()
    source = f"web {auth.client_address()}"
    me = auth.visitor().member
    with closing(app.connect()) as conn, transaction(conn):
        changed = settings_store.set_many(
            conn, values, changed_by=me.id if me else None, source=source
        )
    if changed:
        app.refresh()
        log.info("settings changed from the page: %s", ", ".join(changed))
    return changed


def unknown_models(values: dict[str, Any], stored: dict[str, Any], proposed: Settings) -> dict:
    """New model names their company says do not exist. Only a definite no counts: an unreachable
    company, or none with a key, is no reason to refuse."""
    found: dict[str, str] = {}
    for key, (company, label) in MODEL_BOXES.items():
        name = values.get(key)
        if not name or name == stored.get(key):
            continue
        if providers.build(company, proposed).model_exists(name) is False:
            found[key] = UNKNOWN_MODEL.format(company=label, name=name)
    return found


NOT_ON_THE_MAP = "Could not find {area} on the map. Type its latitude and longitude as well."
FOUND_HOME = "Found {label}, at {lat}, {lon}."


def locate_home(values: dict[str, Any], stored: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Coordinates for a changed home area, unless some were typed with it (those win). Returns
    them and a sentence saying what happened."""
    area = values.get("home_area")
    if not area or area == stored.get("home_area"):
        return {}, ""
    typed = any(
        values.get(key) is not None and values.get(key) != stored.get(key)
        for key in ("home_lat", "home_lon")
    )
    if typed:
        return {}, ""
    try:
        found = _app().geocoder.geocode(area)
    except Exception as exc:  # a map service that is down is not a reason to refuse the save
        log.warning("could not look up %s: %s", area, exc)
        found = None
    if found is None:
        return {}, NOT_ON_THE_MAP.format(area=area)
    lat, lon = round(found.lat, 4), round(found.lon, 4)
    said = FOUND_HOME.format(label=found.label, lat=lat, lon=lon)
    return {"home_lat": lat, "home_lon": lon}, said


def problems_from(exc: ValidationError) -> dict[str, str]:
    """Pydantic's complaints, one sentence per box."""
    found: dict[str, str] = {}
    for error in exc.errors(include_url=False):
        key = str(error["loc"][0]) if error["loc"] else ""
        found.setdefault(key, error["msg"])
    return found


CALENDAR_CONNECTED = "Connected. The bot now uses {name}."


def suggested(one: fields.Field) -> list[tuple[str, str]]:
    """The names a box suggests, each with a word on its place in the lineup and its price."""
    company = MODEL_BOXES.get(one.key, ("", ""))[0]
    # As the daily check last found them, except the hearing models, which it does not follow.
    live = company and one.key not in fields.FIXED_OFFERS
    names = prices.suggestions(company) if live else one.suggested
    return [(name, views.model_offer(company, name)) for name in names]


def level_labels(key: str, live: Settings) -> dict[str, str]:
    surface = LEVEL_BOXES.get(key)
    if surface is None:
        return {}
    answering = providers.for_surface(live, surface)
    return {
        level: views.level_choice(
            level, answering.name, providers.model_at(answering, surface, level)
        )
        for level in providers.catalog.LEVELS
    }


def google_panel(live: Any) -> dict[str, Any]:
    token = Path(live.google_key_path)
    return {
        "connected": token.exists(),
        "calendar": live.google_calendar_id,
        "email": google.service_account_email(token),
    }


# -- the three companies, as setup and the AI model page both offer them -------------------------

# What a line says of price follows the company's default model in prices.py.
COMPANY_LINES = {
    "openai": "The least expensive by far for what FamilyDB does, so it is the one it starts with.",
    "anthropic": "Claude. Several times dearer a message with the model it starts on.",
    "gemini": "Gemini, from Google. In between on price.",
}
KEY_STARTS = {"openai": "sk-", "anthropic": "sk-ant-", "gemini": "AIza"}


def company_choice(live: Settings, asked: str) -> dict[str, Any]:
    """The three companies, and the one whose key is shown: the one asked for, else answering."""
    company = asked if asked in providers.NAMES else live.provider
    return {
        "company": company,
        "label": COMPANIES[company],
        "prefix": KEY_STARTS[company],
        "has_key": bool(getattr(live, f"{company}_api_key")),
        "answering": live.provider,
        "model": providers.model_at(providers.build(company, live), "chat", live.chat_level),
        "companies": [
            {
                "name": name,
                "label": COMPANIES[name],
                "line": COMPANY_LINES[name],
                "has_key": bool(getattr(live, f"{name}_api_key")),
            }
            for name in ("openai", "anthropic", "gemini")
        ],
    }


# -- drawing the pages ---------------------------------------------------------------------------


def _box(
    one: fields.Field,
    overrides: dict[str, Any],
    base: Settings,
    problems: dict[str, str],
    typed: dict[str, str],
    offers: dict[str, list[tuple[str, str]]],
    live: Settings,
    grouped: dict[str, views.ZoneGroups] | None = None,
) -> dict[str, Any]:
    # A grouped dropdown (time zones) says its default in the words it offers.
    headed = (grouped or {}).get(one.key)
    reads = {value: words for _, rows in headed or () for value, words in rows}
    fallback = fields.fallback(one, base)
    return {
        "field": one,
        "value": typed.get(one.key, fields.shown(one, overrides.get(one.key))),
        "placeholder": reads.get(fallback) or fields.placeholder(one, fallback),
        "problem": problems.get(one.key),
        "stored": one.key in overrides,
        "offers": offers.get(one.key) or suggested(one),
        "labels": level_labels(one.key, live),
        "grouped": headed,
    }


def _group(group: fields.Group, boxes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "group": group,
        "boxes": boxes,
        # A folded group opens when it holds a complaint.
        "open": any(box["problem"] for box in boxes),
        "changed": sum(1 for box in boxes if box["stored"]),
    }


def _key_rows(
    live: Settings,
    overrides: dict[str, Any],
    problems: dict[str, str],
    revealed: tuple[str, str] | None,
) -> dict[str, dict[str, Any]]:
    """Every key and token, whether set and where from, the answering company's first."""
    return {
        name: {
            "key": name,
            "label": KEY_LABELS[name],
            "set": bool(getattr(live, name)),
            "stored": name in overrides,
            "problem": problems.get(name),
            "revealed": revealed[1] if revealed and revealed[0] == name else None,
        }
        for name in _key_order(live.provider)
    }


def page(
    section: str | None = None,
    *,
    problems: dict[str, str] | None = None,
    said: str | None = None,
    error: str | None = None,
    revealed: tuple[str, str] | None = None,
    typed: dict[str, str] | None = None,
    status: int = 200,
) -> tuple[str, int]:
    """Draw one settings page, or with no section the list of them."""
    if said is None:
        # Named, because the edit forms flash too.
        told = get_flashed_messages(category_filter=[NOTICE])
        said = told[0] if told else None
    if section is None:
        return overview(said=said, error=error, status=status)
    if section == "personality":
        return personality_page(said=said, error=error, status=status)
    app = _app()
    live = app.settings
    problems = problems or {}
    with closing(app.connect()) as conn:
        overrides = settings_store.overrides(conn)
        extra = PAGES[section](app, conn)
    offers = extra.pop("offers", {})
    grouped = extra.pop("grouped", {})
    groups = {
        group.name: _group(
            group,
            [
                _box(
                    one, overrides, app.base_settings, problems, typed or {}, offers, live, grouped
                )
                for one in group.fields
            ],
        )
        for group in fields.groups_in(section)
    }
    if section == "happening":
        # A calendar the app proposed is a tick above the box, not a line in it.
        proposed = {one["url"] for one in extra.get("proposals", [])}
        for box in groups["feeds"]["boxes"]:
            box["value"] = "\n".join(
                line for line in str(box["value"]).splitlines() if line not in proposed
            )
    return (
        render_template(
            "settings_section.html",
            section=fields.SECTION_BY_NAME[section],
            sections=fields.SECTIONS,
            groups=groups,
            keys=_key_rows(live, overrides, problems, revealed),
            said=said,
            error=error,
            needs_password=auth.visitor().signed_in,
            own_password=auth.visitor().login is not None,
            **extra,
        ),
        status,
    )


def _general(app: App, conn: Any) -> dict[str, Any]:
    return {
        "grouped": {"family_tz": views.zone_groups(fields.zones(), app.clock.now())},
        "served": served(app),
    }


# Where the scripts are: beside the code on a virtualenv install; an image holds only the code.
CHECKOUT = Path(__file__).resolve().parents[3]
INSTALLED = Path("/opt/familydb")


def served(app: App) -> dict[str, Any]:
    """Where the page is served and how to move it. Shown, never set here: `maintain.sh port` and
    `https --port` are out of every form's reach, so a stolen sign-in cannot move or widen it."""
    live = app.settings
    opened = urlsplit(request.host_url)
    script = CHECKOUT / "scripts" / "maintain.sh"
    host = opened.hostname or ""
    wanted = request.args.get("domain", "").strip().lower().rstrip(".")
    return {
        "opened": request.host_url,
        "port": opened.port or (443 if opened.scheme == "https" else 80),
        "own": f"{live.web_host}:{live.web_port}",
        "own_port": live.web_port,
        "proxied": live.web_trust_proxy,
        "local": not web_is_public(live),
        "script": script if script.exists() else INSTALLED / "scripts" / "maintain.sh",
        # For the guide to naming the page; the typed name is only a view, never saved.
        "host": host,
        "reached_by": reached_by(host),
        "domain": wanted if DOMAIN.fullmatch(wanted) else "",
        "domain_refused": bool(wanted) and not DOMAIN.fullmatch(wanted),
    }


# Letters, digits and hyphens, in two parts or more.
DOMAIN = re.compile(r"(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")


def reached_by(host: str) -> str:
    """How the page was reached: "name", "public" or "private" address, or "local"."""
    if host in ("localhost", "") or host.endswith(".localhost"):
        return "local"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return "name"
    if address.is_loopback:
        return "local"
    return "private" if address.is_private else "public"


def _model(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    chat = fields.MODEL_KEYS[live.provider][0]
    looking = fields.MODEL_KEYS[live.worker_provider or live.provider][1]
    return {**company_choice(live, request.args.get("company", "")), "in_use": (chat, looking)}


def _spending(app: App, conn: Any) -> dict[str, Any]:
    return {
        "today": spent_today(conn, app.settings, app.clock.now()),
        "limit": app.settings.daily_spend_limit,
    }


def _messages(app: App, conn: Any) -> dict[str, Any]:
    return {
        "offers": {"digest_chat_id": status_page.digest_chats(conn, app.settings.tzinfo)},
        "can_answer": app.can_ask("chat"),
        "automatic": status_page.automatic(app, conn),
    }


def _lookups(app: App, conn: Any) -> dict[str, Any]:
    return {"on": enrichment_available(app.settings), "can_look": app.can_ask("worker")}


def _happening(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    return {
        **status_page.happening_settings(app, conn),
        "on": happening_available(live),
        "searching": happening_search_available(live),
        "search_wanted": live.happening_search,
        "web": web_tools_available(live),
        "home": weather_available(live) and bool(live.home_area),
        "can_look": app.can_ask("worker"),
        "budget": live.happening_budget,
        "ticketmaster": ticketmaster_available(live),
    }


def _connections(app: App, conn: Any) -> dict[str, Any]:
    return {
        "offers": {"family_chat_id": status_page.digest_chats(conn, app.settings.tzinfo)},
        "google": google_panel(app.settings),
        "bot": status_page.telegram_name(app),
        "telegram": app.channel_states.get("telegram", ""),
        "reads_groups": status_page.telegram_reads_groups(app),
    }


def _security(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    return {
        "personal": auth.own_passwords(conn),
        "password": {
            "chosen": auth.password_chosen(live),
            "needs_current": current_password_needed(live),
            "least": auth.MIN_PASSWORD,
        },
    }


def _history(app: App, conn: Any) -> dict[str, Any]:
    tz = app.settings.tzinfo
    return {
        "history": [change(line, tz) for line in settings_store.history(conn, limit=HISTORY_LIMIT)]
    }


PAGES = {
    "general": _general,
    "model": _model,
    "spending": _spending,
    "messages": _messages,
    "lookups": _lookups,
    "happening": _happening,
    "connections": _connections,
    "security": _security,
    "troubleshooting": troubleshooting.page_data,
    "history": _history,
}


def setting_label(key: str) -> str:
    if key in KEY_LABELS:
        return KEY_LABELS[key]
    if key in fields.BY_KEY:
        return fields.BY_KEY[key].label
    if key in PROFILE_LABELS:
        return PROFILE_LABELS[key][:1].upper() + PROFILE_LABELS[key][1:]
    return {"web_password_hash": "Family password"}.get(key, key)


def change(line: dict[str, Any], tz: Any) -> dict[str, Any]:
    """One line of what has changed, in the pages' words."""
    row = views.change_row(line, tz)
    one = fields.BY_KEY.get(line["key"])
    if one is not None:
        row["old"], row["new"] = one.word(row["old"]), one.word(row["new"])
    return {**row, "label": setting_label(line["key"])}


def section_flags(
    app: App,
    conn: sqlite3.Connection,
    *,
    steps: dict[str, Any] | None = None,
    spent: float | None = None,
) -> dict[str, bool]:
    """Which pages of settings need a look: the one list the overview marks and the sidebar counts,
    so the two cannot disagree. `steps` and `spent` are for a caller that has them already."""
    live = app.settings
    if steps is None:
        steps = {step.name: step for step in status_page.setup_progress(app, conn)}
    if spent is None:
        spent = spent_today(conn, live, app.clock.now())
    limit = live.daily_spend_limit
    return {
        "general": not steps["home"].done,
        "model": not steps["model"].done,
        "spending": bool(limit) and spent >= limit,
        "security": not steps["password"].done,
    }


def needs_look(app: App, conn: sqlite3.Connection) -> int:
    """How many pages of settings need a look, for the sidebar's "1 to check"."""
    return sum(section_flags(app, conn).values())


def overview(*, said: str | None, error: str | None, status: int) -> tuple[str, int]:
    """Every settings page, each with a line or two on how it stands. No network."""
    app = _app()
    live = app.settings
    with closing(app.connect()) as conn:
        steps = {step.name: step for step in status_page.setup_progress(app, conn)}
        today = spent_today(conn, live, app.clock.now())
        flags = section_flags(app, conn, steps=steps, spent=today)
        latest = [change(line, live.tzinfo) for line in settings_store.history(conn, limit=1)]
        trouble_lines = troubleshooting.overview_lines(app, conn)
    hour = hour_words
    units = fields.BY_KEY["weather_units"].word(live.weather_units)
    if live.home_area and live.home_lat is not None:
        home = live.home_area
    elif live.home_area:
        home = f"{live.home_area}, not found on the map yet."
    else:
        home = "Home is not set yet, so there is no forecast and no travel times."
    limit = live.daily_spend_limit
    spend = f"About ${today:.2f} spent today."
    persona = personas.active(live)
    if live.persona == personas.NONE:
        who = "No persona: plain and brief."
    elif live.persona in live.persona_text:
        who = f"{persona.name}, in your words."
    else:
        # By label: two personas may share a name.
        who = f"{persona.listed_as}."
    if live.digest_chat_id:
        day = fields.BY_KEY["digest_day"].word(live.digest_day)
        weekend = f"Weekend ideas on {day}s at {hour(live.digest_hour)}."
    else:
        weekend = "No weekend ideas: no chat is chosen for them."
    if latest:
        last = latest[0]
        by = f", by {last['who']}" if last["who"] else ""
        changed = f"Last: {last['label']}, {last['when']}{by}."
    else:
        changed = "Nothing has been changed here yet."
    every = live.enrich_interval_minutes
    if not enrichment_available(live):
        lookups = "Off: ideas are not filled in from the web."
    elif app.can_ask("worker"):
        lookups = f"On: ideas are looked up every {every} minute{'' if every == 1 else 's'}."
    else:
        lookups = "On, but waiting for a key for the company that looks things up."
    states = {
        "general": ([home, f"{live.tz}, {units}"], flags["general"]),
        "model": ([steps["model"].detail], flags["model"]),
        "spending": (
            [f"Up to ${limit:.2f} a day." if limit else "No daily limit.", spend],
            flags["spending"],
        ),
        "messages": ([weekend, f"Asks how a plan went at {hour(live.follow_up_hour)}."], False),
        "lookups": ([lookups], False),
        "happening": ([views.happening_state(live)], False),
        "personality": (
            [
                who,
                "About the family: written."
                if live.about_family.strip()
                else "Nothing about the family yet.",
            ],
            False,
        ),
        "connections": (
            [f"Telegram: {steps['telegram'].detail}", f"Calendar: {steps['calendar'].detail}"],
            False,
        ),
        "security": ([steps["password"].detail], flags["security"]),
        "troubleshooting": (trouble_lines, False),
        "history": ([changed], False),
    }
    return (
        render_template(
            "settings.html",
            sections=[
                {
                    "section": one,
                    "lines": states[one.name][0],
                    "look": states[one.name][1],
                    "off": one.name == "lookups" and not enrichment_available(live),
                }
                for one in fields.SECTIONS
            ],
            said=said,
            error=error,
        ),
        status,
    )


@bp.get("/settings")
def show() -> tuple[str, int]:
    return page()


@bp.get("/settings/<name>")
def section(name: str) -> tuple[str, int]:
    if _section(name) is None:
        abort(404)
    return page(name)


def _with_ticked_feeds(form: Any) -> Any:
    """The calendars to read, as the page for things near home sends them: the ones the app
    proposed are ticks, each address the page showed among `proposed`, and the rest are lines in
    the box. One setting holds them all, so the ticks are folded into the box's lines here."""
    shown = form.getlist("proposed")
    if not shown or "event_feeds" not in form:
        return form
    ticked = [url for url in form.getlist("feed") if url in shown]
    typed = [line.strip() for line in form["event_feeds"].splitlines() if line.strip()]
    folded = form.copy()
    folded["event_feeds"] = "\n".join([*ticked, *(line for line in typed if line not in shown)])
    return folded


@bp.post("/settings")
def save() -> Response | tuple[str, int]:
    """Store the behaviour settings, or say which box is wrong and keep what was typed."""
    back = auth.setup_return(request.form.get("then"))
    here = _section(request.form.get("section"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, here, error=complaint)
    form = _with_ticked_feeds(request.form)
    values, problems = fields.read_form(form)
    typed = {one.key: fields.given(one, form) for one in fields.FIELDS if one.key in form}
    if not problems:
        stored = _stored()
        proposed = {**stored, **values}
        try:
            # Validate the whole configuration this would leave behind, not only the new boxes.
            candidate = apply_overrides(
                _app().base_settings,
                {key: value for key, value in proposed.items() if value is not None},
            )
        except ValidationError as exc:
            problems = problems_from(exc)
        else:
            problems = unknown_models(values, stored, candidate)
    if problems:
        if back is not None:
            return _answer(back, here, error=_problems_said(problems))
        # Drawn on the page the box is on; with none, every complaint is said at the top.
        owner = next((fields.SECTION_OF[key] for key in problems if key in fields.SECTION_OF), None)
        drawn = here or owner
        elsewhere = {k: why for k, why in problems.items() if fields.SECTION_OF.get(k) != drawn}
        error = _problems_said(elsewhere) if elsewhere else "Nothing was saved."
        return page(drawn, problems=problems, error=error, typed=typed, status=400)
    located, where = locate_home(values, stored)
    said = " ".join(part for part in (_said(_save({**values, **located})), where) if part)
    return _answer(back, here, said=said)


@bp.post("/settings/keys")
def save_keys() -> Response | tuple[str, int]:
    """Store or remove an API key. A key's value never reaches a log or the change history."""
    back = auth.setup_return(request.form.get("then"))
    here = _section(request.form.get("section"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, here, error=complaint, otherwise="model")
    values: dict[str, Any] = {}
    problems: dict[str, str] = {}
    for name in SECRETS:
        if request.form.get(f"remove_{name}"):
            values[name] = None
            continue
        given = request.form.get(name, "").strip()
        if not given:
            continue
        if any(character.isspace() for character in given):
            problems[name] = KEY_HAS_SPACES
        elif len(given) > fields.MAX_LENGTH:
            problems[name] = fields.TOO_LONG
        else:
            values[name] = given
    if problems:
        if back is not None:
            return _answer(back, here, error=" ".join(problems.values()))
        pages = {KEY_PAGES.get(name, "model") for name in problems}
        where = here or (pages.pop() if len(pages) == 1 else "model")
        return page(where, problems=problems, error="Nothing was saved.", status=400)
    return _answer(back, here, said=_said(_save(values), keys=True))


@bp.post("/settings/reveal")
def reveal() -> tuple[str, int]:
    """Show one key, once, after the sign-in password is typed again (a page left open on a phone
    must not hand a key to whoever picks it up). Guessing is locked out as at sign-in."""
    app = _app()
    if (complaint := auth.refused()) is not None:
        return page("security", error=complaint, status=400)
    name = request.form.get("key", "")
    if name not in SECRETS:
        return page("security", error=UNKNOWN_KEY, status=400)
    who = auth.client_address()
    attempt = f"{who} reveal"
    lockout = current_app.config["FAMILYDB_LOCKOUT"]
    now = app.clock.now()
    if lockout.locked(attempt, now):
        return page("security", error=LOCKED_OUT, status=429)
    if auth.visitor().signed_in:
        given = request.form.get("password", "")
        if not given:
            return page("security", error=NEEDS_PASSWORD, status=400)
        if not auth.confirms(given):
            lockout.failed(attempt, now)  # counted apart from sign-in
            return page("security", error=WRONG_PASSWORD, status=401)
        lockout.passed(attempt)
    value = getattr(app.settings, name) or ""
    if not value:
        return page("security", error=f"There is no {KEY_LABELS[name]} to show.", status=404)
    log.warning("%s was shown to %s", name, who)
    return page(
        "security",
        revealed=(name, value),
        said=f"The {KEY_LABELS[name]} is shown below, this once.",
    )


@bp.post("/settings/export")
def export_everything() -> Response | tuple[str, int]:
    """Everything the family has kept, as one JSON file (export.py), after the sign-in password
    is typed again as for showing a key, and counted with it against guessing."""
    app = _app()
    if (complaint := auth.refused()) is not None:
        return page("security", error=complaint, status=400)
    who = auth.client_address()
    attempt = f"{who} reveal"
    lockout = current_app.config["FAMILYDB_LOCKOUT"]
    now = app.clock.now()
    if lockout.locked(attempt, now):
        return page("security", error=LOCKED_OUT, status=429)
    if auth.visitor().signed_in:
        given = request.form.get("password", "")
        if not given:
            return page("security", error=NEEDS_PASSWORD, status=400)
        if not auth.confirms(given):
            lockout.failed(attempt, now)
            return page("security", error=WRONG_PASSWORD, status=401)
        lockout.passed(attempt)
    with closing(app.connect()) as conn:
        text = export.everything_json(conn, now)
    log.warning("everything the family keeps was taken away by %s", who)
    response = Response(text, mimetype="application/json")
    response.headers["Content-Disposition"] = 'attachment; filename="familydb-everything.json"'
    response.headers["Cache-Control"] = "no-store"
    return response


# -- which company answers, and its key --------------------------------------------------------

UNKNOWN_COMPANY = "Choose one of the three companies."
NO_KEY_GIVEN = "Paste the key first."
KEY_REFUSED = (
    "{company} did not accept that key, so it was not saved. Copy it again from {company}'s "
    "API keys page, all of it, and paste it here."
)
KEY_VERDICTS = {
    "works": "{company} accepted the key. {name} answers with {model}.",
    "unknown_model": (
        "Saved. {company} accepted the key, but says it has no model called {model}: choose "
        "another under Models, on the AI model page of the settings."
    ),
    "unchecked": (
        "Saved. {company} could not be asked just now, so the key is not checked yet; the first "
        "message will show whether it works."
    ),
}


@bp.post("/settings/model")
def save_model() -> Response | tuple[str, int]:
    """Which company answers, and its key, checked with the company (the free model lookup)
    before anything is kept. Only a definite "wrong key" stops the save."""
    app = _app()
    back = auth.setup_return(request.form.get("then"))
    here = _section(request.form.get("section"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, here, error=complaint, otherwise="model")
    company = request.form.get("provider", "")
    if company not in providers.NAMES:
        return _answer(back, here, error=UNKNOWN_COMPANY, otherwise="model")
    name = f"{company}_api_key"
    given = request.form.get("key", "").strip()
    values: dict[str, Any] = {}
    if given:
        if any(character.isspace() for character in given):
            return _answer(back, here, error=KEY_HAS_SPACES, otherwise="model")
        if len(given) > fields.MAX_LENGTH:
            return _answer(back, here, error=fields.TOO_LONG, otherwise="model")
        values[name] = given
    elif not getattr(app.settings, name):
        return _answer(back, here, error=NO_KEY_GIVEN, otherwise="model")
    # The environment's own choice is not stored over it.
    values["provider"] = None if company == app.base_settings.provider else company
    stored = _stored()
    try:
        candidate = apply_overrides(
            app.base_settings,
            {key: value for key, value in {**stored, **values}.items() if value is not None},
        )
    except ValidationError as exc:
        return _answer(back, here, error=" ".join(problems_from(exc).values()), otherwise="model")
    chosen = providers.build(company, candidate)
    verdict = chosen.check_key()
    label = COMPANIES[company]
    if verdict == "refused":
        return _answer(back, here, error=KEY_REFUSED.format(company=label), otherwise="model")
    _save(values)
    said = KEY_VERDICTS.get(verdict, KEY_VERDICTS["unchecked"])
    her = personas.active(candidate).name
    # The check asked about the everyday model, which a "no such model" names.
    asked = chosen.model_for("chat")
    answers = providers.model_at(chosen, "chat", candidate.chat_level)
    model = asked if verdict == "unknown_model" else answers
    return _answer(back, here, said=said.format(company=label, model=model, name=her))


# -- the family password ----------------------------------------------------------------------

PASSWORD_SAVED = "Saved. That is the family password now: every other browser will ask for it."
PASSWORD_TWICE = "The two new passwords were not the same. Type them again."
PASSWORD_SHORT = (
    "That one is {length} characters. It needs at least {least}: a short sentence is easy to "
    "remember and long enough."
)
PASSWORD_LONG = "That is longer than a password needs to be."
PASSWORD_CURRENT = "Type the password you use now, to show it is you."
NO_FAMILY_PASSWORD = (
    "Everybody signs in as themselves now, so there is no family password to change. Change "
    "your own on the Your password page."
)
MAX_PASSWORD = passwords.MAX_LENGTH
# The first choice may skip retyping the installer's password, within this long of signing in.
FIRST_CHOICE_MINUTES = 60


def current_password_needed(live: Any) -> bool:
    """Whether changing the password asks for the one in force: always, except the first choice
    soon after signing in with the installer's."""
    if not auth.password_in_use(live):
        return False
    if auth.password_chosen(live):
        return True
    signed_in = session.get(auth.SIGNED_IN_AT)
    now = _app().clock.now().timestamp()
    return not (isinstance(signed_in, int) and 0 <= now - signed_in <= FIRST_CHOICE_MINUTES * 60)


@bp.post("/settings/password")
def change_password() -> Response | tuple[str, int]:
    """Choose the family password, stored hashed; this browser stays signed in, the rest do not.
    It asks for the one in force, so a phone left signed in cannot lock the family out."""
    app = _app()
    back = auth.setup_return(request.form.get("then"))
    here = _section(request.form.get("section"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, here, error=complaint, otherwise="security")
    if auth.visitor().kind == "person":
        return _answer(back, here, error=NO_FAMILY_PASSWORD, status=409, otherwise="security")
    new, again = request.form.get("new", ""), request.form.get("again", "")
    if new != again:
        return _answer(back, here, error=PASSWORD_TWICE, otherwise="security")
    if len(new) < auth.MIN_PASSWORD:
        return _answer(
            back,
            here,
            error=PASSWORD_SHORT.format(length=len(new), least=auth.MIN_PASSWORD),
            otherwise="security",
        )
    if len(new) > MAX_PASSWORD:
        return _answer(back, here, error=PASSWORD_LONG, otherwise="security")
    live = app.settings
    if current_password_needed(live):
        who = auth.client_address()
        attempt = f"{who} password"  # counted apart from sign-in
        lockout = current_app.config["FAMILYDB_LOCKOUT"]
        now = app.clock.now()
        if lockout.locked(attempt, now):
            return _answer(back, here, error=LOCKED_OUT, status=429, otherwise="security")
        given = request.form.get("current", "")
        if not auth.password_matches(live, given):
            lockout.failed(attempt, now)
            return _answer(
                back,
                here,
                error=WRONG_PASSWORD if given else PASSWORD_CURRENT,
                status=401,
                otherwise="security",
            )
        lockout.passed(attempt)
    _save({"web_password_hash": passwords.hash_password(new)})
    log.warning("the family password was changed from the page by %s", auth.client_address())
    # Every session carried the old password's mark and ends; this one is marked again.
    session[auth.SESSION_KEY] = True
    session[auth.PASSWORD_KEY] = auth.password_mark(app.settings)
    response = _answer(back, here, said=PASSWORD_SAVED)
    auth.remember_device(response, app.settings)
    return response


KEY_PINNED = (
    "The signing key is set in WEB_SECRET_KEY, so only changing it there, and restarting, signs "
    "everyone out."
)


# -- who she is, and who the family are ---------------------------------------------------------

RESTORED = "Restored her original description."
PROFILE_LABELS = {
    "voice_lines": "what she says unasked",
    "persona": "personality",
    "persona_name": "her name",
    "persona_text": "her description",
    "persona_notes": "notes on how she talks",
    "about_family": "about the family",
}
# A rough count of what a description adds to every message; /status has the real one.
CHARS_PER_TOKEN = 4
# Her lines grouped for the Personality page, each with whether it starts folded. A line no group
# names (a new one in voice.EVENTS) is shown under "Other".
LINE_GROUPS = (
    (
        "Reminders and follow-ups",
        False,
        (
            "reminder",
            "reminder_late",
            "reminder_from",
            "reminder_plan",
            "gift_ideas",
            "gift_ideas_none",
            "birthday_wishes",
            "nudge",
            "push_note",
            "morning",
            "morning_ending",
            "morning_chase",
            "morning_deadlines",
            "morning_roundup",
            "plan_rain",
            "plan_rain_today",
            "plan_closed",
            "plan_closed_today",
            "plan_backup",
            "follow_up",
        ),
    ),
    (
        "When a button is tapped",
        True,
        (
            "tap_done",
            "tap_done_again",
            "tap_snoozed",
            "tap_undone",
            "tap_ticked",
            "tap_again",
            "tap_ok",
            "tap_not_again",
            "tap_missed",
            "tap_wish_yes",
            "tap_wish_no",
            "tap_later",
            "tap_parents_only",
            "tap_already",
            "tap_stale",
            "tap_failed",
            "tap_stranger",
        ),
    ),
    (
        "The kids' wish lists",
        True,
        ("wish_granted", "wish_declined", "kid_flagged", "kid_asks_parent"),
    ),
    ("Notes", False, ("lookup_done", "lookups_done", "location_shared", "done")),
    (
        "On Telegram",
        False,
        (
            "start",
            "stranger",
            "cannot_read",
            "invite_linked",
            "invite_stale",
            "invite_taken",
            "joined_group",
            "joined_group_mentioned",
        ),
    ),
    (
        "Answering /today, /week, /tasks, /now and /lookup",
        True,
        (
            "cmd_today",
            "cmd_week",
            "cmd_tasks",
            "cmd_now",
            "cmd_list",
            "cmd_list_empty",
            "undo_done",
            "undo_not",
            "lookups_asked",
            "lookups_none",
            "lookups_off",
        ),
    ),
    (
        "When she cannot answer",
        True,
        (
            "kid_limit",
            "limit_reached",
            "kid_share",
            "kid_later",
            "kid_tomorrow",
            "kid_type_it",
            "limit_partial",
            "gave_up",
            "gave_up_partly",
            "retry_later",
            "cannot_reach",
            "no_key",
            "voice_off",
            "voice_no_ears",
            "voice_too_long",
            "voice_unheard",
            "photo_off",
            "photo_too_large",
            "photo_unseen",
        ),
    ),
    (
        "Telling an admin what needs fixing",
        True,
        (
            "alert_credit",
            "alert_key",
            "alert_limit",
            "alert_calendar",
            "alert_calendar_access",
            "alert_model",
            "alert_price",
            "alert_prices",
            "alert_new",
            "alert_shift",
            "alert_api",
            "alert_refused",
            "alert_advice",
            "alert_happening",
            "alert_calendars",
            "alert_backup",
            "alert_disk",
            "alert_telegram",
        ),
    ),
)


def personality_page(
    *,
    said: str | None = None,
    error: str | None = None,
    typed: dict[str, str] | None = None,
    status: int = 200,
) -> tuple[str, int]:
    live = _app().settings
    speaking = personas.active(live)
    if said is None:
        told = get_flashed_messages(category_filter=[NOTICE])
        said = told[0] if told else None
    typed = typed or {}
    chosen = personas.key_for(typed.get("persona", live.persona))
    # The description box describes the persona in force, whichever the list has chosen. Under
    # none nobody is described and there is no box.
    described = live.persona
    plain = described == personas.NONE
    typed_for_her = personas.key_for(typed.get("described", described)) == described
    text = (typed.get("persona_text", "") if typed_for_her else "") or speaking.character
    name = typed.get("persona_name", live.persona_name)
    notes = typed.get("persona_notes", live.persona_notes)
    about = typed.get("about_family", live.about_family)
    # Their rewrite remembers her description as it was then (`of`); without it, no telling.
    rewrite = None if plain else live.persona_text.get(described)
    changes = (
        views.line_changes(rewrite.of, personas.load(described).character)
        if rewrite and rewrite.of
        else []
    )
    hers = voice.wording(personas.load(live.persona))
    lines = {
        name: {
            "event": name,
            "label": event.label,
            "value": typed.get(f"line_{name}", voice.boxed(live.voice_lines.get(name, ""))),
            "placeholder": voice.boxed(hers[name]),
            "fields": ", ".join("{" + f + "}" for f in voice.usable(name)),
            "reads": voice.reads_as(live, name),
        }
        for name, event in voice.EVENTS.items()
    }
    named = {name for _, _, names in LINE_GROUPS for name in names}
    groups = [
        (title, folded, [lines[name] for name in names if name in lines])
        for title, folded, names in LINE_GROUPS
    ]
    if others := [line for name, line in lines.items() if name not in named]:
        groups.append(("Other", False, others))
    return (
        render_template(
            "settings_section.html",
            section=fields.SECTION_BY_NAME["personality"],
            sections=fields.SECTIONS,
            said=said,
            error=error,
            chosen=chosen,
            choices=_choices(live),
            described=described,
            name=name,
            own_name=personas.load(live.persona).name,
            text=text,
            rewritten=rewrite is not None,
            changes=changes,
            notes=notes,
            kept=plain and any(key in personas.available() for key in live.persona_text),
            about=about,
            line_groups=[
                {
                    "title": title,
                    "lines": shown,
                    "folded": folded and not any(line["value"] for line in shown),
                    "own": sum(1 for line in shown if line["value"]),
                }
                for title, folded, shown in groups
            ],
            plain=plain,
            her_name=speaking.name,
            tokens=(len(speaking.prompt) + len(live.about_family)) // CHARS_PER_TOKEN,
            limits={
                "persona_name": Settings.model_fields["persona_name"].metadata[0].max_length,
                "persona_text": PersonaRewrite.model_fields["text"].metadata[0].max_length,
                "persona_notes": Settings.model_fields["persona_notes"].metadata[0].max_length,
                "about_family": Settings.model_fields["about_family"].metadata[0].max_length,
            },
        ),
        status,
    )


@bp.get("/settings/personality")
def personality() -> tuple[str, int]:
    return personality_page()


@bp.post("/settings/personality")
def save_personality() -> Response | tuple[str, int]:
    """Who she is and who the family are. The description box rewrites the persona it described
    when the page was drawn, never one chosen in the same save. A box not sent (none under the
    none persona) leaves what it stands for as it was. Her own text or name is no rewrite."""
    if (complaint := auth.refused()) is not None:
        return personality_page(error=complaint, status=400)
    typed = {
        name: request.form.get(name, "") for name in ("persona", "persona_text", "about_family")
    }
    typed.update(
        {
            name: request.form[name]
            for name in ("described", "persona_name", "persona_notes")
            if name in request.form
        }
    )
    live = _app().settings
    written = {
        name: _line(request.form.get(f"line_{name}", ""), live.voice_lines.get(name))
        for name in voice.EVENTS
    }
    written = {name: line for name, line in written.items() if line}
    typed.update({f"line_{name}": voice.boxed(line) for name, line in written.items()})
    if wrong := voice.problems(written):
        what = "; ".join(f"{voice.EVENTS[n].label}: {why}" for n, why in wrong.items())
        return personality_page(error=f"Nothing was saved. {what}.", typed=typed, status=400)
    chosen = personas.key_for(typed["persona"])
    hers = voice.wording(personas.load(live.persona))
    values: dict[str, Any] = {
        # What the environment already says is not stored over it.
        "persona": None if chosen == _app().base_settings.persona else chosen,
        "about_family": typed["about_family"].replace("\r\n", "\n").strip() or None,
        "voice_lines": {
            name: line for name, line in written.items() if voice.wordings(line) != hers[name]
        }
        or None,
    }
    if "persona_name" in request.form:
        # An empty box, or her own name, is no name of theirs, stored only over an environment name.
        called = typed["persona_name"].strip()
        if called == personas.load(live.persona).name:
            called = ""
        values["persona_name"] = None if called == _app().base_settings.persona_name else called
    if "persona_notes" in request.form:
        notes = typed["persona_notes"].replace("\r\n", "\n").strip()
        values["persona_notes"] = None if notes == _app().base_settings.persona_notes else notes
    if "persona_text" in request.form:
        described = personas.key_for(typed.get("described", live.persona))
        text = typed["persona_text"].replace("\r\n", "\n").strip()
        rewrites = _rewritten(live, described, text)
        if rewrites != _rewrites(live):
            values["persona_text"] = _keeping(rewrites)
    try:
        apply_overrides(
            _app().base_settings,
            {k: v for k, v in {**_stored(), **values}.items() if v is not None},
        )
    except ValidationError as exc:
        problems = problems_from(exc)
        return personality_page(
            error="Nothing was saved. " + " ".join(problems.values()), typed=typed, status=400
        )
    flash(_said(_save(values)), NOTICE)
    return redirect(url_for("settings.personality"))


@bp.post("/settings/personality/restore")
def restore_personality() -> Response | tuple[str, int]:
    """Her original description again: the described persona's rewrite goes, and nobody else's."""
    if (complaint := auth.refused()) is not None:
        return personality_page(error=complaint, status=400)
    live = _app().settings
    described = personas.key_for(request.form.get("described", live.persona))
    rewrites = _rewrites(live)
    if rewrites.pop(described, None) is not None:
        _save({"persona_text": _keeping(rewrites)})
    flash(RESTORED, NOTICE)
    return redirect(url_for("settings.personality"))


def _line(box: str, stored: voice.Line | None) -> voice.Line:
    """What a line's box says: one wording to a row, a string for one and a list for several. A box
    left as drawn keeps the stored line, so a wording with line breaks stays one wording."""
    rows = _rows(box)
    if not rows:
        return ""
    if stored is not None and rows == _rows(voice.boxed(stored)):
        return stored
    return rows[0] if len(rows) == 1 else rows


def _rows(box: str) -> list[str]:
    return [row.strip() for row in box.splitlines() if row.strip()]


def _rewrites(settings: Settings) -> dict[str, dict[str, str]]:
    return {key: rewrite.model_dump() for key, rewrite in settings.persona_text.items()}


def _rewritten(live: Settings, described: str, text: str) -> dict[str, dict[str, str]]:
    """The rewrites with the described persona's as her box now says. A blank box or her own
    character is no rewrite; an unchanged text keeps theirs; a new one is written against her
    character now, so the page can tell later when hers changes."""
    rewrites = _rewrites(live)
    if described not in personas.available():
        return rewrites
    own = personas.load(described)
    theirs = live.persona_text.get(described)
    if not text or text in (own.character, own.prompt):
        rewrites.pop(described, None)
    elif theirs is None or theirs.text.strip() != text:
        rewrites[described] = {"text": text, "of": own.character}
    return rewrites


def _keeping(rewrites: dict[str, dict[str, str]]) -> dict[str, dict[str, str]] | None:
    """What to store: nothing when they are what the environment says."""
    return None if rewrites == _rewrites(_app().base_settings) else rewrites


def _choices(live: Settings) -> list[dict[str, Any]]:
    """Each persona with a folder, the default first, as she would be if chosen, with roughly
    what she would add to every message (their rewrite and notes included)."""
    choices = []
    for key in sorted(personas.available(), key=lambda key: key != personas.DEFAULT):
        her = personas.active(live.model_copy(update={"persona": key}))
        tokens = len(her.prompt) // CHARS_PER_TOKEN
        choices.append({"key": key, "label": her.listed_as, "tokens": tokens})
    return choices


@bp.post("/settings/sign-out-everyone")
def sign_out_everyone() -> Response | tuple[str, int]:
    """End every session on every device, this one included, after the sign-in password is typed
    again: every cookie and known-browser mark was signed with the key this replaces."""
    app = _app()
    if (complaint := auth.refused()) is not None:
        return page("security", error=complaint, status=400)
    who = auth.client_address()
    attempt = f"{who} reveal"
    lockout = current_app.config["FAMILYDB_LOCKOUT"]
    now = app.clock.now()
    if lockout.locked(attempt, now):
        return page("security", error=LOCKED_OUT, status=429)
    if auth.visitor().signed_in:
        if not auth.confirms(request.form.get("password", "")):
            lockout.failed(attempt, now)
            return page("security", error=WRONG_PASSWORD, status=401)
        lockout.passed(attempt)
    fresh = keys.rotate(app.settings)
    if fresh is None:
        return page("security", error=KEY_PINNED, status=409)
    current_app.secret_key = fresh
    session.clear()
    log.warning("%s signed everyone out", who)
    return redirect(url_for("auth.login"))


@bp.post("/settings/google/connect")
def google_connect() -> Response | tuple[str, int]:
    """Keep the service account key and calendar id only if the calendar can be read and changed."""
    app = _app()
    back = auth.setup_return(request.form.get("then"))
    if (complaint := auth.refused()) is not None:
        return _google_answer(back, error=complaint)
    calendar_id = request.form.get("calendar_id", "").strip()
    try:
        info = google.service_account_key(request.form.get("key", ""))
        google.check_access(info, calendar_id)
    except google.GoogleSetupError as exc:
        return _google_answer(back, error=str(exc))
    google.save_key(Path(app.settings.google_key_path), json.dumps(info))
    _save({"google_calendar_id": calendar_id})
    app.forget_calendar()
    log.info("Google Calendar connected from the page by %s", auth.client_address())
    return _google_answer(back, said=CALENDAR_CONNECTED.format(name=calendar_id))


def _google_answer(
    back: str | None, *, said: str | None = None, error: str | None = None
) -> Response | tuple[str, int]:
    return _answer(back, "connections", said=said, error=error)


def _problems_said(problems: dict[str, str]) -> str:
    """Every complaint, in one line, named by its box."""
    named = [
        f"{fields.BY_KEY[key].label}: {why}" if key in fields.BY_KEY else why
        for key, why in problems.items()
    ]
    return "Nothing was saved. " + " ".join(named)


def _key_order(provider: str) -> list[str]:
    """The answering company's key first, as a new install needs it."""
    first = f"{provider}_api_key"
    return sorted(SECRETS, key=lambda name: (name != first, name in KEY_PAGES))


def _said(changed: list[str], *, keys: bool = False) -> str:
    if not changed:
        return NOTHING_CHANGED
    labels = [
        KEY_LABELS.get(name, name)
        if keys
        else (
            fields.BY_KEY[name].label if name in fields.BY_KEY else PROFILE_LABELS.get(name, name)
        )
        for name in changed
    ]
    return SAVED.format(what=f"Changed: {', '.join(labels)}.")
