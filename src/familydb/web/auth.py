"""The shared-password gate in front of the page.

One password for the whole family, kept in WEB_PASSWORD. A successful login sets a signed session
cookie; every page but the login and the health check is behind it. Failed attempts are counted
per client address and locked out for a while, so a page on the open internet is not worth
guessing at. When no password is configured and the page is only on the loopback (or the waiver
is set on purpose), there is nothing to log into and every page is open.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from familydb.app import App
from familydb.config import Settings

log = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)

SESSION_KEY = "signed_in"
CSRF_KEY = "csrf"
# A mark of the password a session was opened with. Changing WEB_PASSWORD then ends every session
# that was signed in with the old one, which is what someone changing it after a scare expects.
# It is an HMAC under the cookie signing key, not the password itself or a plain hash of it, so
# what sits in the cookie says nothing about the password to anyone holding the cookie.
PASSWORD_KEY = "pw"
# A browser or a monitor asking to read gets the login page; anything else gets a plain refusal.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
# A page on the internet can be poked from endless addresses; the table of failures must not grow
# with them. Past this many, everything not currently locked out is forgotten.
MAX_TRACKED = 4096
# Per-address counting alone cannot stop someone with many addresses, which anyone renting a
# server has. A site-wide ceiling makes guessing a shared password impractical; a family will
# never come near it.
GLOBAL_ATTEMPTS = 50
GLOBAL_WINDOW_MINUTES = 15
# Long enough for any real address, IPv6 with a zone included.
MAX_ADDRESS = 64
# Endpoints reachable without signing in. "static" covers the stylesheet on the login page.
OPEN_ENDPOINTS = frozenset({"auth.login", "auth.sign_in", "auth.logout", "web.healthz", "static"})
HOME = "/"
WRONG_PASSWORD = "That password is not right."
LOCKED_OUT = "Too many tries. Wait a quarter of an hour and try again."
BAD_ORIGIN = "That request did not come from this page."
STALE_FORM = "That form was too old to use. Here it is again."


@dataclass
class Lockout:
    """Wrong passwords per client address. In memory: a restart forgives, which is fine.

    The address is the usual identity, but anything can be counted: the settings page counts its
    reveal form separately, so a slip there never shuts the family out of the page itself.
    """

    failures: dict[str, int] = field(default_factory=dict)
    until: dict[str, datetime] = field(default_factory=dict)
    everyone: int = 0
    everyone_since: datetime | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def locked(self, who: str, now: datetime) -> bool:
        """Whether this address, or the whole site, is being kept waiting."""
        with self.lock:
            if self._everyone_locked(now):
                return True
            deadline = self.until.get(who)
            if deadline is None:
                return False
            if now >= deadline:
                self.until.pop(who, None)
                self.failures.pop(who, None)
                return False
            return True

    def _everyone_locked(self, now: datetime) -> bool:
        if self.everyone_since is None:
            return False
        if now - self.everyone_since >= timedelta(minutes=GLOBAL_WINDOW_MINUTES):
            self.everyone = 0
            self.everyone_since = None
            return False
        return self.everyone >= GLOBAL_ATTEMPTS

    def _prune(self, now: datetime) -> None:
        if len(self.failures) <= MAX_TRACKED:
            return
        live = {who for who, deadline in self.until.items() if deadline > now}
        if len(live) > MAX_TRACKED:
            # More addresses are locked out than we will track. Per-address counting is not
            # helping against whoever is doing this, so say so and start again.
            log.warning("forgetting %d web lockouts: too many addresses to track", len(live))
            live = set()
        self.failures = {who: n for who, n in self.failures.items() if who in live}
        self.until = {who: d for who, d in self.until.items() if who in live}

    def failed(self, who: str, now: datetime) -> None:
        with self.lock:
            self._prune(now)
            if self.everyone_since is None or now - self.everyone_since >= timedelta(
                minutes=GLOBAL_WINDOW_MINUTES
            ):
                self.everyone, self.everyone_since = 0, now
            self.everyone += 1
            count = self.failures.get(who, 0) + 1
            self.failures[who] = count
            if self.everyone == GLOBAL_ATTEMPTS:
                log.warning(
                    "%d wrong web passwords in %d minutes: refusing every one for a while",
                    self.everyone,
                    GLOBAL_WINDOW_MINUTES,
                )
            if count >= MAX_ATTEMPTS:
                self.until[who] = now + timedelta(minutes=LOCKOUT_MINUTES)
                log.warning("locking out %s after %d wrong passwords", who, count)
            else:
                log.warning("wrong web password from %s (%d/%d)", who, count, MAX_ATTEMPTS)

    def passed(self, who: str) -> None:
        with self.lock:
            self.failures.pop(who, None)
            self.until.pop(who, None)


def password_in_use(settings: Settings) -> bool:
    """Whether visitors have to sign in at all."""
    return bool(settings.web_password)


def password_mark(settings: Settings) -> str:
    """A short mark of the password in force, for the session to carry."""
    key = (current_app.secret_key or b"") if current_app else b""
    if isinstance(key, str):
        key = key.encode()
    password = (settings.web_password or "").encode()
    return hmac.new(key, password, hashlib.sha256).hexdigest()[:16]


def password_matches(settings: Settings, given: str) -> bool:
    expected = settings.web_password or ""
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


def client_address() -> str:
    """Who is asking. Correct behind a proxy only when WEB_TRUST_PROXY is set.

    Trimmed, because behind a proxy this is whatever arrived in a header: it is a key in the
    lockout table and it is written to the settings log, and neither wants an essay.
    """
    return (request.remote_addr or "unknown")[:MAX_ADDRESS]


def safe_next(target: str | None) -> str | None:
    """A path on this site, or None. Stops the login form redirecting anywhere else.

    Backslashes are refused outright: browsers treat "/\\elsewhere.example" the way they treat
    "//elsewhere.example", which would send someone straight off the site after signing in.
    """
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    if "\\" in target or "\r" in target or "\n" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    return target


def csrf_token() -> str:
    """This session's token for its forms, made the first time a form is drawn.

    The session cookie is SameSite=Lax and every post checks the Origin header, so this is the
    third lock on the same door. It is the one that still holds if a browser ever forgets the
    other two.
    """
    token = session.get(CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_KEY] = token
    return token


def csrf_ok(given: str | None) -> bool:
    """Whether this form carried this session's token. Encoded, because `compare_digest` refuses
    to compare strings outside ASCII and a pasted token full of accents is a wrong answer, not a
    server error."""
    expected = session.get(CSRF_KEY)
    if not expected or not given:
        return False
    return hmac.compare_digest(given.encode("utf-8", "replace"), expected.encode("utf-8"))


def origin_ok() -> bool:
    """Whether a POST came from this site.

    Browsers send Origin on every POST, so a mismatch is a cross-site attempt. A missing header
    means a non-browser client, which the session cookie's SameSite setting already covers.
    """
    origin = request.headers.get("Origin")
    if origin is None:
        return True
    return origin == f"{request.scheme}://{request.host}"


def refused() -> str | None:
    """None when a form may be acted on, else what to tell whoever sent it.

    Every form on the page goes through this: the Origin check catches a post from another site,
    and this session's token catches a browser that did not send one. A missing token is not the
    same thing as a request from somewhere else, and is not reported as one: signing out and back
    in leaves an open page holding a token nobody recognises any more, and telling that person
    their form came from another site would be a lie they cannot act on.
    """
    if not origin_ok():
        return BAD_ORIGIN
    if not csrf_ok(request.form.get("csrf")):
        return STALE_FORM
    return None


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _lockout() -> Lockout:
    return current_app.config["FAMILYDB_LOCKOUT"]


def require_login() -> Response | None:
    """Flask before_request hook: send anyone who is not signed in to the login page."""
    settings = _app().settings
    if not password_in_use(settings):
        return None
    if request.endpoint in OPEN_ENDPOINTS:
        return None
    if session.get(SESSION_KEY):
        if hmac.compare_digest(session.get(PASSWORD_KEY, ""), password_mark(settings)):
            return None
        # The password has changed since this session was opened, so it is no longer signed in.
        session.clear()
    if request.method not in SAFE_METHODS:
        return Response("sign in first", status=401, mimetype="text/plain")
    return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))


@bp.get("/login")
def login() -> Response | str:
    settings = _app().settings
    if not password_in_use(settings) or session.get(SESSION_KEY):
        return redirect(HOME)
    return render_template("login.html", error=None, next=safe_next(request.args.get("next")))


@bp.post("/login")
def sign_in() -> Response | str:
    app = _app()
    settings = app.settings
    if not password_in_use(settings):
        return redirect(HOME)
    if not origin_ok():
        return render_template("login.html", error=BAD_ORIGIN, next=None), 400

    now = app.clock.now()
    lockout = _lockout()
    who = client_address()
    if lockout.locked(who, now):
        return render_template("login.html", error=LOCKED_OUT, next=None), 429

    target = safe_next(request.form.get("next"))
    if not password_matches(settings, request.form.get("password", "")):
        lockout.failed(who, now)
        error = LOCKED_OUT if lockout.locked(who, now) else WRONG_PASSWORD
        return render_template("login.html", error=error, next=target), 401

    lockout.passed(who)
    session.clear()
    session[SESSION_KEY] = True
    session[PASSWORD_KEY] = password_mark(settings)
    session.permanent = True
    log.info("web login from %s", who)
    return redirect(target or HOME)


@bp.post("/logout")
def logout() -> Response:
    if origin_ok():
        session.clear()
    return redirect(url_for("auth.login"))
