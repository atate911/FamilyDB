"""The settings page: the only part of the web surface that writes.

It writes to one place and one place only, `app_settings`, through `store.settings`. Nothing
here can reach an idea, a plan or a message. Every change is logged, and a key's value is never
what gets logged: only that it was replaced.

The Personality page (/settings/personality) writes the three `PROFILE` settings: which persona,
her description as the family rewrote it, and the family's words about themselves.

Two forms on the main page, because they are not the same kind of thing. The behaviour form
carries every box on the page each time it is sent, so an emptied box means "go back to what
the environment says". The keys form carries only what someone typed: an empty key box means
"leave that one alone", since a password box is empty every time the page is drawn.
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

from familydb import personas
from familydb.agent import providers
from familydb.app import App
from familydb.config import Settings, apply_overrides
from familydb.integrations import google_calendar as google
from familydb.store import settings as settings_store
from familydb.store.db import transaction
from familydb.store.settings import SECRETS
from familydb.web import auth, fields, keys, views
from familydb.web import status as status_page

log = logging.getLogger(__name__)

bp = Blueprint("settings", __name__)

HISTORY_LIMIT = 12
NOTICE = "settings"
SAVED = "Saved. {what}"
NOTHING_CHANGED = "Nothing was different, so nothing was written."
NEEDS_PASSWORD = "Type the family password to see a key."
WRONG_PASSWORD = "That password is not right."
LOCKED_OUT = "Too many tries. Wait a quarter of an hour."
KEY_HAS_SPACES = "A key has no spaces in it. Check what was pasted."
UNKNOWN_KEY = "There is no such key."
UNKNOWN_MODEL = "{company} says it has no model called {name}. Check the spelling."
# Which company each model box belongs to, so a new name can be checked with that company.
MODEL_BOXES = {
    "openai_model": ("openai", "OpenAI"),
    "openai_worker_model": ("openai", "OpenAI"),
    "anthropic_model": ("anthropic", "Anthropic"),
    "worker_model": ("anthropic", "Anthropic"),
    "gemini_model": ("gemini", "Google"),
    "gemini_worker_model": ("gemini", "Google"),
}
KEY_LABELS = {
    "anthropic_api_key": "Claude (Anthropic)",
    "openai_api_key": "OpenAI",
    "gemini_api_key": "Google Gemini",
    "telegram_bot_token": "Telegram bot token",
}


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _stored() -> dict[str, Any]:
    with closing(_app().connect()) as conn:
        return settings_store.overrides(conn)


def _save(values: dict[str, Any]) -> list[str]:
    """Write the changes and log them. Returns the keys that actually moved."""
    app = _app()
    source = f"web {auth.client_address()}"
    with closing(app.connect()) as conn, transaction(conn):
        changed = settings_store.set_many(conn, values, source=source)
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


def google_panel(live: Any) -> dict[str, Any]:
    pending = _pending()
    return {
        "connected": Path(live.google_token_path).exists(),
        "calendar": live.google_calendar_id,
        "consent_url": pending["url"] if pending and "calendars" not in pending else None,
        "calendars": pending.get("calendars") if pending else None,
    }


def page(
    *,
    problems: dict[str, str] | None = None,
    said: str | None = None,
    error: str | None = None,
    revealed: tuple[str, str] | None = None,
    typed: dict[str, str] | None = None,
    status: int = 200,
) -> tuple[str, int]:
    """Draw the page. Everything it shows is read fresh, so a save is visible at once."""
    app = _app()
    live = app.settings
    base = app.base_settings
    if said is None:
        # What the last save said, handed over by the redirect that followed it. Named,
        # because the edit forms flash too and their notices belong on their own pages.
        told = get_flashed_messages(category_filter=[NOTICE])
        said = told[0] if told else None
    with closing(app.connect()) as conn:
        overrides = settings_store.overrides(conn)
        history = settings_store.history(conn, limit=HISTORY_LIMIT)
        chats = status_page.digest_chats(conn, live.tzinfo)
    groups = [
        {
            "title": title,
            "note": note,
            "boxes": [
                {
                    "field": one,
                    "value": (typed or {}).get(one.key, fields.shown(one, overrides.get(one.key))),
                    "placeholder": fields.placeholder(one, getattr(base, one.key)),
                    "problem": (problems or {}).get(one.key),
                    "stored": one.key in overrides,
                    "offers": chats
                    if one.key == "digest_chat_id"
                    else [(name, "") for name in one.suggested],
                }
                for one in group
            ],
        }
        for title, note, group in fields.GROUPS
    ]
    keys = [
        {
            "key": name,
            "label": KEY_LABELS[name],
            "set": bool(getattr(live, name)),
            "stored": name in overrides,
            "problem": (problems or {}).get(name),
            "revealed": revealed[1] if revealed and revealed[0] == name else None,
        }
        for name in _key_order(live.provider)
    ]
    return (
        render_template(
            "settings.html",
            groups=groups,
            keys=keys,
            history=[views.change_row(line, app.settings.tzinfo) for line in history],
            said=said,
            error=error,
            needs_password=auth.password_in_use(live),
            google=google_panel(live),
        ),
        status,
    )


@bp.get("/settings")
def show() -> tuple[str, int]:
    return page()


@bp.post("/settings")
def save() -> Response | tuple[str, int]:
    """Store the behaviour settings, or say which box is wrong and keep what was typed."""
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, status=400)
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
        return page(problems=problems, error="Nothing was saved.", typed=typed, status=400)
    located, where = locate_home(values, stored)
    flash(" ".join(part for part in (_said(_save({**values, **located})), where) if part), NOTICE)
    return redirect(url_for("settings.show"))


@bp.post("/settings/keys")
def save_keys() -> Response | tuple[str, int]:
    """Store or remove an API key. A key's value never reaches a log or the change history."""
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, status=400)
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
        return page(problems=problems, error="Nothing was saved.", status=400)
    flash(_said(_save(values), keys=True), NOTICE)
    return redirect(url_for("settings.show"))


@bp.post("/settings/reveal")
def reveal() -> tuple[str, int]:
    """Show one key, once, after the family password is typed again.

    Signing in weeks ago is not enough: a page left open on a phone should not hand a key to
    whoever picks it up. Guessing here is counted and locked out the same way signing in is.
    """
    app = _app()
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, status=400)
    name = request.form.get("key", "")
    if name not in SECRETS:
        return page(error=UNKNOWN_KEY, status=400)
    who = auth.client_address()
    attempt = f"{who} reveal"
    lockout = current_app.config["FAMILYDB_LOCKOUT"]
    now = app.clock.now()
    if lockout.locked(attempt, now):
        return page(error=LOCKED_OUT, status=429)
    if auth.password_in_use(app.settings):
        given = request.form.get("password", "")
        if not given:
            return page(error=NEEDS_PASSWORD, status=400)
        if not auth.password_matches(app.settings, given):
            lockout.failed(attempt, now)  # counted apart from signing in, and logged there
            return page(error=WRONG_PASSWORD, status=401)
        lockout.passed(attempt)
    value = getattr(app.settings, name) or ""
    if not value:
        return page(error=f"There is no {KEY_LABELS[name]} key to show.", status=404)
    log.warning("%s was shown to %s", name, who)
    return page(revealed=(name, value), said=f"{KEY_LABELS[name]} is shown below, this once.")


KEY_PINNED = (
    "The signing key is set in WEB_SECRET_KEY, so only changing it there, and restarting, signs "
    "everyone out."
)


# -- who she is, and who the family are ---------------------------------------------------------

RESTORED = "Restored her original description."
PROFILE_LABELS = {
    "persona": "personality",
    "persona_text": "her description",
    "about_family": "about the family",
}
# A rough count, to say what a description adds to every message; the real one is on /status.
CHARS_PER_TOKEN = 4


def personality_page(
    *, error: str | None = None, typed: dict[str, str] | None = None, status: int = 200
) -> tuple[str, int]:
    live = _app().settings
    told = get_flashed_messages(category_filter=[NOTICE])
    chosen = (typed or {}).get("persona", live.persona)
    text = (typed or {}).get("persona_text") or personas.text_for(live) or personas.load(chosen)
    about = (typed or {}).get("about_family", live.about_family)
    return (
        render_template(
            "personality.html",
            said=told[0] if told else None,
            error=error,
            chosen=chosen,
            choices=personas.available(),
            text=text,
            rewritten=bool(live.persona_text.strip()),
            about=about,
            tokens=(len(personas.text_for(live)) + len(live.about_family)) // CHARS_PER_TOKEN,
            limits={
                name: Settings.model_fields[name].metadata[0].max_length
                for name in ("persona_text", "about_family")
            },
        ),
        status,
    )


@bp.get("/settings/personality")
def personality() -> tuple[str, int]:
    return personality_page()


@bp.post("/settings/personality")
def save_personality() -> Response | tuple[str, int]:
    """Who she is and who the family are. Her text the same as the file's is no rewrite at all."""
    if (complaint := auth.refused()) is not None:
        return personality_page(error=complaint, status=400)
    typed = {
        name: request.form.get(name, "") for name in ("persona", "persona_text", "about_family")
    }
    chosen = typed["persona"].strip()
    text = typed["persona_text"].replace("\r\n", "\n").strip()
    original = personas.load(chosen) if chosen in personas.available() else ""
    values: dict[str, Any] = {
        # What the environment already says is not stored over it, as on the main page.
        "persona": None if chosen == _app().base_settings.persona else chosen,
        "persona_text": text if original and text and text != original else None,
        "about_family": typed["about_family"].replace("\r\n", "\n").strip() or None,
    }
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
    if (complaint := auth.refused()) is not None:
        return personality_page(error=complaint, status=400)
    _save({"persona_text": None})
    flash(RESTORED, NOTICE)
    return redirect(url_for("settings.personality"))


@bp.post("/settings/sign-out-everyone")
def sign_out_everyone() -> Response | tuple[str, int]:
    """End every session, on every device, this one included, after the password is typed again.

    For a phone that went missing or a password that was shared too widely: every login cookie
    and every known-browser mark was signed with the key this replaces.
    """
    app = _app()
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, status=400)
    who = auth.client_address()
    attempt = f"{who} reveal"
    lockout = current_app.config["FAMILYDB_LOCKOUT"]
    now = app.clock.now()
    if lockout.locked(attempt, now):
        return page(error=LOCKED_OUT, status=429)
    if auth.password_in_use(app.settings):
        if not auth.password_matches(app.settings, request.form.get("password", "")):
            lockout.failed(attempt, now)
            return page(error=WRONG_PASSWORD, status=401)
        lockout.passed(attempt)
    fresh = keys.rotate(app.settings)
    if fresh is None:
        return page(error=KEY_PINNED, status=409)
    current_app.secret_key = fresh
    session.clear()
    log.warning("%s signed everyone out", who)
    return redirect(url_for("auth.login"))


@bp.post("/settings/google/start")
def google_start() -> tuple[str, int]:
    """Take the OAuth client pasted in, and give back Google's consent link."""
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, status=400)
    try:
        config = google.client_config(request.form.get("client", ""))
        url, flow, state = google.begin_consent(config)
    except google.GoogleSetupError as exc:
        return page(error=str(exc), status=400)
    key = secrets.token_urlsafe(16)
    consents = _consents()
    for old in [k for k, v in consents.items() if time.monotonic() - v["started"] > 3600]:
        consents.pop(old, None)
    consents[key] = {"flow": flow, "state": state, "url": url, "started": time.monotonic()}
    session[GOOGLE_KEY] = key
    return page(said="Open the link below, allow access, then paste where it sends you.")


@bp.post("/settings/google/finish")
def google_finish() -> tuple[str, int]:
    """Exchange the pasted address for a token, save it, and offer the calendars it can see."""
    app = _app()
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, status=400)
    pending = _pending()
    if pending is None:
        return page(error=GOOGLE_EXPIRED, status=400)
    try:
        creds = google.finish_consent(
            pending["flow"],
            request.form.get("pasted", ""),
            Path(app.settings.google_token_path),
            state=pending["state"],
        )
        pending["calendars"] = google.list_calendars(creds)
    except google.GoogleSetupError as exc:
        return page(error=str(exc), status=400)
    except Exception as exc:  # the token is saved; only listing the calendars failed
        log.warning("connected to Google but could not list the calendars: %s", exc)
        pending["calendars"] = []
    app.forget_calendar()
    log.info("Google Calendar connected from the page by %s", auth.client_address())
    return page(said="Connected to Google. Choose the family calendar.")


@bp.post("/settings/google/calendar")
def google_calendar_choice() -> Response | tuple[str, int]:
    """The calendar the bot keeps plans on, chosen from the ones the connection can see."""
    if (complaint := auth.refused()) is not None:
        return page(error=complaint, status=400)
    pending = _pending()
    offered = {row["id"]: row for row in (pending or {}).get("calendars") or []}
    chosen = request.form.get("calendar_id", "")
    if chosen not in offered:
        return page(error=GOOGLE_EXPIRED, status=400)
    _save({"google_calendar_id": chosen})
    _consents().pop(session.pop(GOOGLE_KEY, ""), None)
    flash(CALENDAR_SET.format(name=offered[chosen]["summary"] or chosen), NOTICE)
    return redirect(url_for("settings.show"))


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
