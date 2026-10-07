"""The setup pages, one step at a time. Each form posts to the module that owns the change
(settings.py, family.py) and asks to come back here, so this module only reads. Progress is
never stored: a step is done when what it sets up is there (`status.setup_progress`)."""

from __future__ import annotations

from contextlib import closing
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    get_flashed_messages,
    render_template,
    request,
    url_for,
)

from familydb import personas, presents, roles
from familydb.agent import providers
from familydb.app import App
from familydb.store import knocks as knock_store
from familydb.store import logins as login_store
from familydb.store import members as member_store
from familydb.web import auth, fields, views
from familydb.web import status as status_page
from familydb.web.family import own_form
from familydb.web.settings import company_choice, google_panel

bp = Blueprint("setup", __name__)

TELEGRAM = "telegram"
# The Telegram step reloads itself every WAIT_SECONDS, at most WAIT_TIMES times, while it waits
# for the bot to connect or a first message; after that a link does it by hand.
WAIT_SECONDS = 4
WAIT_TIMES = 45
NEED_WORDS = {
    "needed": "needed before it can answer",
    "recommended": "recommended",
    "optional": "optional",
}


STEP_GLYPHS = {
    "you": "smile",
    "password": "lock",
    "model": "sparkle",
    "home": "home",
    "telegram": "send",
    "family": "people",
    "calendar": "cal",
}


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _told() -> dict[str, list[str]]:
    """What the form that sent the browser back here said."""
    return {
        "said": get_flashed_messages(category_filter=[auth.SETUP_SAID]),
        "problems": get_flashed_messages(category_filter=[auth.SETUP_PROBLEM]),
    }


def _admin(conn: Any) -> member_store.Member | None:
    return next((one for one in member_store.list_all(conn) if one.role == "admin"), None)


@bp.get("/setup")
def overview() -> str:
    """Every step and how far each has got."""
    app = _app()
    with closing(app.connect()) as conn:
        steps = status_page.setup_progress(app, conn)
    return render_template(
        "setup.html",
        steps=steps,
        next_step=next((step for step in steps if not step.done and not step.skipped), None),
        started=any(step.done for step in steps),
        ready=status_page.ready_to_answer(steps),
        needed=sum(1 for step in steps if step.need == "needed"),
        **_told(),
    )


@bp.get("/setup/done")
def done() -> str:
    """The end: what is set up and what was left for later."""
    app = _app()
    with closing(app.connect()) as conn:
        steps = status_page.setup_progress(app, conn)
        admin = _admin(conn)
        # The admin setting up is asked for their own on the password step, not here.
        unsigned = [one for one in without_sign_in(conn) if admin is None or one.id != admin.id]
    return render_template(
        "setup_done.html",
        steps=steps,
        ready=status_page.ready_to_answer(steps),
        later=[step for step in steps if not step.done and not step.skipped],
        bot=status_page.telegram_name(app),
        admin=admin,
        unsigned=presents.join_names([one.display_name for one in unsigned]),
        unsigned_many=len(unsigned) > 1,
        step_glyphs=STEP_GLYPHS,
        question=views.WEEKEND_QUESTION,
        **_told(),
    )


@bp.get("/setup/<name>")
def step(name: str) -> str:
    if name not in status_page.SETUP_ORDER:
        abort(404)
    app = _app()
    with closing(app.connect()) as conn:
        steps = status_page.setup_progress(app, conn)
        extra = PAGES[name](app, conn)
    index = status_page.SETUP_ORDER.index(name)
    here = steps[index]
    later = steps[index + 1] if index + 1 < len(steps) else None
    return render_template(
        "setup_step.html",
        steps=steps,
        step=here,
        number=index + 1,
        total=len(steps),
        need_words=NEED_WORDS,
        previous=url_for("setup.step", name=steps[index - 1].name)
        if index
        else url_for("setup.overview"),
        following=url_for("setup.step", name=later.name) if later else url_for("setup.done"),
        then=url_for("setup.step", name=name),
        **_told(),
        **extra,
    )


def _password(app: App, conn: Any) -> dict[str, Any]:
    return {
        "personal": auth.own_passwords(conn),
        "admin": _admin(conn),
        "own": own_form(conn),
    }


def _you(app: App, conn: Any) -> dict[str, Any]:
    return {"admin": _admin(conn)}


def _model(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    choice = company_choice(live, request.args.get("company", ""))
    return {
        **choice,
        "lineup": [
            {"label": model.label, "level": model.level, "price": views.price_text(model.price)}
            for model in providers.catalog.lineup(choice["company"])
        ],
        "limit": live.daily_spend_limit,
    }


def _home(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    offered = fields.zones()
    return {
        "home": {
            "area": live.home_area,
            "lat": live.home_lat,
            "lon": live.home_lon,
            "tz": live.tzinfo.key,
            # The server's own zone may not be on the list (Etc/UTC): it is then offered, chosen.
            "tz_listed": live.tzinfo.key in offered,
            "units": live.weather_units,
        },
        "zones": views.zone_groups(offered, app.clock.now()),
    }


def _telegram(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    state = app.channel_states.get(TELEGRAM, "")
    bot = status_page.telegram_name(app)
    admin = _admin(conn)
    knocks = [
        views.knock_row(knock, live.tzinfo)
        for knock in knock_store.recent(conn, channel=TELEGRAM)
        if not (knock.chat_id or "").startswith("-")  # a private chat is somebody's own phone
    ]
    linked = bool(admin and admin.channel_user_id)
    if not live.telegram_bot_token:
        stage = "token"
    elif state.startswith("the token"):
        stage = "refused"
    elif bot is None:
        stage = "connecting"  # also when this page runs without the bot, which never connects
    elif admin is None:
        stage = "nobody"
    elif not linked:
        stage = "link"
    else:
        stage = "linked"
    waited = request.args.get("wait", "0")
    waited_times = int(waited) if waited.isdigit() else 0
    waiting = stage == "connecting" or (stage == "link" and not knocks)
    refresh = None
    if waiting and waited_times < WAIT_TIMES:
        refresh = url_for("setup.step", name="telegram", wait=waited_times + 1)
    return {
        "stage": stage,
        "state": state,
        "assistant": personas.active(live).name,
        "bot": bot,
        "admin": admin,
        "knocks": knocks,
        "refresh": refresh,
        "refresh_seconds": WAIT_SECONDS,
        "gave_up": waiting and refresh is None,
        "digest_here": live.digest_chat_id == "web",
        "digest_day": views.DAY_NAMES[live.digest_day],
        "reads_groups": status_page.telegram_reads_groups(app),
    }


def without_sign_in(conn: Any) -> list[member_store.Member]:
    """Who on the list may sign in but has no password of any kind yet: named where setup ends."""
    logins = login_store.by_member(conn)
    return [
        person
        for person in member_store.list_all(conn)
        if person.active and person.id not in logins and roles.may(person.role, "sign_in")
    ]


def _family(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    return {
        "people": member_store.list_all(conn),
        "logins": login_store.by_member(conn),
        "roles": member_store.ROLES,
        "role_words": views.ROLE_WORDS,
        "bot": status_page.telegram_name(app),
        "knocks": [
            views.knock_row(knock, live.tzinfo)
            for knock in knock_store.recent(conn, channel=TELEGRAM)
        ],
    }


def _calendar(app: App, conn: Any) -> dict[str, Any]:
    return {"google": google_panel(app.settings)}


PAGES = {
    "password": _password,
    "you": _you,
    "model": _model,
    "home": _home,
    "telegram": _telegram,
    "family": _family,
    "calendar": _calendar,
}
