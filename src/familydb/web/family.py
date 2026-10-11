"""The Family page: each form goes to `familydb.family`, which holds the rules and writes;
nothing here reaches a table. All an admin's, except Your password (/you), which is everybody's."""

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
from familydb import passwords, personas, roles
from familydb.agent import spending
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import calls
from familydb.store import knocks as knock_store
from familydb.store import logins as login_store
from familydb.store import members as member_store
from familydb.store import push as push_store
from familydb.store.logins import Login
from familydb.web import auth, views
from familydb.web import status as status_page
from familydb.web.once import once

log = logging.getLogger(__name__)

bp = Blueprint("family", __name__)

MAX_ID = 2**63 - 1
NOTICE = "edit"
ADDED = "{name} is on the family list."
CHANGED = "Saved {name}."
REMOVED = (
    "{name} is off the family list for good. What they said stays in the chat, without their name."
)
NOT_SURE = "Tick the box to say you are sure first: taking somebody off cannot be undone."
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
NO_BOT = "Connect the Telegram bot first, on the setup page's Telegram step: the link names it."
INVITE_LINK = "https://t.me/{bot}?start={code}"
# A starting password or link waits here, in memory, for the page that shows it once: it must not
# ride in the session cookie, which is signed but not sealed.
MADE_KEY = "FAMILYDB_MADE"
MADE_MINUTES = 10
PASSWORD = "password"
INVITE = "invite"


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
        limit = app.settings.kid_daily_messages
        since = spending.day_start(app.settings, app.clock.now())
        today = {
            person.id: calls.answered_for(conn, person.id, since=since)
            for person in everyone
            if limit and roles.daily_limited(person.role)
        }
    return render_template(
        "family.html",
        people=[_person(person, passwords_by_member.get(person.id)) for person in everyone],
        today=today,
        daily_limit=limit,
        roles=member_store.ROLES,
        role_words=views.ROLE_WORDS,
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
                form.get("role", "parent"),
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
        genders=views.GENDER_WORDS,
        today=_app().clock.today().isoformat(),
        personal=personal,
        mine=me is not None and me.id == member_id,
        made=_take_made(member_id),
        invite=_take_made(member_id, INVITE),
        bot=status_page.telegram_name(_app()),
        invite_hours=rules.INVITE_HOURS,
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
                birth_date=form.get("birth_date", rules.KEEP),
                gender=form.get("gender", rules.KEEP),
            )
    except rules.FamilyError as exc:
        return _answer(setup, problem=str(exc), fallback=here)
    log.info("family member %s changed from the page by %s", member_id, auth.client_address())
    return _answer(
        setup, said=CHANGED.format(name=person.display_name), fallback=url_for("family.show")
    )


@bp.post(f"/family/<int(max={MAX_ID}):member_id>/remove")
@once
def remove(member_id: int) -> Response:
    """Take somebody off the list for good, once the form's box saying so is ticked."""
    here = url_for("family.edit", member_id=member_id)
    if (complaint := auth.refused()) is not None:
        return _answer(None, problem=complaint, fallback=here)
    if request.form.get("sure") != "yes":
        return _answer(None, problem=NOT_SURE, fallback=here)
    app = _app()
    visiting = auth.visitor()
    try:
        with closing(app.connect()) as conn:
            person = rules.remove(
                conn,
                member_id,
                by=visiting.member.id if visiting.member else None,
                seen=request.form.get("revision", ""),
                now=utc_iso(app.clock.now()),
            )
    except rules.FamilyError as exc:
        return _answer(None, problem=str(exc), fallback=here)
    log.info("family member %s removed from the page by %s", member_id, auth.client_address())
    return _answer(
        None, said=REMOVED.format(name=person.display_name), fallback=url_for("family.show")
    )


@bp.post(f"/family/<int(max={MAX_ID}):member_id>/telegram")
@once
def link_telegram(member_id: int) -> Response:
    """Put a Telegram id on somebody on the list (the setup page's "That's me"). Nothing else
    changes, so the form has no revision: the one read here is passed on."""
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


@bp.post(f"/family/<int(max={MAX_ID}):member_id>/invite")
@once
def invite(member_id: int) -> Response:
    """A link that links somebody's Telegram when opened and Start is pressed, shown once (only a
    hash of its code is kept). The bot must be connected, since the link names it."""
    here = url_for("family.edit", member_id=member_id)
    if (complaint := auth.refused()) is not None:
        return _answer(None, problem=complaint, fallback=here)
    app = _app()
    bot = status_page.telegram_name(app)
    if bot is None:
        return _answer(None, problem=NO_BOT, fallback=here)
    me = auth.visitor().member
    try:
        with closing(app.connect()) as conn:
            code = rules.invite(conn, member_id, by=me.id if me else None, now=app.clock.now())
    except rules.FamilyError as exc:
        return _answer(None, problem=str(exc), fallback=here)
    _keep_made(member_id, INVITE_LINK.format(bot=bot, code=code), INVITE)
    log.warning("a Telegram link was made for member %s from %s", member_id, auth.client_address())
    return redirect(here)


@bp.post(f"/family/<int(max={MAX_ID}):member_id>/password")
@once
def sign_in_for(member_id: int) -> Response:
    """Make somebody a starting password, shown once, or take theirs away. Only by an admin signed
    in as themselves: under the shared password nobody is on record as making it."""
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
    app = _app()
    with closing(app.connect()) as conn:
        own = own_form(conn)
        parents = [
            person.display_name
            for person in member_store.list_all(conn)
            if person.active and roles.may(person.role, "decide")
        ]
        notices = _notices(app, conn)
    return (
        render_template(
            "you.html",
            error=error,
            own=own,
            parents_text=views.names_text([{"name": name} for name in parents]),
            notices=notices,
        ),
        status,
    )


def _notices(app: App, conn: Any) -> dict[str, Any] | None:
    """Notifications on this device, for somebody signed in as themselves while the family has
    them on (push.py); None otherwise."""
    member = auth.visitor().member
    if member is None or not app.settings.web_push:
        return None
    name = personas.active(app.settings).name
    return {
        "key": push_store.public_key(conn) or "",
        "devices": push_store.count_for(conn, member.id),
        "words": {key: words.format(name=name) for key, words in views.PUSH_WORDS.items()},
    }


# -- her replies kept at hand (docs/INTERFACE.md section 8) -------------------------------------


def _pinned_back() -> Response:
    """Back to the page the form named, a path on this site, else the conversation."""
    back = request.form.get("back", "")
    if not back.startswith("/") or back.startswith("//") or "\\" in back:
        back = url_for("chat.show", _anchor="latest")
    return redirect(back)


def _message_id() -> int | None:
    given = request.form.get("message", "")
    return int(given) if given.isascii() and given.isdigit() and len(given) <= 18 else None


@bp.post("/pin")
@once
def pin() -> Response:
    """Pin under her reply: kept at hand for whoever is signed in as themselves, in the column
    beside the box on a big screen and at the top of the conversation (familydb/family.py)."""
    from familydb.web import chat  # the conversation this person reads

    member = auth.visitor().member
    message_id = _message_id()
    if (complaint := auth.refused()) is not None:
        _say(complaint)
    elif member is None:
        _say("Sign in as yourself to pin her replies.")
    elif message_id is not None:
        app = _app()
        try:
            with closing(app.connect()) as conn:
                rules.pin(conn, member, message_id, chat_id=chat.my_chat(), now=app.clock.now())
        except rules.PinRefused as refused:
            _say(str(refused).capitalize() + ".")
    return _pinned_back()


@bp.post("/unpin")
@once
def unpin() -> Response:
    member = auth.visitor().member
    message_id = _message_id()
    if (complaint := auth.refused()) is not None:
        _say(complaint)
    elif member is not None and message_id is not None:
        with closing(_app().connect()) as conn:
            rules.unpin(conn, member, message_id)
    return _pinned_back()


@bp.post("/you/push")
def push_on() -> tuple[str, int]:
    """This device, to be told when she writes (static/push.js posts it, with the CSRF token)."""
    if (complaint := auth.refused()) is not None:
        return complaint, 403
    member = auth.visitor().member
    if member is None:
        return "Sign in as yourself to have notices.", 403
    app = _app()
    form = request.form
    try:
        with closing(app.connect()) as conn:
            rules.subscribe_push(
                conn,
                member,
                endpoint=form.get("endpoint", ""),
                p256dh=form.get("p256dh", ""),
                auth=form.get("auth", ""),
                now=app.clock.now(),
            )
    except rules.PushRefused as refused:
        return str(refused), 400
    return "", 204


@bp.post("/you/push/off")
def push_off() -> tuple[str, int]:
    if (complaint := auth.refused()) is not None:
        return complaint, 403
    member = auth.visitor().member
    if member is None:
        return "Sign in as yourself to have notices.", 403
    with closing(_app().connect()) as conn:
        rules.unsubscribe_push(conn, member, endpoint=request.form.get("endpoint", ""))
    return "", 204


def own_form(conn: Any) -> dict[str, Any]:
    """What the own-password form needs, here and on the setup page: the current password unless
    it was a starting one, or, under the shared password, the admins one of whom may claim."""
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
    """Somebody's own password: replaces theirs (this browser stays signed in, others do not), or
    under the shared password an admin choosing theirs, which ends the shared one."""
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
        attempt = f"{auth.client_address()} password"  # counted apart from sign-in
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
    if found is None:  # switched off in the same moment
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
    """Back to the setup page that sent the form; else home, or this page again on a problem."""
    if setup is not None:
        return auth.back_to_setup(setup, said=said, problem=problem)
    if problem is not None:
        return _you_page(error=problem, status=status)
    _say(said or "")
    return redirect(url_for("web.home"))


def _keep_made(member_id: int, secret: str, kind: str = PASSWORD) -> None:
    made: dict[str, tuple[str, float]] = current_app.config.setdefault(MADE_KEY, {})
    now = time.monotonic()
    for key in [key for key, (_, at) in made.items() if now - at > MADE_MINUTES * 60]:
        made.pop(key, None)
    made[f"{kind}:{session.get(auth.CSRF_KEY, '')}:{member_id}"] = (secret, now)


def _take_made(member_id: int, kind: str = PASSWORD) -> str | None:
    """The starting password (or link) this browser just made, once. Keyed on the session's form
    token, so a double click still lands on the page with it."""
    made: dict[str, tuple[str, float]] = current_app.config.setdefault(MADE_KEY, {})
    found = made.pop(f"{kind}:{session.get(auth.CSRF_KEY, '')}:{member_id}", None)
    if found is None or time.monotonic() - found[1] > MADE_MINUTES * 60:
        return None
    return found[0]


def _answer(
    setup: str | None, *, said: str | None = None, problem: str | None = None, fallback: str
) -> Response:
    if setup is not None:
        return auth.back_to_setup(setup, said=said, problem=problem)
    _say(problem or said or "")
    return redirect(fallback)


def _person(person: member_store.Member, login: Login | None = None) -> dict[str, Any]:
    telegram = person.channel_user_id if person.channel == rules.TELEGRAM else None
    # "own", "starting", or None when they cannot sign in whatever may be stored.
    may_sign_in = person.active and roles.may(person.role, "sign_in")
    sign_in = None
    if login is not None and may_sign_in:
        sign_in = "starting" if login.temporary else "own"
    today = _app().clock.today()
    return {
        "id": person.id,
        "name": person.display_name,
        "slot": person.slot or 0,
        "role": person.role,
        "birth_date": person.birth_date,
        "age": rules.age_on(person.birth_date, today),
        "gender": person.gender,
        "active": person.active,
        "telegram_id": telegram,
        # On a channel this page does not edit, such as the console.
        "elsewhere": person.channel if person.channel not in (None, rules.TELEGRAM) else None,
        "revision": rules.revision(person),
        "sign_in": sign_in,
        "role_may_sign_in": roles.may(person.role, "sign_in"),
    }
