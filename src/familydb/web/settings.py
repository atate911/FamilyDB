"""The settings page: the only part of the web surface that writes.

It writes to one place and one place only, `app_settings`, through `store.settings`. Nothing
here can reach an idea, a plan or a message. Every change is logged, and a key's value is never
what gets logged: only that it was replaced.

The Personality page (/settings/personality) writes the four `PROFILE` settings: which persona,
her description as the family rewrote it, her lines likewise, and the family's words about
themselves. Her description is shown and kept as written, with {name} where her name goes.

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

from familydb import passwords, personas, voice
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


def _answer(
    back: str | None, *, said: str | None = None, error: str | None = None, status: int = 400
) -> Response | tuple[str, int]:
    """Where a form's result goes: back to the setup page that sent it, or this page as before."""
    if back is not None:
        return auth.back_to_setup(back, said=said, problem=error)
    if error is not None:
        return page(error=error, status=status)
    flash(said or NOTHING_CHANGED, NOTICE)
    return redirect(url_for("settings.show"))


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
            password={
                "chosen": auth.password_chosen(live),
                "needs_current": current_password_needed(live),
                "least": auth.MIN_PASSWORD,
            },
        ),
        status,
    )


@bp.get("/settings")
def show() -> tuple[str, int]:
    return page()


@bp.post("/settings")
def save() -> Response | tuple[str, int]:
    """Store the behaviour settings, or say which box is wrong and keep what was typed."""
    back = auth.setup_return(request.form.get("then"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, error=complaint)
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
            return _answer(back, error=_problems_said(problems))
        return page(problems=problems, error="Nothing was saved.", typed=typed, status=400)
    located, where = locate_home(values, stored)
    said = " ".join(part for part in (_said(_save({**values, **located})), where) if part)
    return _answer(back, said=said)


@bp.post("/settings/keys")
def save_keys() -> Response | tuple[str, int]:
    """Store or remove an API key. A key's value never reaches a log or the change history."""
    back = auth.setup_return(request.form.get("then"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, error=complaint)
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
            return _answer(back, error=" ".join(problems.values()))
        return page(problems=problems, error="Nothing was saved.", status=400)
    return _answer(back, said=_said(_save(values), keys=True))


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


# -- which company answers, and its key --------------------------------------------------------

COMPANIES = {"openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Google"}
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
        "another under Who answers on the Settings page."
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
    if (complaint := auth.refused()) is not None:
        return _answer(back, error=complaint)
    company = request.form.get("provider", "")
    if company not in providers.NAMES:
        return _answer(back, error=UNKNOWN_COMPANY)
    name = f"{company}_api_key"
    given = request.form.get("key", "").strip()
    values: dict[str, Any] = {}
    if given:
        if any(character.isspace() for character in given):
            return _answer(back, error=KEY_HAS_SPACES)
        if len(given) > fields.MAX_LENGTH:
            return _answer(back, error=fields.TOO_LONG)
        values[name] = given
    elif not getattr(app.settings, name):
        return _answer(back, error=NO_KEY_GIVEN)
    # The environment's own choice is not stored over it, as on the rest of the page.
    values["provider"] = None if company == app.base_settings.provider else company
    stored = _stored()
    try:
        candidate = apply_overrides(
            app.base_settings,
            {key: value for key, value in {**stored, **values}.items() if value is not None},
        )
    except ValidationError as exc:
        return _answer(back, error=" ".join(problems_from(exc).values()))
    chosen = providers.build(company, candidate)
    verdict = chosen.check_key()
    label = COMPANIES[company]
    if verdict == "refused":
        return _answer(back, error=KEY_REFUSED.format(company=label))
    _save(values)
    said = KEY_VERDICTS.get(verdict, KEY_VERDICTS["unchecked"])
    her = personas.active(candidate).name
    return _answer(back, said=said.format(company=label, model=chosen.model_for("chat"), name=her))


# -- the family password ----------------------------------------------------------------------

PASSWORD_SAVED = "Saved. That is the family password now: every other browser will ask for it."
PASSWORD_TWICE = "The two new passwords were not the same. Type them again."
PASSWORD_SHORT = (
    "That one is {length} characters. It needs at least {least}: a short sentence is easy to "
    "remember and long enough."
)
PASSWORD_LONG = "That is longer than a password needs to be."
PASSWORD_CURRENT = "Type the password you use now, to show it is you."
MAX_PASSWORD = 200
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
    if (complaint := auth.refused()) is not None:
        return _answer(back, error=complaint)
    new, again = request.form.get("new", ""), request.form.get("again", "")
    if new != again:
        return _answer(back, error=PASSWORD_TWICE)
    if len(new) < auth.MIN_PASSWORD:
        return _answer(back, error=PASSWORD_SHORT.format(length=len(new), least=auth.MIN_PASSWORD))
    if len(new) > MAX_PASSWORD:
        return _answer(back, error=PASSWORD_LONG)
    live = app.settings
    if current_password_needed(live):
        who = auth.client_address()
        attempt = f"{who} password"  # counted apart from signing in, like showing a key
        lockout = current_app.config["FAMILYDB_LOCKOUT"]
        now = app.clock.now()
        if lockout.locked(attempt, now):
            return _answer(back, error=LOCKED_OUT, status=429)
        given = request.form.get("current", "")
        if not auth.password_matches(live, given):
            lockout.failed(attempt, now)
            return _answer(back, error=WRONG_PASSWORD if given else PASSWORD_CURRENT, status=401)
        lockout.passed(attempt)
    _save({"web_password_hash": passwords.hash_password(new)})
    log.warning("the family password was changed from the page by %s", auth.client_address())
    # Every session was marked with the old password and so ends; this one is marked again.
    session[auth.SESSION_KEY] = True
    session[auth.PASSWORD_KEY] = auth.password_mark(app.settings)
    response = _answer(back, said=PASSWORD_SAVED)
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
    "persona_text": "her description",
    "about_family": "about the family",
}
# A rough count, to say what a description adds to every message; the real one is on /status.
CHARS_PER_TOKEN = 4


def personality_page(
    *, error: str | None = None, typed: dict[str, str] | None = None, status: int = 200
) -> tuple[str, int]:
    live = _app().settings
    speaking = personas.active(live)
    told = get_flashed_messages(category_filter=[NOTICE])
    chosen = personas.key_for((typed or {}).get("persona", live.persona))
    # A persona nobody has a folder for (a hand-made form) is shown as nothing, and refused on save.
    original = personas.load(chosen).character if chosen in personas.available() else ""
    text = (typed or {}).get("persona_text") or speaking.character or original
    about = (typed or {}).get("about_family", live.about_family)
    # What she says unasked: the family's line if they wrote one, hers as the placeholder.
    hers = voice.wording(personas.load(live.persona))
    said_lines = [
        {
            "event": name,
            "label": event.label,
            "value": (typed or {}).get(f"line_{name}", live.voice_lines.get(name, "")),
            "placeholder": hers[name],
            "fields": ", ".join("{" + f + "}" for f in voice.usable(name)),
        }
        for name, event in voice.EVENTS.items()
    ]
    return (
        render_template(
            "personality.html",
            said=told[0] if told else None,
            error=error,
            chosen=chosen,
            choices=[personas.load(key) for key in personas.available()],
            text=text,
            rewritten=bool(live.persona_text.strip()),
            about=about,
            said_lines=said_lines,
            plain=live.persona == personas.NONE,
            her_name=speaking.name,
            tokens=(len(speaking.prompt) + len(live.about_family)) // CHARS_PER_TOKEN,
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
    """Who she is and who the family are. Her own text, as written or with her name filled in,
    is no rewrite at all."""
    if (complaint := auth.refused()) is not None:
        return personality_page(error=complaint, status=400)
    typed = {
        name: request.form.get(name, "") for name in ("persona", "persona_text", "about_family")
    }
    written = {
        name: request.form.get(f"line_{name}", "").strip()
        for name in voice.EVENTS
        if request.form.get(f"line_{name}", "").strip()
    }
    typed.update({f"line_{name}": line for name, line in written.items()})
    if wrong := voice.problems(written):
        what = "; ".join(f"{voice.EVENTS[n].label}: {why}" for n, why in wrong.items())
        return personality_page(error=f"Nothing was saved. {what}.", typed=typed, status=400)
    chosen = personas.key_for(typed["persona"])
    text = typed["persona_text"].replace("\r\n", "\n").strip()
    shipped = personas.load(chosen) if chosen in personas.available() else None
    hers = voice.wording(personas.load(_app().settings.persona))
    values: dict[str, Any] = {
        # What the environment already says is not stored over it, as on the main page.
        "persona": None if chosen == _app().base_settings.persona else chosen,
        "persona_text": (
            text if shipped and text and text not in (shipped.character, shipped.prompt) else None
        ),
        "about_family": typed["about_family"].replace("\r\n", "\n").strip() or None,
        # Only lines that differ from hers are the family's own.
        "voice_lines": {name: line for name, line in written.items() if line != hers[name]} or None,
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
    if (complaint := auth.refused()) is not None:
        return _answer(back, error=complaint)
    pending = _pending()
    offered = {row["id"]: row for row in (pending or {}).get("calendars") or []}
    chosen = request.form.get("calendar_id", "")
    if chosen not in offered:
        return _answer(back, error=GOOGLE_EXPIRED)
    _save({"google_calendar_id": chosen})
    _consents().pop(session.pop(GOOGLE_KEY, ""), None)
    return _answer(back, said=CALENDAR_SET.format(name=offered[chosen]["summary"] or chosen))


def _google_answer(
    back: str | None, *, said: str | None = None, error: str | None = None
) -> Response | tuple[str, int]:
    """The consent steps draw this page with the next step on it; setup draws its own instead."""
    if back is not None:
        return auth.back_to_setup(back, said=said, problem=error)
    return page(said=said, error=error, status=400 if error else 200)


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
