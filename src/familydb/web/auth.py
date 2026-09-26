"""The gate in front of the page: each person signs in as themselves.

Each admin and member may have their own password; familydb/family.py holds the rules and
store/logins.py the hashes. Signing in with a name and that password opens a session that knows
who it is: the chat speaks as them, the settings log says who changed what, and each part of the
page is reached only by a role with the permission it needs (familydb/roles.py, and `NEEDS`
below): Settings, the setup pages and the Family list by an admin alone. Somebody signed in with a
starting password an admin made up for them goes nowhere until they have chosen their own.

Until an admin has a password of their own, the page takes one the family shares instead: the
installer makes one up and puts it in WEB_PASSWORD, and the family may choose another on the page,
stored hashed. A session opened with it does not know who anybody is, so it may do everything.
The first admin to choose their own password ends that: from then on the shared one opens
nothing, and every session opened with it ends.

A successful sign-in sets a signed session cookie; every page but the login and the health check
is behind it. Failed attempts are counted per client address and locked out for a while, and
across the whole site past that, so a page on the open internet is not worth guessing at. When
there is no password of either kind and the page is only on the loopback (or the waiver is set on
purpose), there is nothing to sign in to and every page is open.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import sqlite3
import threading
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import cache
from typing import Literal
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from itsdangerous import BadSignature, URLSafeSerializer

from familydb import passwords, personas, roles
from familydb.app import App
from familydb.config import Settings
from familydb.store import logins
from familydb.store.logins import Login, SignIn
from familydb.store.members import Member
from familydb.web import views

log = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)

# Signed in with the password the family shares, so as nobody in particular.
SESSION_KEY = "signed_in"
# Signed in as this person: their member id.
MEMBER_KEY = "member"
CSRF_KEY = "csrf"
# A mark of the password a session was opened with: the shared one, or the person's own.
# Changing it then ends every session that was signed in with the old one, which is what someone
# changing a password after a scare expects. It is an HMAC under the cookie signing key, not the
# password itself or a plain hash of it, so what sits in the cookie says nothing about the
# password to anyone holding the cookie.
PASSWORD_KEY = "pw"
# When this session signed in, as a Unix time. The first password chosen on the page may skip
# typing the installer's again, which the person has only just typed, but only this soon after.
SIGNED_IN_AT = "at"
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
# A browser that has signed in before carries this, and the site-wide ceiling does not apply to
# it. Otherwise fifty wrong guesses from anywhere would keep the family out as well, for as long
# as someone cared to keep guessing. The per-address lockout still applies. The cookie holds only
# a signed mark of the password it was earned with, so a new password makes every one worthless.
DEVICE_COOKIE = "familydb_device"
DEVICE_SALT = "familydb-device"
DEVICE_DAYS = 365
# Long enough for any real address, IPv6 with a zone included.
MAX_ADDRESS = 64
# Endpoints reachable without signing in. "static" covers the stylesheet on the login page.
OPEN_ENDPOINTS = frozenset({"auth.login", "auth.sign_in", "auth.logout", "web.healthz", "static"})
# Where somebody signed in with a starting password may go before they have chosen their own.
CHOOSING = frozenset({"family.you", "family.choose"})
# The permission each part of the page needs beyond signing in, by blueprint (roles.py says who
# has which). Reading needs nothing more: every page routes.py draws.
NEEDS: dict[str, roles.Permission] = {
    "chat": "chat",
    "edits": "change",
    "settings": "manage",
    "setup": "manage",
    "family": "manage",
}
# Pages in those parts that are anybody's own, and need no more than signing in.
EVERYBODY_S_OWN = CHOOSING
HOME = "/"
MIN_PASSWORD = passwords.MIN_LENGTH
WRONG_PASSWORD = "That password is not right."
WRONG_NAME_OR_PASSWORD = "That name and password do not go together."
NAME_TOO = "Type your name as well as your password."
LOCKED_OUT = "Too many tries. Wait a quarter of an hour and try again."
BAD_ORIGIN = "That request did not come from this page."
STALE_FORM = "That form was too old to use. Here it is again."
CHOOSE_FIRST = "choose your own password first"
MAX_NAME = 80


Kind = Literal["stranger", "anyone", "family", "person"]


@dataclass(frozen=True)
class Visitor:
    """Who is looking at the page.

    A stranger has not signed in, and sees only the login page and the health check. On a page
    with nothing to sign in to it is anyone at all. The family is whoever the shared password let
    in, whom the page cannot tell apart. A person signed in as themselves.
    """

    kind: Kind
    member: Member | None = None
    login: Login | None = None

    @property
    def signed_in(self) -> bool:
        """Whether a password let them in, and so whether one is asked for again before a key
        is shown or everybody is signed out."""
        return self.kind in ("family", "person")

    def may(self, permission: roles.Permission) -> bool:
        """Whether they may do this: as their role allows, when they signed in as themselves.

        Anybody the page cannot tell apart may do everything, because there is nobody to tell
        them from. A stranger may do nothing.
        """
        if self.kind == "person":
            return self.member is not None and roles.may(self.member.role, permission)
        return self.kind in ("anyone", "family")

    @property
    def manages(self) -> bool:
        """Whether they may reach what only an admin should: settings, setup, the family list."""
        return self.may("manage")

    @property
    def name(self) -> str | None:
        return self.member.display_name if self.member else None


STRANGER = Visitor("stranger")
ANYONE = Visitor("anyone")
FAMILY = Visitor("family")


def visitor() -> Visitor:
    """Who is asking, as the gate found them. Also a template global."""
    return g.get("visitor", STRANGER)


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

    def locked(self, who: str, now: datetime, *, known: bool = False) -> bool:
        """Whether this address, or the whole site, is being kept waiting.

        `known` says the browser has signed in here before, which the site-wide ceiling spares.
        """
        with self.lock:
            if not known and self._everyone_locked(now):
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
    """Whether there is a password the family shares: the installer's, or one chosen on the page.

    It opens the page only until an admin has a password of their own (`own_passwords`).
    """
    return bool(settings.web_password or settings.web_password_hash)


def password_chosen(settings: Settings) -> bool:
    """Whether the family has chosen their own password on the page, rather than the installer's."""
    return bool(settings.web_password_hash)


def own_passwords(conn: sqlite3.Connection) -> bool:
    """Whether people sign in as themselves, which they do from the moment an admin can.

    From then on the password the family shared opens nothing. A database that has not been
    migrated yet has nobody with a password of their own; any other error is raised, because
    answering "no" to a database that is only busy would let the shared password back in.
    """
    try:
        return logins.admin_can_sign_in(conn)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return False
        raise


def _signing_key() -> bytes:
    key = (current_app.secret_key or b"") if current_app else b""
    return key.encode() if isinstance(key, str) else key


def password_mark(settings: Settings) -> str:
    """A short mark of the shared password in force, for the session to carry."""
    password = (settings.web_password_hash or settings.web_password or "").encode()
    return hmac.new(_signing_key(), password, hashlib.sha256).hexdigest()[:16]


def login_mark(login: Login) -> str:
    """A short mark of somebody's own password, for their session to carry. A new password is a
    new hash with a new salt, so choosing one, or being given a starting one, changes the mark
    and signs them out everywhere else."""
    seen = f"{login.member_id}|{login.password_hash}".encode()
    return hmac.new(_signing_key(), seen, hashlib.sha256).hexdigest()[:16]


def password_matches(settings: Settings, given: str) -> bool:
    """Whether `given` is the password the family shares."""
    if settings.web_password_hash:
        return passwords.hash_matches(settings.web_password_hash, given)
    expected = settings.web_password or ""
    return bool(expected) and hmac.compare_digest(
        given.encode("utf-8", "replace"), expected.encode("utf-8")
    )


def confirms(given: str) -> bool:
    """Whether `given` is the password this visitor signed in with: their own, or the family's.

    Asked again before something that matters, such as showing a key or signing everybody out,
    so a phone left signed in is not enough to do it.
    """
    who = visitor()
    if who.login is not None:
        return passwords.hash_matches(who.login.password_hash, given)
    return password_matches(_app().settings, given)


@cache
def _decoy() -> str:
    """A hash nobody's password matches, made once, to check a name that signs in as nobody
    against: as slow as a real check, so a wrong name cannot be told from a wrong password by
    how long the answer takes."""
    return passwords.hash_password(secrets.token_urlsafe(32))


def _devices() -> URLSafeSerializer:
    return URLSafeSerializer(current_app.secret_key, salt=DEVICE_SALT)


def device_mark(login: Login | None, settings: Settings) -> str:
    """What the known-browser cookie holds: whose password it was earned with, and a mark of
    that password. Without a person, the mark of the shared password alone."""
    if login is None:
        return password_mark(settings)
    return f"{login.member_id}:{login_mark(login)}"


def known_device(conn: sqlite3.Connection, settings: Settings, *, personal: bool) -> bool:
    """Whether this browser signed in here before, under a password still in force.

    Once people sign in as themselves, only one of theirs counts: the shared password opens
    nothing, and a browser that knew only that one is a stranger like any other.
    """
    raw = request.cookies.get(DEVICE_COOKIE)
    if not raw:
        return False
    try:
        mark = _devices().loads(raw)
    except BadSignature:
        return False
    if not isinstance(mark, str):
        return False
    member, _, own = mark.partition(":")
    if own:
        found = logins.signing_in(conn, int(member)) if member.isdigit() else None
        return found is not None and hmac.compare_digest(own, login_mark(found.login))
    return not personal and hmac.compare_digest(mark, password_mark(settings))


def remember_device(response: Response, settings: Settings, login: Login | None = None) -> None:
    """Mark this browser as one that signed in, with the password it signed in with."""
    response.set_cookie(
        DEVICE_COOKIE,
        _devices().dumps(device_mark(login, settings)),
        max_age=DEVICE_DAYS * 24 * 3600,
        httponly=True,
        samesite="Lax",
        secure=settings.web_trust_proxy,
    )


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


# The setup pages (web/setup.py) send each form to the module that owns that change, and ask to be
# brought back afterwards. Only ever to a setup page: a hidden field is not a way to send a browser
# anywhere else, on this site or off it.
SETUP_PATH = "/setup"
SETUP_SAID = "setup"
SETUP_PROBLEM = "setup-problem"


def setup_return(target: str | None) -> str | None:
    """Where a setup page's form asked to go back to: a setup page on this site, or None."""
    target = safe_next(target)
    if target is None:
        return None
    path = urlsplit(target).path
    return target if path == SETUP_PATH or path.startswith(SETUP_PATH + "/") else None


def back_to_setup(target: str, *, said: str | None = None, problem: str | None = None) -> Response:
    """Send the browser back to the setup page it came from, with what happened."""
    if said:
        flash(said, SETUP_SAID)
    if problem:
        flash(problem, SETUP_PROBLEM)
    return redirect(target)


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


def _marked(expected: str) -> bool:
    """Whether this session carries the mark of the password it should have been opened with."""
    return hmac.compare_digest(str(session.get(PASSWORD_KEY, "")), expected)


def require_login() -> Response | tuple[str, int] | None:
    """Flask before_request hook: say who is asking, and send anyone not signed in to sign in.

    Somebody signed in as themselves costs one small query: whether they are still on the list,
    still allowed to sign in, and still using the password the session was opened with. Somebody
    not signed in at all, on a page with a shared password, costs nothing: they are sent to sign
    in without the page doing any work on their behalf.
    """
    g.visitor = STRANGER
    if request.endpoint in OPEN_ENDPOINTS:
        return None
    app = _app()
    settings = app.settings
    member_id = session.get(MEMBER_KEY)
    if isinstance(member_id, int):
        with closing(app.connect()) as conn:
            found = logins.signing_in(conn, member_id)
        if found is not None and _marked(login_mark(found.login)):
            g.visitor = Visitor("person", found.member, found.login)
            return _within_reach(g.visitor)
        # A new password, switched off, a role that may not sign in, or their password taken away.
        session.clear()
    elif session.get(SESSION_KEY):
        if _marked(password_mark(settings)):
            with closing(app.connect()) as conn:
                personal = own_passwords(conn)
            if not personal:
                g.visitor = FAMILY
                return None
        # The shared password changed, or an admin chose their own and so ended it.
        session.clear()
    elif not password_in_use(settings):
        with closing(app.connect()) as conn:
            personal = own_passwords(conn)
        if not personal:
            g.visitor = ANYONE  # nothing to sign in to
            return None
    if request.method not in SAFE_METHODS:
        return Response("sign in first", status=401, mimetype="text/plain")
    return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))


def _within_reach(who: Visitor) -> Response | tuple[str, int] | None:
    """Keep a person to what they may reach: their own password first, if an admin made it up
    for them, and no part of the page their role has no permission for."""
    if who.login is not None and who.login.temporary and request.endpoint not in CHOOSING:
        if request.method in SAFE_METHODS:
            return redirect(url_for("family.you"))
        return Response(CHOOSE_FIRST, status=403, mimetype="text/plain")
    needed = NEEDS.get(request.blueprint or "")
    if needed and request.endpoint not in EVERYBODY_S_OWN and not who.may(needed):
        title, why = views.REFUSALS[needed]
        why = why.format(name=personas.active(_app().settings).name)
        return render_template("403.html", title=title, why=why), 403
    return None


def start_session(found: SignIn, now: datetime) -> None:
    """Sign this browser in as this person, in place of whoever it was signed in as."""
    session.clear()
    session[MEMBER_KEY] = found.member.id
    session[PASSWORD_KEY] = login_mark(found.login)
    session[SIGNED_IN_AT] = int(now.timestamp())
    session.permanent = True


def keep_session(login: Login) -> None:
    """Keep this browser signed in after its own password changed: the mark follows the new
    one, while every other browser signed in with the old one is signed out."""
    session[PASSWORD_KEY] = login_mark(login)


def _find(conn: sqlite3.Connection, name: str) -> SignIn | None:
    """Whoever signs in by this name, on a database old enough to have nobody who does."""
    try:
        return logins.by_name(conn, name)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return None
        raise


def _login_page(
    personal: bool,
    *,
    error: str | None = None,
    target: str | None = None,
    name: str = "",
    status: int = 200,
) -> tuple[str, int]:
    return (
        render_template("login.html", error=error, next=target, personal=personal, name=name),
        status,
    )


@bp.get("/login")
def login() -> Response | tuple[str, int]:
    app = _app()
    with closing(app.connect()) as conn:
        personal = own_passwords(conn)
    if not personal and not password_in_use(app.settings):
        return redirect(HOME)  # nothing to sign in to
    if session.get(MEMBER_KEY) or session.get(SESSION_KEY):
        return redirect(HOME)  # and if that session is no longer good, the gate says so there
    return _login_page(personal, target=safe_next(request.args.get("next")))


@bp.post("/login")
def sign_in() -> Response | tuple[str, int]:
    """A name and that person's own password, or, while the family still shares one, that.

    A name that signs in as nobody takes as long to refuse as a wrong password, and gets the
    same answer, so the page is no way to find out who is in the family.
    """
    app = _app()
    settings = app.settings
    if not origin_ok():
        return _login_page(False, error=BAD_ORIGIN, status=400)

    now = app.clock.now()
    lockout = _lockout()
    who = client_address()
    target = safe_next(request.form.get("next"))
    name = " ".join(request.form.get("name", "").split())[:MAX_NAME]
    given = request.form.get("password", "")
    with closing(app.connect()) as conn:
        personal = own_passwords(conn)
        if not personal and not password_in_use(settings):
            return redirect(HOME)
        known = known_device(conn, settings, personal=personal)
        if lockout.locked(who, now, known=known):
            return _login_page(personal, error=LOCKED_OUT, name=name, status=429)
        found = _find(conn, name) if name else None
    if personal and not name:
        return _login_page(personal, error=NAME_TOO, target=target, status=400)

    if found is not None and passwords.hash_matches(found.login.password_hash, given):
        lockout.passed(who)
        start_session(found, now)
        log.info("web login as member %s from %s", found.member.id, who)
        # A starting password is for choosing their own with, and for nothing else.
        response = redirect(url_for("family.you") if found.login.temporary else target or HOME)
        remember_device(response, settings, found.login)
        return response
    if found is None and name:
        passwords.hash_matches(_decoy(), given)

    if not personal and password_matches(settings, given):
        lockout.passed(who)
        session.clear()
        session[SESSION_KEY] = True
        session[PASSWORD_KEY] = password_mark(settings)
        session[SIGNED_IN_AT] = int(now.timestamp())
        session.permanent = True
        log.info("web login with the family password from %s", who)
        response = redirect(target or HOME)
        remember_device(response, settings)
        return response

    lockout.failed(who, now)
    if lockout.locked(who, now, known=known):
        error = LOCKED_OUT
    else:
        error = WRONG_NAME_OR_PASSWORD if name else WRONG_PASSWORD
    return _login_page(personal, error=error, target=target, name=name, status=401)


@bp.post("/logout")
def logout() -> Response:
    if origin_ok():
        session.clear()
    return redirect(url_for("auth.login"))
