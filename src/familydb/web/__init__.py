"""The web page: the whole bot in a browser.

`create_app` builds a Flask application around an existing `App`, so the page works on the same
database and settings as the bot itself. Most of it reads — the ideas list, one idea, the
restaurants, the plans, what is connected and what it has cost. Three parts write, each through
one door: `chat.py` hands a message to the pipeline, `edits.py` changes an idea, an outcome or a
plan through the same tools the model calls, and `settings.py` is the only thing that touches
`app_settings`. Every other module in this package reads and nothing else.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from flask import Flask, render_template, request

from familydb import __version__
from familydb.app import App
from familydb.availability import web_is_public, web_password_required
from familydb.channels.web import WebChat
from familydb.config import Settings
from familydb.errors import ConfigError
from familydb.web import auth, chat, edits, family, once, routes, views
from familydb.web import settings as settings_page
from familydb.web.auth import MIN_PASSWORD
from familydb.web.keys import session_secret

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 64 * 1024  # nothing here takes an upload
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)
HSTS = "max-age=31536000"
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
    f"{MIN_PASSWORD}, because one password guards everything and there is no second factor."
)
NO_PROXY_TRUSTED = (
    "The page is on %s with WEB_TRUST_PROXY off. If a reverse proxy is in front, set it to true: "
    "otherwise every visitor shares one lockout, so five wrong guesses shut the family out, and "
    "the login cookie is not marked Secure."
)


def check_configuration(settings: Settings) -> None:
    """Refuse to serve a page the network could walk into. Raises ConfigError."""
    if not web_password_required(settings):
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
    # a form from a real browser. The test client sends no Origin at all, which is why no test
    # noticed. "same-origin" keeps the point of the old value — a link out to a restaurant's
    # site still carries no referrer — while letting this site's own posts say where they came
    # from.
    response.headers.setdefault("Referrer-Policy", REFERRER_POLICY)
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", HSTS)
    return response


def create_app(app: App, *, api: Any = None) -> Flask:
    """A Flask application over this App's database and settings.

    `api` stands in for the model on the chat page, which is how the tests drive a whole turn
    without a network. Left alone, every turn picks its provider from the settings in force.
    """
    app.refresh()  # start from the settings in force, not only from what the environment said
    settings = app.settings
    check_configuration(settings)
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

    # Read through `app` rather than closing over `settings`: a change made on the settings page
    # replaces the whole object, and these must follow it.
    web.jinja_env.globals["password_in_use"] = lambda: auth.password_in_use(app.settings)
    web.jinja_env.globals["csrf_token"] = auth.csrf_token
    web.jinja_env.globals["once_token"] = once.once_token
    web.context_processor(
        lambda: {"site_title": app.settings.web_title, "footer": views.footer(__version__)}
    )
    web.register_blueprint(auth.bp)
    web.register_blueprint(routes.bp)
    web.register_blueprint(chat.bp)
    web.register_blueprint(edits.bp)
    web.register_blueprint(family.bp)
    web.register_blueprint(settings_page.bp)
    # The gate first: somebody who is not signed in should not be able to make the page work,
    # not even for one small query.
    web.before_request(auth.require_login)
    web.before_request(_picking_up_settings(app, web))
    web.after_request(security_headers)
    web.register_error_handler(404, _not_found)
    if web_is_public(settings) and not auth.password_in_use(settings):
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


def _not_found(_error: Any) -> tuple[str, int]:
    return render_template("404.html"), 404
