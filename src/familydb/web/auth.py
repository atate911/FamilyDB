"""The gate in front of the page: each person signs in as themselves (rules in
familydb/family.py, hashes in store/logins.py, permissions in familydb/roles.py and `NEEDS`).

Until an admin has a password of their own, the page takes one the family shares (WEB_PASSWORD or
one chosen on the page), which does everything as nobody in particular. The first admin's own
password ends it and every session opened with it. With no password of either kind on a loopback
page (or the waiver), there is nothing to sign in to. Failed attempts are locked out per client
address and, past a ceiling, across the site.
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

# Signed in with the shared password, so as nobody in particular.
SESSION_KEY = "signed_in"
# Signed in as this member id.
MEMBER_KEY = "member"
CSRF_KEY = "csrf"
# An HMAC (under the cookie signing key, so the cookie says nothing of the password) of the
# password a session was opened with: changing the password ends every session using the old one.
PASSWORD_KEY = "pw"
# Unix time of sign-in: the first password chosen on the page may skip retyping the installer's,
# but only this soon after.
SIGNED_IN_AT = "at"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
# Past this many tracked addresses, everything not currently locked out is forgotten.
MAX_TRACKED = 4096
# A site-wide ceiling, because per-address counting cannot stop someone with many addresses.
GLOBAL_ATTEMPTS = 50
GLOBAL_WINDOW_MINUTES = 15
# A browser that has signed in before carries this and is spared the site-wide ceiling, so wrong
# guesses from anywhere cannot keep the family out. The cookie holds a signed mark of the password
# it was earned with, so a new password makes every one worthless.
DEVICE_COOKIE = "familydb_device"
DEVICE_SALT = "familydb-device"
DEVICE_DAYS = 365
MAX_ADDRESS = 64
# Reachable without signing in. "static" covers the login page's stylesheet and the home-screen
# icons, which a phone fetches without the cookie.
OPEN_ENDPOINTS = frozenset(
    {"auth.login", "auth.sign_in", "auth.logout", "web.healthz", "web.manifest", "static"}
    # The service worker, which a phone fetches to show a notice, without the cookie (push.py).
    | {"web.service_worker"}
)
# Where somebody signed in with a starting password may go before they have chosen their own.
CHOOSING = frozenset({"family.you", "family.choose"})
# The permission each blueprint needs beyond signing in.
NEEDS: dict[str, roles.Permission] = {
    "chat": "chat",
    "edits": "change",
    "settings": "manage",
    "setup": "manage",
    "family": "manage",
    # Private words from any chat.
    "activity": "manage",
}
# A page that needs something other than its blueprint's, asked before the blueprint is.
NEEDS_HERE: dict[str, roles.Permission] = {
    "web.new_idea": "change",
    "web.edit_idea": "change",
    "web.edit_task": "change",
    "web.memory": "browse",
    "web.status": "browse",
    "web.wishes": "wish",
    "edits.add_wish": "wish",
    "edits.move_wish": "wish",
    "edits.withdraw_wish": "wish",
    "edits.ask_parent": "wish",
    "edits.answer_wish": "decide",
    # A kid may tick or snooze only her own (update_task holds that for page and chat alike).
    "edits.finish_task": "own_tasks",
    "edits.snooze_task": "own_tasks",
    # Taking back a change: anybody may try; undo.py says whose they may (a kid, her own tasks).
    "edits.undo": "own_tasks",
    # Notices on one's own devices, for anybody signed in as themselves (push.py).
    "family.push_on": "sign_in",
    "family.push_off": "sign_in",
}
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
    """Who is looking: a stranger (not signed in), anyone (nothing to sign in to), the family
    (the shared password, indistinguishable people) or a person signed in as themselves."""

    kind: Kind
    member: Member | None = None
    login: Login | None = None

    @property
    def signed_in(self) -> bool:
        """Whether a password let them in, so one is asked again before a key is shown."""
        return self.kind in ("family", "person")

    def may(self, permission: roles.Permission) -> bool:
        """A person by their role; anyone or the family may do everything; a stranger nothing."""
        if self.kind == "person":
            return self.member is not None and roles.may(self.member.role, permission)
        return self.kind in ("anyone", "family")

    @property
    def manages(self) -> bool:
        """Whether they may reach what only an admin should."""
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
    """Wrong passwords per client key, in memory. The settings page counts its reveal form under
    its own key, so a slip there never shuts the family out of the page."""

    failures: dict[str, int] = field(default_factory=dict)
    until: dict[str, datetime] = field(default_factory=dict)
    everyone: int = 0
    everyone_since: datetime | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def locked(self, who: str, now: datetime, *, known: bool = False) -> bool:
        """Whether this address, or the whole site (unless `known`), is being kept waiting."""
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
    """Whether there is a shared password (until `own_passwords`, it opens the page)."""
    return bool(settings.web_password or settings.web_password_hash)


def password_chosen(settings: Settings) -> bool:
    """Whether the family chose the shared password on the page, not the installer."""
    return bool(settings.web_password_hash)


def own_passwords(conn: sqlite3.Connection) -> bool:
    """Whether people sign in as themselves, from the moment an admin can; the shared password
    then opens nothing. Errors other than an unmigrated database are raised: answering "no" to
    a busy one would let the shared password back in."""
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
    """A short mark of somebody's own password for their session. A new password is a new salted
    hash, so it changes the mark."""
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
    """Whether `given` is the password this visitor signed in with, asked again before showing
    a key or signing everybody out, so a phone left signed in is not enough."""
    who = visitor()
    if who.login is not None:
        return passwords.hash_matches(who.login.password_hash, given)
    return password_matches(_app().settings, given)


@cache
def _decoy() -> str:
    """A hash nobody's password matches, so an unknown name takes as long to refuse as a wrong
    password."""
    return passwords.hash_password(secrets.token_urlsafe(32))


def _devices() -> URLSafeSerializer:
    return URLSafeSerializer(current_app.secret_key, salt=DEVICE_SALT)


def device_mark(login: Login | None, settings: Settings) -> str:
    """What the known-browser cookie holds: the member and a mark of their password, or the shared
    password's mark."""
    if login is None:
        return password_mark(settings)
    return f"{login.member_id}:{login_mark(login)}"


def known_device(conn: sqlite3.Connection, settings: Settings, *, personal: bool) -> bool:
    """Whether this browser signed in before under a password still in force; once people sign
    in as themselves, a browser that knew only the shared one is a stranger."""
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
    response.set_cookie(
        DEVICE_COOKIE,
        _devices().dumps(device_mark(login, settings)),
        max_age=DEVICE_DAYS * 24 * 3600,
        httponly=True,
        samesite="Lax",
        secure=settings.web_trust_proxy,
    )


def client_address() -> str:
    """Who is asking; correct behind a proxy only when WEB_TRUST_PROXY is set. Trimmed, because it
    may be a header's content and goes into the lockout table and the settings log."""
    return (request.remote_addr or "unknown")[:MAX_ADDRESS]


def safe_next(target: str | None) -> str | None:
    """A path on this site, or None. Backslashes are refused: browsers read "/\\elsewhere.example"
    as "//elsewhere.example", which would send someone off the site."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    if "\\" in target or "\r" in target or "\n" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    return target


# Setup forms ask to be brought back, only ever to a setup page.
SETUP_PATH = "/setup"
SETUP_SAID = "setup"
SETUP_PROBLEM = "setup-problem"


def setup_return(target: str | None) -> str | None:
    target = safe_next(target)
    if target is None:
        return None
    path = urlsplit(target).path
    return target if path == SETUP_PATH or path.startswith(SETUP_PATH + "/") else None


def back_to_setup(target: str, *, said: str | None = None, problem: str | None = None) -> Response:
    if said:
        flash(said, SETUP_SAID)
    if problem:
        flash(problem, SETUP_PROBLEM)
    return redirect(target)


def csrf_token() -> str:
    """This session's form token, the third lock after SameSite=Lax and the Origin check."""
    token = session.get(CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_KEY] = token
    return token


def csrf_ok(given: str | None) -> bool:
    """Whether this form carried this session's token. Encoded because `compare_digest` refuses
    non-ASCII strings, which must be a wrong answer, not a server error."""
    expected = session.get(CSRF_KEY)
    if not expected or not given:
        return False
    return hmac.compare_digest(given.encode("utf-8", "replace"), expected.encode("utf-8"))


def origin_ok() -> bool:
    """Whether a POST came from this site. A missing Origin is a non-browser client, which
    SameSite already covers."""
    origin = request.headers.get("Origin")
    if origin is None:
        return True
    return origin == f"{request.scheme}://{request.host}"


def refused() -> str | None:
    """None when a form may be acted on, else what to tell whoever sent it. A stale token is not
    reported as a foreign origin: signing out and back in leaves an open page with one."""
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
    return hmac.compare_digest(str(session.get(PASSWORD_KEY, "")), expected)


def require_login() -> Response | tuple[str, int] | None:
    """before_request hook: say who is asking, and send anyone not signed in to sign in. A person
    costs one query (still listed, allowed and on the same password); a stranger none."""
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
        session.clear()
    elif session.get(SESSION_KEY):
        if _marked(password_mark(settings)):
            with closing(app.connect()) as conn:
                personal = own_passwords(conn)
            if not personal:
                g.visitor = FAMILY
                return None
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
    """Keep a person to their own password first (if starting) and to what their role may reach."""
    if who.login is not None and who.login.temporary and request.endpoint not in CHOOSING:
        if request.method in SAFE_METHODS:
            return redirect(url_for("family.you"))
        return Response(CHOOSE_FIRST, status=403, mimetype="text/plain")
    needed = NEEDS_HERE.get(request.endpoint or "") or NEEDS.get(request.blueprint or "")
    if needed and request.endpoint not in EVERYBODY_S_OWN and not who.may(needed):
        title, why = views.REFUSALS[needed]
        why = why.format(name=personas.active(_app().settings).name)
        return render_template("403.html", title=title, why=why), 403
    return None


def start_session(found: SignIn, now: datetime) -> None:
    """Sign this browser in as this person, replacing any session."""
    session.clear()
    session[MEMBER_KEY] = found.member.id
    session[PASSWORD_KEY] = login_mark(found.login)
    session[SIGNED_IN_AT] = int(now.timestamp())
    session.permanent = True


def keep_session(login: Login) -> None:
    """Keep this browser signed in after its password changed; others using the old one end."""
    session[PASSWORD_KEY] = login_mark(login)


def _find(conn: sqlite3.Connection, name: str) -> SignIn | None:
    """Whoever signs in by this name; nobody on a database not yet migrated."""
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
        return redirect(HOME)  # a session no longer good is caught there
    return _login_page(personal, target=safe_next(request.args.get("next")))


@bp.post("/login")
def sign_in() -> Response | tuple[str, int]:
    """A name and that person's own password, or the shared one. An unknown name is refused as a
    wrong password is, so the page does not reveal who is in the family."""
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
