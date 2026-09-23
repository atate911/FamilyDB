"""The settings page: the only part of the web surface that writes.

It writes to one place and one place only, `app_settings`, through `store.settings`. Nothing
here can reach an idea, a plan or a message. Every change is logged, and a key's value is never
what gets logged: only that it was replaced.

Two forms, because they are not the same kind of thing. The behaviour form carries every box on
the page each time it is sent, so an emptied box means "go back to what the environment says".
The keys form carries only what someone typed: an empty key box means "leave that one alone",
since a password box is empty every time the page is drawn.
"""

from __future__ import annotations

import logging
from contextlib import closing
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

from familydb.agent import providers
from familydb.app import App
from familydb.config import Settings, apply_overrides
from familydb.store import settings as settings_store
from familydb.store.db import transaction
from familydb.store.settings import SECRETS
from familydb.web import auth, fields, keys, views

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


def problems_from(exc: ValidationError) -> dict[str, str]:
    """Pydantic's complaints, one sentence per box, in the words it used."""
    found: dict[str, str] = {}
    for error in exc.errors(include_url=False):
        key = str(error["loc"][0]) if error["loc"] else ""
        found.setdefault(key, error["msg"])
    return found


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
        for name in SECRETS
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
    flash(_said(_save(values)), NOTICE)
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


def _said(changed: list[str], *, keys: bool = False) -> str:
    if not changed:
        return NOTHING_CHANGED
    if keys:
        labels = ", ".join(KEY_LABELS.get(name, name) for name in changed)
        return SAVED.format(what=f"Changed: {labels}.")
    return SAVED.format(what=f"Changed: {', '.join(changed)}.")
