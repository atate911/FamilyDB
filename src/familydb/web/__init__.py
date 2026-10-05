"""The web page: the whole bot in a browser.

`create_app` builds a Flask application around an existing `App`, so the page works on the same
database and settings as the bot itself. Most of it reads — the ideas list, one idea, the
restaurants, the plans, what is connected and what it has cost. Four parts write, each through
one door: `chat.py` hands a message to the pipeline, `edits.py` changes an idea, an outcome, a
plan, a task or a memory through the same tools the model calls, `family.py` changes who is in
the family and how they sign in through `familydb.family`, and `settings.py` is the only thing
that writes `app_settings` (and two files, the session key and the Google token). Every other
module in this package reads and nothing else, bar `look.py`, whose Look page keeps which of the
page's looks this one browser wears in a cookie: it changes nothing the family's data knows.
"""

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
    views,
)
from familydb.web import settings as settings_page
from familydb.web import status as status_page
from familydb.web.auth import MIN_PASSWORD
from familydb.web.keys import session_secret

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 64 * 1024  # nothing here takes an upload
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)
HSTS = "max-age=31536000"
# What the page links to is named with a fingerprint of what is in it (`style.css?v=…`), so a
# browser keeps it for a year, and still fetches the new one the moment an upgrade changes it,
# rather than asking again about every file on every page. The fonts are named by the stylesheet,
# where no fingerprint reaches, and the page's preload has to name them the same way or the
# browser fetches them twice, so they go unmarked and are kept a day.
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
    """Refuse to serve a page the network could walk into. Raises ConfigError.

    `own_passwords` says people sign in as themselves, each with a password the page would not
    take too short, so there is no need for a shared one at all.
    """
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
    # Not "no-referrer": under that policy a browser sends `Origin: null` with every form it
    # posts, and `auth.origin_ok` rightly refuses a null origin, so nobody could sign in or send
    # a form from a real browser (the test client sends no Origin at all, so only a real browser
    # shows it). "same-origin" still sends no referrer with a link out to a restaurant's site,
    # while this site's own posts say where they came from.
    response.headers.setdefault("Referrer-Policy", REFERRER_POLICY)
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", HSTS)
    return response


def fingerprints(folder: str | Path) -> Callable[[str], str | None]:
    """A short hash of each static file's contents, read once: they change only with an upgrade,
    which restarts the page. None for a file that is not there."""
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
    """A Flask application over this App's database and settings.

    `api` stands in for the model on the chat page, which is how the tests drive a whole turn
    without a network. Left alone, every turn picks its provider from the settings in force.
    """
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
        # Behind a proxy we assume it terminates TLS, so the cookie must never cross plain HTTP.
        SESSION_COOKIE_SECURE=settings.web_trust_proxy,
        PERMANENT_SESSION_LIFETIME=timedelta(days=settings.web_session_days),
        MAX_CONTENT_LENGTH=MAX_BODY_BYTES,
        FAMILYDB_APP=app,
        FAMILYDB_LOCKOUT=auth.Lockout(),
        # A turn outlives the request that asked for it, so the thing running turns belongs to
        # the application rather than to any one view.
        FAMILYDB_CHAT=WebChat(app, api=api),
        # Where each form's first post went, so a second one goes there too (see once.py).
        FAMILYDB_ONCE=once.Once(),
    )

    # Who is asking, as the login gate found them: whether to offer signing out, whose name to
    # show, and whether the pages only an admin changes are in reach.
    web.jinja_env.globals["visitor"] = auth.visitor
    web.jinja_env.globals["csrf_token"] = auth.csrf_token
    web.jinja_env.globals["once_token"] = once.once_token
    # Every page outside FamilyDB it links to (web/links.py).
    web.jinja_env.globals["links"] = links.LINKS
    # Every page of settings, for the menu in the bar.
    web.jinja_env.globals["settings_sections"] = fields.SECTIONS

    def every_page() -> dict[str, Any]:
        # Who the family talks to, for every page that speaks of her: her name, and whether
        # there is a her at all, both from the persona in force. With no persona the bot is
        # FamilyDB and the place is "Chat".
        her = personas.active(app.settings)
        # A kid sees nothing of how it works, its version included (roles.py `browse`).
        who = auth.visitor()
        plain = who.member is not None and not who.may("browse")
        # An admin's Status tile lights up while something only an admin can fix goes on.
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
            # How this browser asked the page to look (web/looks.py): a theme, and day or night.
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
    # The gate first: somebody who is not signed in should not be able to make the page work,
    # not even for one small query.
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


# Nothing these two serve depends on a setting, and a monitor may ask for the first every few
# seconds, so neither is worth a query.
SETTINGS_FREE = frozenset({"web.healthz", "static"})


def _picking_up_settings(app: App, web: Flask) -> Any:
    """A before_request hook that serves each page from the settings in force.

    One small query per request when nothing has changed. It is registered after the login gate,
    so a request about to be turned away costs nothing. Flask keeps its own copy of the session
    lifetime, so that one is handed over again on every request: the form that changed it has
    already refreshed by the time this runs, so asking `refresh()` whether to bother would mean
    the new lifetime never arrived.
    """

    def hook() -> None:
        if request.endpoint in SETTINGS_FREE:
            return
        app.refresh()
        web.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=app.settings.web_session_days)

    return hook


def _look() -> dict[str, Any]:
    """The look this browser chose, as the templates want it. Anything the cookie says that is
    not one of ours is the default."""
    wearing, mode = looks.parse(request.cookies.get(looks.COOKIE))
    return {
        "look": wearing,
        "look_mode": mode,
        "look_scheme": looks.scheme(wearing, mode),
        "look_colours": looks.theme_colours(wearing, mode),
    }


def _not_found(_error: Any) -> tuple[str, int]:
    return render_template("404.html"), 404
