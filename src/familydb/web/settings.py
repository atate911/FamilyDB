"""The settings pages: the only part of the web surface that writes settings.

It writes to one place and one place only, `app_settings`, through `store.settings`. Nothing
here can reach an idea, a plan or a message. Every change is logged, and a key's value is never
what gets logged: only that it was replaced.

/settings says how each part stands, in a line or two, and each part has a page of its own,
/settings/<name> (`fields.SECTIONS`). Every form on one of those pages says which page it is on,
so what it did is said on the page it was sent from. A form that names no page (from an older
page, or a test) comes back to /settings, and a complaint about it is drawn on the page its boxes
are on.

The Personality page (/settings/personality) writes the six `PROFILE` settings: which persona,
the name the family call her, her description as the family rewrote it, their notes on how she
talks, her lines likewise, and the family's words about themselves. Her description is shown and
kept as written, with {name} where her name goes, and a rewrite of it is kept for the persona it
describes, the one in force when the page was drawn; when her own has changed since, the page
says so and shows how. Their name for her and their notes are theirs whoever she is: the name is
what {name} says, and the notes follow her description, so they last when hers is improved or
rewritten. A line of hers may have several wordings, one to a row of its box, and under each box
the page shows how the line in force reads, filled in with example facts by `voice.reads_as`.

Two kinds of form, because they are not the same kind of thing. A page's behaviour form carries
every box on that page each time it is sent, so an emptied box means "go back to the default";
the boxes of other pages are not in it, and are left alone. The keys form carries only what
someone typed: an empty key box means "leave that one alone", since a password box is empty
every time the page is drawn.
"""

from __future__ import annotations

import logging
import secrets
import time
from contextlib import closing
from pathlib import Path
from typing import Any

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

from familydb import passwords, personas, voice
from familydb.agent import gateway, providers
from familydb.agent.spending import spent_today
from familydb.app import App
from familydb.availability import enrichment_available
from familydb.config import PersonaRewrite, Settings, apply_overrides
from familydb.integrations import google_calendar as google
from familydb.store import settings as settings_store
from familydb.store.db import transaction
from familydb.store.settings import SECRETS
from familydb.web import auth, fields, keys, views
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
# Which company each model box belongs to, so a new name can be checked with that company.
MODEL_BOXES = {
    one.key: (one.company, COMPANIES[one.company]) for one in fields.FIELDS if one.company
}
# Which surface each level box chooses a model for: that of the kinds of call that read it.
LEVEL_BOXES = {call.level: call.surface for call in gateway.KINDS.values()}
KEY_LABELS = {
    "anthropic_api_key": "Anthropic key",
    "openai_api_key": "OpenAI key",
    "gemini_api_key": "Google key",
    "telegram_bot_token": "Telegram bot token",
}


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
    """Where a form's result goes: back to the setup page that sent it, or to the settings page
    it was sent from. A complaint about a form that named no page is drawn on `otherwise`, the
    page its boxes are on."""
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
    """Write the changes and log them, with who made them when the page knows. Returns the keys
    that actually moved."""
    app = _app()
    source = f"web {auth.client_address()}"
    me = auth.visitor().member
    with closing(app.connect()) as conn, transaction(conn):
        changed = settings_store.set_many(
            conn, values, changed_by=me.id if me else None, source=source
        )
    if changed:
        app.refresh()  # the page it redirects to should already show the new state
        log.info("settings changed from the page: %s", ", ".join(changed))
    return changed


def unknown_models(values: dict[str, Any], stored: dict[str, Any], proposed: Settings) -> dict:
    """The model names this save would introduce that their company says do not exist.

    Asked only about a name that is changing, and only a definite no counts: a company that
    cannot be reached, or has no key yet, is not a reason to refuse what was typed.
    """
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
    """Coordinates for a home area typed on the page, looked up as the installer used to.

    Only when the area is changing and no new coordinates were typed with it: coordinates typed
    by hand win. Returns the coordinates to store, and a sentence saying what happened.
    """
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
    """Pydantic's complaints, one sentence per box, in the words it used."""
    found: dict[str, str] = {}
    for error in exc.errors(include_url=False):
        key = str(error["loc"][0]) if error["loc"] else ""
        found.setdefault(key, error["msg"])
    return found


# Connecting Google from the page: the consent started, and the calendars found once it finished.
# In memory, like the form tokens: a restart in the middle means starting the connection again.
GOOGLE_KEY = "google_consent"
CONSENT_MINUTES = 15
GOOGLE_EXPIRED = "That connection was started too long ago, or before a restart. Start again."
CALENDAR_SET = "Saved. The bot now uses {name}."


def _consents() -> dict[str, dict[str, Any]]:
    return current_app.config.setdefault("FAMILYDB_GOOGLE", {})


def _pending() -> dict[str, Any] | None:
    """This session's consent in progress, if it is recent enough to finish."""
    found = _consents().get(session.get(GOOGLE_KEY, ""))
    if found is None or time.monotonic() - found["started"] > CONSENT_MINUTES * 60:
        return None
    return found


def suggested(one: fields.Field) -> list[tuple[str, str]]:
    """The names a box suggests as it is typed in, each with a word on what it is: a model's
    place in its company's lineup, and its price."""
    company = MODEL_BOXES.get(one.key, ("", ""))[0]
    return [(name, views.model_offer(company, name)) for name in one.suggested]


def level_labels(key: str, live: Settings) -> dict[str, str]:
    """For a level box, what each level means on the company that answers it now."""
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
    pending = _pending()
    return {
        "connected": Path(live.google_token_path).exists(),
        "calendar": live.google_calendar_id,
        "consent_url": pending["url"] if pending and "calendars" not in pending else None,
        "calendars": pending.get("calendars") if pending else None,
    }


# -- the three companies, as setup and the AI model page both offer them -------------------------

# Who each company is, in a line, for choosing between them. The default model's price decides
# the order of the words, not a preference: prices.py is where the numbers are.
COMPANY_LINES = {
    "openai": "The least expensive by far for what FamilyDB does, so it is the one it starts with.",
    "anthropic": "Claude. Several times dearer a message with the model it starts on.",
    "gemini": "Gemini, from Google. In between on price.",
}
KEY_STARTS = {"openai": "sk-", "anthropic": "sk-ant-", "gemini": "AIza"}


def company_choice(live: Settings, asked: str) -> dict[str, Any]:
    """The three companies to choose between, and the one whose key is shown: the one asked for
    in the address, or else the one answering now."""
    company = asked if asked in providers.NAMES else live.provider
    return {
        "company": company,
        "label": COMPANIES[company],
        "prefix": KEY_STARTS[company],
        "has_key": bool(getattr(live, f"{company}_api_key")),
        "answering": live.provider,
        # What it answers the family with: its everyday model, or a stronger one a level up.
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
) -> dict[str, Any]:
    return {
        "field": one,
        "value": typed.get(one.key, fields.shown(one, overrides.get(one.key))),
        "placeholder": fields.placeholder(one, fields.fallback(one, base)),
        "problem": problems.get(one.key),
        "stored": one.key in overrides,
        "offers": offers.get(one.key) or suggested(one),
        "labels": level_labels(one.key, live),
    }


def _group(group: fields.Group, boxes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "group": group,
        "boxes": boxes,
        # A folded group opens by itself when it holds a complaint, so nobody hunts for it.
        "open": any(box["problem"] for box in boxes),
        "changed": sum(1 for box in boxes if box["stored"]),
    }


def _key_rows(
    live: Settings,
    overrides: dict[str, Any],
    problems: dict[str, str],
    revealed: tuple[str, str] | None,
) -> dict[str, dict[str, Any]]:
    """Every key and token, whether there is one and where it came from, answering company's
    first, as that is the one a new install needs."""
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
    """Draw one settings page, or with no section the list of them. Everything it shows is read
    fresh, so a save is visible at once."""
    if said is None:
        # What the last save said, handed over by the redirect that followed it. Named,
        # because the edit forms flash too and their notices belong on their own pages.
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
    groups = {
        group.name: _group(
            group,
            [
                _box(one, overrides, app.base_settings, problems, typed or {}, offers, live)
                for one in group.fields
            ],
        )
        for group in fields.groups_in(section)
    }
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
            # Whose password is typed again before a key is shown: their own, or the family's.
            own_password=auth.visitor().login is not None,
            **extra,
        ),
        status,
    )


def _general(app: App, conn: Any) -> dict[str, Any]:
    return {"offers": {"family_tz": [(zone, "") for zone in fields.zones()]}}


def _model(app: App, conn: Any) -> dict[str, Any]:
    """The company answering, and the two models at work, shown before everything else."""
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
    }


def _lookups(app: App, conn: Any) -> dict[str, Any]:
    return {"on": enrichment_available(app.settings), "can_look": app.can_ask("worker")}


def _connections(app: App, conn: Any) -> dict[str, Any]:
    return {
        "google": google_panel(app.settings),
        "bot": status_page.telegram_name(app),
        "telegram": app.channel_states.get("telegram", ""),
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
    "connections": _connections,
    "security": _security,
    "history": _history,
}


def setting_label(key: str) -> str:
    """A setting by the name the pages give it."""
    if key in KEY_LABELS:
        return KEY_LABELS[key]
    if key in fields.BY_KEY:
        return fields.BY_KEY[key].label
    if key in PROFILE_LABELS:
        return PROFILE_LABELS[key][:1].upper() + PROFILE_LABELS[key][1:]
    return {"web_password_hash": "Family password"}.get(key, key)


def change(line: dict[str, Any], tz: Any) -> dict[str, Any]:
    """One line of what has changed, in the words the pages use for the setting and its values."""
    row = views.change_row(line, tz)
    one = fields.BY_KEY.get(line["key"])
    if one is not None:
        row["old"], row["new"] = one.word(row["old"]), one.word(row["new"])
    return {**row, "label": setting_label(line["key"])}


def overview(*, said: str | None, error: str | None, status: int) -> tuple[str, int]:
    """Every settings page, each with a line or two on how it stands. Reads only; no network."""
    app = _app()
    live = app.settings
    with closing(app.connect()) as conn:
        steps = {step.name: step for step in status_page.setup_progress(app, conn)}
        today = spent_today(conn, live, app.clock.now())
        latest = [change(line, live.tzinfo) for line in settings_store.history(conn, limit=1)]
    hour = "{:02d}:00".format
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
        # By her label, which says which of her it is: two personas may share a name.
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
        "general": ([home, f"{live.tz}, {units}"], not steps["home"].done),
        "model": ([steps["model"].detail], not steps["model"].done),
        "spending": (
            [f"Up to ${limit:.2f} a day." if limit else "No daily limit.", spend],
            bool(limit) and today >= limit,
        ),
        "messages": ([weekend, f"Asks how a plan went at {hour(live.follow_up_hour)}."], False),
        "lookups": ([lookups], False),
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
        "security": ([steps["password"].detail], not steps["password"].done),
        "history": ([changed], False),
    }
    return (
        render_template(
            "settings.html",
            sections=[
                {"section": one, "lines": states[one.name][0], "look": states[one.name][1]}
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


@bp.post("/settings")
def save() -> Response | tuple[str, int]:
    """Store the behaviour settings, or say which box is wrong and keep what was typed."""
    back = auth.setup_return(request.form.get("then"))
    here = _section(request.form.get("section"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, here, error=complaint)
    values, problems = fields.read_form(request.form)
    typed = {one.key: request.form[one.key] for one in fields.FIELDS if one.key in request.form}
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
        # Drawn on the page the box is on, so the complaint is beside it. With no such page
        # (a complaint about no box in particular), every complaint is said at the top.
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
        where = here or ("connections" if set(problems) == {"telegram_bot_token"} else "model")
        return page(where, problems=problems, error="Nothing was saved.", status=400)
    return _answer(back, here, said=_said(_save(values), keys=True))


@bp.post("/settings/reveal")
def reveal() -> tuple[str, int]:
    """Show one key, once, after the password this browser signed in with is typed again: the
    person's own, or the family's while they share one.

    Signing in weeks ago is not enough: a page left open on a phone should not hand a key to
    whoever picks it up. Guessing here is counted and locked out the same way signing in is.
    """
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
            lockout.failed(attempt, now)  # counted apart from signing in, and logged there
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
    """Which company answers, and its key, checked with that company before anything is kept.

    The check is the free model lookup the model boxes already use. Only a definite "that key is
    wrong" stops the save: a company that cannot be reached is no reason to refuse what was pasted.
    """
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
    # The environment's own choice is not stored over it, as on the rest of the page.
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
    # The check asked about the everyday model, so that is the one a "no such model" names.
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
# The family's first choice may skip typing the installer's password again, which they have only
# just typed to sign in, but only within this long of signing in with it.
FIRST_CHOICE_MINUTES = 60


def current_password_needed(live: Any) -> bool:
    """Whether changing the password asks for the one in force: always, except for the first one
    the family chooses, soon after signing in with the installer's."""
    if not auth.password_in_use(live):
        return False
    if auth.password_chosen(live):
        return True
    signed_in = session.get(auth.SIGNED_IN_AT)
    now = _app().clock.now().timestamp()
    return not (isinstance(signed_in, int) and 0 <= now - signed_in <= FIRST_CHOICE_MINUTES * 60)


@bp.post("/settings/password")
def change_password() -> Response | tuple[str, int]:
    """Choose the family password. Stored hashed; this browser stays signed in, the rest do not.

    It asks for the password in force, as every change of password should, so a phone left signed
    in cannot be used to lock the family out of their own page.
    """
    app = _app()
    back = auth.setup_return(request.form.get("then"))
    here = _section(request.form.get("section"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, here, error=complaint, otherwise="security")
    if auth.visitor().kind == "person":
        # Somebody signed in as themselves, so the shared password already opens nothing.
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
        attempt = f"{who} password"  # counted apart from signing in, like showing a key
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
    # Every session was marked with the old password and so ends; this one is marked again.
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
# A rough count, to say what a description adds to every message; the real one is on /status.
CHARS_PER_TOKEN = 4
# Her lines as the Personality page groups them, each group with whether it starts folded. A line
# no group names (a new one in voice.EVENTS) is shown under "Other", so it is never left off.
LINE_GROUPS = (
    (
        "Reminders and follow-ups",
        False,
        ("reminder", "reminder_late", "gift_ideas", "gift_ideas_none", "nudge", "follow_up"),
    ),
    (
        "When a button is tapped",
        True,
        (
            "tap_done",
            "tap_done_again",
            "tap_snoozed",
            "tap_again",
            "tap_not_again",
            "tap_missed",
            "tap_already",
            "tap_stale",
            "tap_failed",
            "tap_stranger",
        ),
    ),
    ("Notes", False, ("lookup_done", "location_shared", "done")),
    ("On Telegram", False, ("start", "stranger")),
    (
        "When she cannot answer",
        True,
        (
            "limit_reached",
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
    # The description box describes the persona in force, whichever the list has chosen, and says
    # which, so that saving writes it to her. Under none nobody is described and there is no box.
    described = live.persona
    plain = described == personas.NONE
    # What was typed goes back in the box only when it was typed for her.
    typed_for_her = personas.key_for(typed.get("described", described)) == described
    text = (typed.get("persona_text", "") if typed_for_her else "") or speaking.character
    # The name the family call her, with her own as the placeholder: an empty box is hers.
    name = typed.get("persona_name", live.persona_name)
    notes = typed.get("persona_notes", live.persona_notes)
    about = typed.get("about_family", live.about_family)
    # What has changed in her own description since the family rewrote her, if anything: their
    # rewrite remembers hers as it was then, and her folder says what it is now. One saved before
    # that was remembered cannot tell.
    rewrite = None if plain else live.persona_text.get(described)
    changes = (
        views.line_changes(rewrite.of, personas.load(described).character)
        if rewrite and rewrite.of
        else []
    )
    # What she says unasked: the family's line if they wrote one, hers as the placeholder, and
    # how the line in force reads now, each of its wordings filled in with example facts.
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
            # Under none, whether anything they wrote for a persona is waiting for her.
            kept=plain and any(key in personas.available() for key in live.persona_text),
            about=about,
            line_groups=[
                {
                    "title": title,
                    "lines": shown,
                    # Folded until one of its lines is the family's own, or was just typed.
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
    """Who she is and who the family are.

    The description box is a rewrite of the persona it described when the page was drawn, never
    of one chosen in the same save, and with no box sent (under none) every rewrite stays as it
    was. Her own text, as written or with her name filled in, is no rewrite at all. Likewise the
    name box: one not sent leaves their name for her as it was, and her own name is none of
    theirs. And the box of their notes on how she talks: one not sent leaves them as they were."""
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
        # What the environment already says is not stored over it, as on the main page.
        "persona": None if chosen == _app().base_settings.persona else chosen,
        "about_family": typed["about_family"].replace("\r\n", "\n").strip() or None,
        # Only lines that differ from hers are the family's own.
        "voice_lines": {
            name: line for name, line in written.items() if voice.wordings(line) != hers[name]
        }
        or None,
    }
    if "persona_name" in request.form:
        # An empty box, or her own name, is no name of theirs. That is stored only over a name
        # the environment gives her, which would otherwise stay whatever the box said.
        called = typed["persona_name"].strip()
        if called == personas.load(live.persona).name:
            called = ""
        values["persona_name"] = None if called == _app().base_settings.persona_name else called
    if "persona_notes" in request.form:
        # Likewise an empty box is stored only over notes the environment gives.
        notes = typed["persona_notes"].replace("\r\n", "\n").strip()
        values["persona_notes"] = None if notes == _app().base_settings.persona_notes else notes
    if "persona_text" in request.form:
        # A form drawn before the box said whom it described was drawn for the persona in force.
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
    """What a line's box says: one wording to a row, blank rows no part of it, kept as a string
    when there is one and a list when there are several. A box left as it was drawn keeps the
    line as it is stored, so one saved as a string before a line could have several wordings
    stays one wording, line breaks and all."""
    rows = _rows(box)
    if not rows:
        return ""
    if stored is not None and rows == _rows(voice.boxed(stored)):
        return stored
    return rows[0] if len(rows) == 1 else rows


def _rows(box: str) -> list[str]:
    return [row.strip() for row in box.splitlines() if row.strip()]


def _rewrites(settings: Settings) -> dict[str, dict[str, str]]:
    """The family's rewrites of her, by persona, as they are stored."""
    return {key: rewrite.model_dump() for key, rewrite in settings.persona_text.items()}


def _rewritten(live: Settings, described: str, text: str) -> dict[str, dict[str, str]]:
    """The family's rewrites with the described persona's as her box now says.

    A blank box, or her own character as written or with her name filled in, is no rewrite. A
    text unchanged from theirs keeps theirs as it is; a new one is written against her own
    character now, so the page can tell later when hers has changed. Only a persona there is a
    folder for can have been described."""
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
    """What to store for these rewrites: nothing when they are what the environment says."""
    return None if rewrites == _rewrites(_app().base_settings) else rewrites


def _choices(live: Settings) -> list[dict[str, Any]]:
    """Each persona there is a folder for, the default first, as she would be if chosen: her
    label, with the name the family call her in it, and roughly what she would add to every
    message, their rewrite of her and their notes included."""
    choices = []
    for key in sorted(personas.available(), key=lambda key: key != personas.DEFAULT):
        her = personas.active(live.model_copy(update={"persona": key}))
        tokens = len(her.prompt) // CHARS_PER_TOKEN
        choices.append({"key": key, "label": her.listed_as, "tokens": tokens})
    return choices


@bp.post("/settings/sign-out-everyone")
def sign_out_everyone() -> Response | tuple[str, int]:
    """End every session, on every device, this one included, after the password this browser
    signed in with is typed again.

    For a phone that went missing or a password that was shared too widely: every login cookie
    and every known-browser mark was signed with the key this replaces.
    """
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


@bp.post("/settings/google/start")
def google_start() -> tuple[str, int]:
    """Take the OAuth client pasted in, and give back Google's consent link."""
    back = auth.setup_return(request.form.get("then"))
    if (complaint := auth.refused()) is not None:
        return _google_answer(back, error=complaint)
    try:
        config = google.client_config(request.form.get("client", ""))
        url, flow, state = google.begin_consent(config)
    except google.GoogleSetupError as exc:
        return _google_answer(back, error=str(exc))
    key = secrets.token_urlsafe(16)
    consents = _consents()
    for old in [k for k, v in consents.items() if time.monotonic() - v["started"] > 3600]:
        consents.pop(old, None)
    consents[key] = {"flow": flow, "state": state, "url": url, "started": time.monotonic()}
    session[GOOGLE_KEY] = key
    return _google_answer(
        back, said="Open the link below, allow access, then paste where it sends you."
    )


@bp.post("/settings/google/finish")
def google_finish() -> tuple[str, int]:
    """Exchange the pasted address for a token, save it, and offer the calendars it can see."""
    app = _app()
    back = auth.setup_return(request.form.get("then"))
    if (complaint := auth.refused()) is not None:
        return _google_answer(back, error=complaint)
    pending = _pending()
    if pending is None:
        return _google_answer(back, error=GOOGLE_EXPIRED)
    try:
        creds = google.finish_consent(
            pending["flow"],
            request.form.get("pasted", ""),
            Path(app.settings.google_token_path),
            state=pending["state"],
        )
        pending["calendars"] = google.list_calendars(creds)
    except google.GoogleSetupError as exc:
        return _google_answer(back, error=str(exc))
    except Exception as exc:  # the token is saved; only listing the calendars failed
        log.warning("connected to Google but could not list the calendars: %s", exc)
        pending["calendars"] = []
    app.forget_calendar()
    log.info("Google Calendar connected from the page by %s", auth.client_address())
    return _google_answer(back, said="Connected to Google. Choose the family calendar.")


@bp.post("/settings/google/calendar")
def google_calendar_choice() -> Response | tuple[str, int]:
    """The calendar the bot keeps plans on, chosen from the ones the connection can see."""
    back = auth.setup_return(request.form.get("then"))
    here = _section(request.form.get("section"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, here, error=complaint, otherwise="connections")
    pending = _pending()
    offered = {row["id"]: row for row in (pending or {}).get("calendars") or []}
    chosen = request.form.get("calendar_id", "")
    if chosen not in offered:
        return _answer(back, here, error=GOOGLE_EXPIRED, otherwise="connections")
    _save({"google_calendar_id": chosen})
    _consents().pop(session.pop(GOOGLE_KEY, ""), None)
    return _answer(back, here, said=CALENDAR_SET.format(name=offered[chosen]["summary"] or chosen))


def _google_answer(
    back: str | None, *, said: str | None = None, error: str | None = None
) -> Response | tuple[str, int]:
    """The consent steps draw the Connections page with the next step on it; setup draws its own
    instead."""
    if back is not None:
        return auth.back_to_setup(back, said=said, problem=error)
    return page("connections", said=said, error=error, status=400 if error else 200)


def _problems_said(problems: dict[str, str]) -> str:
    """Every complaint about a form, in one line, named by the box it is about."""
    named = [
        f"{fields.BY_KEY[key].label}: {why}" if key in fields.BY_KEY else why
        for key, why in problems.items()
    ]
    return "Nothing was saved. " + " ".join(named)


def _key_order(provider: str) -> list[str]:
    """The key of the company answering now first, as that is the one a new install needs."""
    first = f"{provider}_api_key"
    return sorted(SECRETS, key=lambda name: (name != first, name == "telegram_bot_token"))


def _said(changed: list[str], *, keys: bool = False) -> str:
    """What moved, in the words the page uses for it."""
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
