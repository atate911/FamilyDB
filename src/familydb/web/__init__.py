"""The web page: a Flask application over an `App`. Which modules may write, and through what
door, is in CLAUDE.md and held by `tests/test_web.py`."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from typing import Any

from flask import Flask, render_template, request
from werkzeug.security import safe_join

from familydb import __version__, personas
from familydb.app import App
from familydb.availability import web_is_public, web_password_required
from familydb.channels.web import WebChat
from familydb.config import Settings
from familydb.errors import ConfigError
from familydb.web import (
    activity,
    auth,
    chat,
    edits,
    family,
    fields,
    links,
    look,
    looks,
    once,
    routes,
    setup,
    shell,
    views,
)
from familydb.web import settings as settings_page
from familydb.web import status as status_page
from familydb.web.auth import MIN_PASSWORD
from familydb.web.keys import session_secret

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 64 * 1024  # every form but one: nothing else takes an upload
# The chat's box, after sign-in, may carry a photo (chat.send); the server reads no more than that
# of any request, and Flask still refuses anything over MAX_BODY_BYTES everywhere else.
MAX_UPLOAD_BYTES = chat.MAX_UPLOAD_BYTES
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)
HSTS = "max-age=31536000"
# Static files carry a content fingerprint (`style.css?v=…`) and are kept a year. Fonts are named
# by the stylesheet, where no fingerprint reaches, and the preload must name them the same way or
# they are fetched twice, so they go unmarked and are kept a day.
STATIC_FOREVER = "public, max-age=31536000, immutable"
STATIC_FONTS = "public, max-age=86400"
FONTS = "fonts/"
REFERRER_POLICY = "same-origin"
NO_PASSWORD = (
    "WEB_HOST is {host}, so the page would be reachable from other machines, but WEB_PASSWORD is "
    "empty. Set a password, bind to 127.0.0.1, or set WEB_ALLOW_NO_PASSWORD=true if this is a "
    "home network you trust."
)
NO_PASSWORD_BEHIND_PROXY = (
    "WEB_TRUST_PROXY is on, so a proxy is bringing the internet to this page, but WEB_PASSWORD is "
    f"empty. Set one of at least {MIN_PASSWORD} characters."
)
SHORT_PASSWORD = (
    "WEB_PASSWORD is {length} characters. A page reachable from other machines needs at least "
    f"{MIN_PASSWORD}, because a password is all that guards it and there is no second factor."
)
NO_PROXY_TRUSTED = (
    "The page is on %s with WEB_TRUST_PROXY off. If a reverse proxy is in front, set it to true: "
    "otherwise every visitor shares one lockout, so five wrong guesses shut the family out, and "
    "the login cookie is not marked Secure."
)


def check_configuration(settings: Settings, *, own_passwords: bool = False) -> None:
    """Refuse to serve a page the network could walk into. Raises ConfigError. With
    `own_passwords` there is no need for a shared password."""
    if not web_password_required(settings) or own_passwords:
        return
    if settings.web_password_hash:
        return  # chosen on the page, whose form would not take one that was too short
    if not settings.web_password:
        if settings.web_trust_proxy:
            raise ConfigError(NO_PASSWORD_BEHIND_PROXY)
        raise ConfigError(NO_PASSWORD.format(host=settings.web_host))
    if len(settings.web_password) < MIN_PASSWORD:
        raise ConfigError(SHORT_PASSWORD.format(length=len(settings.web_password)))


def security_headers(response: Any) -> Any:
    if request.endpoint != "static":
        # Otherwise the back button can redisplay the family's pages after signing out.
        response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    # Not "no-referrer": a browser then posts `Origin: null`, which `auth.origin_ok` refuses, so
    # nobody could sign in (the test client sends no Origin, so only a real browser shows it).
    response.headers.setdefault("Referrer-Policy", REFERRER_POLICY)
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", HSTS)
    return response


def fingerprints(folder: str | Path) -> Callable[[str], str | None]:
    """A short hash of each static file, read once. None for a file that is not there."""
    known: dict[str, str | None] = {}

    def fingerprint(filename: str) -> str | None:
        if filename not in known:
            path = safe_join(str(folder), filename)
            try:
                data = Path(path).read_bytes() if path else None
            except OSError:
                data = None
            known[filename] = hashlib.sha256(data).hexdigest()[:12] if data is not None else None
        return known[filename]

    return fingerprint


def _static_caching(web: Flask) -> None:
    """Name each static file with its fingerprint, and let a browser keep what it names."""
    fingerprint = fingerprints(web.static_folder or "")

    @web.url_defaults
    def named_with_fingerprint(endpoint: str, values: dict[str, Any]) -> None:
        filename = values.get("filename", "")
        if endpoint != "static" or "v" in values or filename.startswith(FONTS):
            return
        stamp = fingerprint(filename)
        if stamp:
            values["v"] = stamp

    @web.after_request
    def kept(response: Any) -> Any:
        # Only a file that was found: a name somebody made up is never read, let alone kept.
        if request.endpoint != "static" or response.status_code not in (200, 304):
            return response
        filename = (request.view_args or {}).get("filename", "")
        if filename.startswith(FONTS):
            response.headers["Cache-Control"] = STATIC_FONTS
        elif request.args.get("v") and request.args.get("v") == fingerprint(filename):
            response.headers["Cache-Control"] = STATIC_FOREVER
        return response


def create_app(app: App, *, api: Any = None) -> Flask:
    """A Flask application over this App. `api` stands in for the chat page's model, for tests."""
    app.refresh()  # start from the settings in force, not only from what the environment said
    settings = app.settings
    try:
        with closing(app.connect()) as conn:
            personal = auth.own_passwords(conn)
    except sqlite3.Error as exc:
        # Asked as if nobody had a password of their own, which only ever asks for more.
        log.warning("could not read who signs in to the page: %s", exc)
        personal = False
    check_configuration(settings, own_passwords=personal)
    web = Flask(__name__)
    web.config.update(
        SECRET_KEY=session_secret(settings),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # A proxy is assumed to terminate TLS.
        SESSION_COOKIE_SECURE=settings.web_trust_proxy,
        PERMANENT_SESSION_LIFETIME=timedelta(days=settings.web_session_days),
        MAX_CONTENT_LENGTH=MAX_BODY_BYTES,
        FAMILYDB_APP=app,
        FAMILYDB_LOCKOUT=auth.Lockout(),
        # A turn outlives its request.
        FAMILYDB_CHAT=WebChat(app, api=api),
        FAMILYDB_ONCE=once.Once(),
    )

    web.jinja_env.globals["visitor"] = auth.visitor
    web.jinja_env.globals["csrf_token"] = auth.csrf_token
    web.jinja_env.globals["once_token"] = once.once_token
    web.jinja_env.globals["links"] = links.LINKS
    web.jinja_env.globals["settings_sections"] = fields.SECTIONS
    # The new frame's pill and counts, read only by a page built on base_kitchen.html.
    web.jinja_env.globals["shell_frame"] = lambda: shell.frame(app)

    def every_page() -> dict[str, Any]:
        her = personas.active(app.settings)
        # A kid sees nothing of how it works, its version included (roles.py `browse`).
        who = auth.visitor()
        plain = who.member is not None and not who.may("browse")
        light = None
        if who.may("manage"):
            try:
                with closing(app.connect()) as conn:
                    light = status_page.light(app, conn)
            except sqlite3.Error:
                log.debug("the status light is off: the troubles could not be read", exc_info=True)
        return {
            "site_title": app.settings.web_title,
            "footer": views.footer(__version__, plain=plain),
            "dictation": app.settings.web_dictation,
            "status_light": light,
            "status_words": views.STATUS_LIGHTS.get(light or ""),
            "assistant": her.name,
            "has_persona": her is not personas.PLAIN,
            **_look(),
        }

    web.context_processor(every_page)
    web.register_blueprint(auth.bp)
    web.register_blueprint(routes.bp)
    web.register_blueprint(activity.bp)
    web.register_blueprint(chat.bp)
    web.register_blueprint(edits.bp)
    web.register_blueprint(family.bp)
    web.register_blueprint(look.bp)
    web.register_blueprint(settings_page.bp)
    web.register_blueprint(setup.bp)
    # The gate first: nobody signed out may cost even a query.
    web.before_request(auth.require_login)
    web.before_request(_picking_up_settings(app, web))
    web.after_request(security_headers)
    _static_caching(web)
    web.register_error_handler(404, _not_found)
    if web_is_public(settings) and not (personal or auth.password_in_use(settings)):
        log.warning("serving the web page on %s with no password", settings.web_host)
    elif web_is_public(settings) and not settings.web_trust_proxy:
        log.warning(NO_PROXY_TRUSTED, settings.web_host)
    return web


# A monitor may ask healthz every few seconds, so these are not worth a query.
SETTINGS_FREE = frozenset({"web.healthz", "static"})


def _picking_up_settings(app: App, web: Flask) -> Any:
    """A before_request hook that serves each page from the settings in force. Flask keeps its own
    copy of the session lifetime, so it is handed over on every request: the form that changed it
    has already refreshed, so `refresh()` would report nothing moved."""

    def hook() -> None:
        if request.endpoint in SETTINGS_FREE:
            return
        app.refresh()
        web.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=app.settings.web_session_days)

    return hook


def _look() -> dict[str, Any]:
    """The look this browser chose, as the templates want it."""
    wearing, mode = looks.parse(request.cookies.get(looks.COOKIE))
    return {
        "look": wearing,
        "look_mode": mode,
        "look_scheme": looks.scheme(wearing, mode),
        "look_colours": looks.theme_colours(wearing, mode),
    }


def _not_found(_error: Any) -> tuple[str, int]:
    return render_template("404.html"), 404
