"""The Family page: who is on the list, adding or changing somebody, and how they sign in.

Like the edit forms, this module does not know how to save anything. It hands each form to
`familydb.family`, which holds the rules — one person per name, always an admin, no quiet
overwrites, an admin who can always sign in — and writes through `store.members` and
`store.logins`. Nothing here reaches a table itself.

Everything here is an admin's, except Your password (/you), which is everybody's own: where a
person changes their password, chooses one in place of a starting password an admin made up for
them, or, while the family still shares a password, where an admin chooses theirs and so ends it.
"""

from __future__ import annotations

import logging
import time
from contextlib import closing
from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from familydb import family as rules
from familydb import passwords
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import knocks as knock_store
from familydb.store import logins as login_store
from familydb.store import members as member_store
from familydb.store.logins import Login
from familydb.web import auth, views
from familydb.web.once import once

log = logging.getLogger(__name__)

bp = Blueprint("family", __name__)

MAX_ID = 2**63 - 1
NOTICE = "edit"  # the same stream as the other edit forms, drawn by the base template
ADDED = "{name} is on the family list."
CHANGED = "Saved {name}."
LINKED = "Linked. The bot knows {name} on Telegram now, and will answer them."
NOBODY = "There is nobody by that number any more."
PASSWORD_SAVED = (
    "Saved. That is your password now: every other browser signed in as you asks for it."
)
PASSWORD_CLAIMED = (
    "Saved. You sign in as {name} from now on, and so does everybody else as themselves: give "
    "them each a starting password on the Family page."
)
PASSWORD_TWICE = "The two new passwords were not the same. Type them again."
PASSWORD_CURRENT = "Type the password you use now, to show it is you."
WRONG_PASSWORD = "That password is not right."
LOCKED_OUT = "Too many tries. Wait a quarter of an hour."
WHICH_ONE = "Say which admin you are."
TAKEN_AWAY = "{name} can no longer sign in to the page, and is signed out wherever they were."
YOURS_FIRST = (
    "Choose your own password first, as an admin; then you can give everybody else one here."
)
THAT_IS_YOU = "That is you: change your own password on the Your password page."
# A starting password waits here for the page that shows it, once, and is gone when shown. In
# memory, like the form tokens: a password must not ride in the session cookie, which is signed
# but not sealed, and a restart before it is shown only means making another.
MADE_KEY = "FAMILYDB_MADE"
MADE_MINUTES = 10


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _say(message: str) -> None:
    flash(message, NOTICE)


@bp.get("/family")
def show() -> str:
    app = _app()
    with closing(app.connect()) as conn:
        everyone = member_store.list_all(conn, active_only=False)
        strangers = knock_store.recent(conn, channel=rules.TELEGRAM)
        passwords_by_member = login_store.by_member(conn)
        personal = auth.own_passwords(conn)
    return render_template(
        "family.html",
        people=[_person(person, passwords_by_member.get(person.id)) for person in everyone],
        roles=member_store.ROLES,
        knocks=[views.knock_row(knock, app.settings.tzinfo) for knock in strangers],
        personal=personal,
    )


@bp.post("/family")
@once
def add() -> Response:
    back = auth.setup_return(request.form.get("then"))
    if (complaint := auth.refused()) is not None:
        return _answer(back, problem=complaint, fallback=url_for("family.show"))
    app = _app()
    form = request.form
    try:
        with closing(app.connect()) as conn:
            person = rules.add(
                conn,
                form.get("name", ""),
                form.get("role", "member"),
                telegram_id=form.get("telegram_id"),
                now=utc_iso(app.clock.now()),
            )
    except rules.FamilyError as exc:
        return _answer(back, problem=str(exc), fallback=url_for("family.show"))
    log.info("family member %s added from the page by %s", person.id, auth.client_address())
    return _answer(
        back, said=ADDED.format(name=person.display_name), fallback=url_for("family.show")
    )


@bp.get(f"/family/<int(max={MAX_ID}):member_id>")
def edit(member_id: int) -> str:
    with closing(_app().connect()) as conn:
        person = member_store.get(conn, member_id)
        login = login_store.get(conn, member_id)
        personal = auth.own_passwords(conn)
    if person is None:
        abort(404)
    me = auth.visitor().member
    return render_template(
        "member_form.html",
        person=_person(person, login),
        roles=member_store.ROLES,
        personal=personal,
        mine=me is not None and me.id == member_id,
        made=_take_made(member_id),
    )


@bp.post(f"/family/<int(max={MAX_ID}):member_id>")
@once
def change(member_id: int) -> Response:
    setup = auth.setup_return(request.form.get("then"))
    here = url_for("family.edit", member_id=member_id)
    if (complaint := auth.refused()) is not None:
        return _answer(setup, problem=complaint, fallback=here)
    app = _app()
    form = request.form
    try:
        with closing(app.connect()) as conn:
            person = rules.change(
                conn,
                member_id,
                name=form.get("name", ""),
                role=form.get("role", ""),
                active=form.get("active") == "yes",
                telegram_id=form.get("telegram_id"),
                seen=form.get("revision", ""),
                now=utc_iso(app.clock.now()),
            )
    except rules.FamilyError as exc:
        return _answer(setup, problem=str(exc), fallback=here)
    log.info("family member %s changed from the page by %s", member_id, auth.client_address())
    return _answer(
        setup, said=CHANGED.format(name=person.display_name), fallback=url_for("family.show")
    )


@bp.post(f"/family/<int(max={MAX_ID}):member_id>/telegram")
@once
def link_telegram(member_id: int) -> Response:
    """Put a Telegram id on somebody already on the list, as it arrived in a message to the bot.

    The setup page's "That's me", pressed after messaging the bot from a phone. Nothing else about
    the person changes, so the form carries no revision of its own: the one read here is passed
    on, and the rules still refuse an id that somebody else already has.
    """
    setup = auth.setup_return(request.form.get("then"))
    here = url_for("family.show")
    if (complaint := auth.refused()) is not None:
        return _answer(setup, problem=complaint, fallback=here)
    app = _app()
    try:
        with closing(app.connect()) as conn:
            person = member_store.get(conn, member_id)
            if person is None:
                return _answer(setup, problem=NOBODY, fallback=here)
            person = rules.change(
                conn,
                member_id,
                name=person.display_name,
                role=person.role,
                active=person.active,
                telegram_id=request.form.get("telegram_id"),
                seen=rules.revision(person),
                now=utc_iso(app.clock.now()),
            )
    except rules.FamilyError as exc:
        return _answer(setup, problem=str(exc), fallback=here)
    log.info("Telegram linked to member %s from the page by %s", member_id, auth.client_address())
    return _answer(setup, said=LINKED.format(name=person.display_name), fallback=here)


@bp.post(f"/family/<int(max={MAX_ID}):member_id>/password")
@once
def sign_in_for(member_id: int) -> Response:
    """Make somebody a starting password, shown once on their page, or take theirs away.

    Only by an admin signed in as themselves: while the family shares a password there is nobody
    to say who made it, and the first admin's own password comes first (see `choose`).
    """
    here = url_for("family.edit", member_id=member_id)
    if (complaint := auth.refused()) is not None:
        return _answer(None, problem=complaint, fallback=here)
    me = auth.visitor().member
    if me is None:
        return _answer(None, problem=YOURS_FIRST, fallback=here)
    if me.id == member_id:
        return _answer(None, problem=THAT_IS_YOU, fallback=here)
    app = _app()
    try:
        with closing(app.connect()) as conn:
            if request.form.get("action") == "remove":
                person = rules.remove_login(conn, member_id)
                said = TAKEN_AWAY.format(name=person.display_name)
            else:
                made = rules.give_starting_password(
                    conn, member_id, by=me.id, now=utc_iso(app.clock.now())
                )
                _keep_made(member_id, made)
                said = None  # their page says it, with the password
    except rules.FamilyError as exc:
        return _answer(None, problem=str(exc), fallback=here)
    what = "took away the password of" if said else "made a starting password for"
    log.warning("member %s %s member %s from %s", me.id, what, member_id, auth.client_address())
    if said:
        _say(said)
    return redirect(here)


@bp.get("/you")
def you() -> str | tuple[str, int]:
    return _you_page()


def _you_page(*, error: str | None = None, status: int = 200) -> tuple[str, int]:
    """Your own password: to change it, to choose it after a starting one, or, while the family
    still shares a password, for an admin to choose theirs and so end the shared one."""
    with closing(_app().connect()) as conn:
        own = own_form(conn)
    return render_template("you.html", error=error, own=own), status


def own_form(conn: Any) -> dict[str, Any]:
    """What the own-password form needs, wherever it is drawn: here, and on the setup page.

    Signed in as themselves, it asks for the password in use, unless that was a starting one they
    have only just signed in with. Let in by the family password, it offers the admins, one of
    whom may be the first to have their own.
    """
    who = auth.visitor()
    claimable: list[member_store.Member] = []
    if who.member is None and not auth.own_passwords(conn):
        claimable = [person for person in member_store.list_all(conn) if person.role == "admin"]
    temporary = who.login is not None and who.login.temporary
    return {
        "claimable": claimable,
        "name": who.name,
        "temporary": temporary,
        "needs_current": who.login is not None and not temporary,
        "least": passwords.MIN_LENGTH,
        "most": passwords.MAX_LENGTH,
    }


@bp.post("/you")
@once
def choose() -> Response | tuple[str, int]:
    """Somebody's own password. Signed in as themselves, it replaces theirs, and asks for the one
    it replaces unless that was a starting password they have only just used; this browser stays
    signed in and every other one signed in as them does not. While the family shares a password,
    it is an admin choosing theirs, which signs this browser in as them and ends the shared one.
    """
    back = auth.setup_return(request.form.get("then"))
    if (complaint := auth.refused()) is not None:
        return _chosen(back, problem=complaint)
    new, again = request.form.get("new", ""), request.form.get("again", "")
    if new != again:
        return _chosen(back, problem=PASSWORD_TWICE)
    app = _app()
    who = auth.visitor()
    now = app.clock.now()
    if who.login is not None and not who.login.temporary:
        attempt = f"{auth.client_address()} password"  # counted apart from signing in
        lockout = current_app.config["FAMILYDB_LOCKOUT"]
        if lockout.locked(attempt, now):
            return _chosen(back, problem=LOCKED_OUT, status=429)
        given = request.form.get("current", "")
        if not auth.confirms(given):
            lockout.failed(attempt, now)
            return _chosen(back, problem=WRONG_PASSWORD if given else PASSWORD_CURRENT, status=401)
        lockout.passed(attempt)
    try:
        with closing(app.connect()) as conn:
            if who.member is not None:
                rules.choose_password(conn, who.member.id, new, now=utc_iso(now))
                person = who.member
            else:
                chosen = request.form.get("member", "")
                if not chosen.isdigit() or int(chosen) > MAX_ID:
                    return _chosen(back, problem=WHICH_ONE)
                person = rules.claim(conn, int(chosen), new, now=utc_iso(now))
            found = login_store.signing_in(conn, person.id)
    except rules.FamilyError as exc:
        return _chosen(back, problem=str(exc))
    if found is None:  # switched off in the same moment; the gate turns them away next time
        return _chosen(back, problem=NOBODY)
    if who.member is None:
        auth.start_session(found, now)
        log.warning("member %s ended the family password from %s", person.id, auth.client_address())
        said = PASSWORD_CLAIMED.format(name=person.display_name)
    else:
        auth.keep_session(found.login)
        log.warning("member %s chose a new password from %s", person.id, auth.client_address())
        said = PASSWORD_SAVED
    response = _chosen(back, said=said)
    auth.remember_device(response, app.settings, found.login)
    return response


def _chosen(
    setup: str | None, *, said: str | None = None, problem: str | None = None, status: int = 400
) -> Any:
    """Back to the setup page that sent the form; else home when it worked, and the page again,
    saying what was wrong, when it did not."""
    if setup is not None:
        return auth.back_to_setup(setup, said=said, problem=problem)
    if problem is not None:
        return _you_page(error=problem, status=status)
    _say(said or "")
    return redirect(url_for("web.home"))


def _keep_made(member_id: int, password: str) -> None:
    """Hold a starting password for this browser's next look at that person's page."""
    made: dict[str, tuple[str, float]] = current_app.config.setdefault(MADE_KEY, {})
    now = time.monotonic()
    for key in [key for key, (_, at) in made.items() if now - at > MADE_MINUTES * 60]:
        made.pop(key, None)
    made[f"{session.get(auth.CSRF_KEY, '')}:{member_id}"] = (password, now)


def _take_made(member_id: int) -> str | None:
    """The starting password this browser just made for that person, once, then never again.

    Keyed on the session's form token, which was there before the form was sent: a double click
    lands on the page with the password on it even if the browser never saw the first answer.
    """
    made: dict[str, tuple[str, float]] = current_app.config.setdefault(MADE_KEY, {})
    found = made.pop(f"{session.get(auth.CSRF_KEY, '')}:{member_id}", None)
    if found is None or time.monotonic() - found[1] > MADE_MINUTES * 60:
        return None
    return found[0]


def _answer(
    setup: str | None, *, said: str | None = None, problem: str | None = None, fallback: str
) -> Response:
    """Back to the setup page that sent the form, or to this page's own, with what happened."""
    if setup is not None:
        return auth.back_to_setup(setup, said=said, problem=problem)
    _say(problem or said or "")
    return redirect(fallback)


def _person(person: member_store.Member, login: Login | None = None) -> dict[str, Any]:
    telegram = person.channel_user_id if person.channel == rules.TELEGRAM else None
    # How they sign in to the page: "own", "starting", or None when they cannot (no password, a
    # kid, or switched off, whatever may be stored for them).
    sign_in = None
    if login is not None and person.active and person.role in login_store.SIGN_IN_ROLES:
        sign_in = "starting" if login.temporary else "own"
    return {
        "id": person.id,
        "name": person.display_name,
        "role": person.role,
        "active": person.active,
        "telegram_id": telegram,
        # Somebody the bot knows on a channel this page does not edit, such as the console.
        "elsewhere": person.channel if person.channel not in (None, rules.TELEGRAM) else None,
        "revision": rules.revision(person),
        "sign_in": sign_in,
    }
