"""The setup pages: FamilyDB set up one step at a time, in order, with the how-to beside each form.

The home page sends an admin here until it can answer anyone. Each step says why it matters,
what to do outside FamilyDB (where to get a key, what to send BotFather, what to click in Google
Cloud), and has one small form. The forms are the ones the rest of the page already uses: each
posts to the module that owns that change (settings.py, family.py) and asks to be brought back
here, so this module only reads, and setting up is never a second way of changing anything.

Nothing records progress. A step is done when what it sets up is there (`status.setup_progress`),
so leaving half way, or doing a step on the settings page instead, never leaves setup out of step.
"""

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

from familydb import personas
from familydb.agent import providers
from familydb.app import App
from familydb.store import knocks as knock_store
from familydb.store import members as member_store
from familydb.web import auth, fields, views
from familydb.web import status as status_page
from familydb.web.family import own_form
from familydb.web.settings import company_choice, google_panel

bp = Blueprint("setup", __name__)

TELEGRAM = "telegram"
# How long the Telegram step keeps looking again by itself while it waits: for the bot to connect,
# or for the first message from somebody's phone. Every WAIT_SECONDS, at most WAIT_TIMES times,
# and only while there is something to wait for; after that a link does it by hand.
WAIT_SECONDS = 4
WAIT_TIMES = 45
NEED_WORDS = {
    "needed": "needed before it can answer",
    "recommended": "recommended",
    "optional": "optional",
}
WEEKEND_QUESTION = "What should we do this weekend?"


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _told() -> dict[str, list[str]]:
    """What the form that sent the browser back here said, good news and bad kept apart."""
    return {
        "said": get_flashed_messages(category_filter=[auth.SETUP_SAID]),
        "problems": get_flashed_messages(category_filter=[auth.SETUP_PROBLEM]),
    }


def _admin(conn: Any) -> member_store.Member | None:
    return next((one for one in member_store.list_all(conn) if one.role == "admin"), None)


@bp.get("/setup")
def overview() -> str:
    """Every step and how far each has got, with one button to the next thing to do."""
    app = _app()
    with closing(app.connect()) as conn:
        steps = status_page.setup_progress(app, conn)
    return render_template(
        "setup.html",
        steps=steps,
        next_step=next((step for step in steps if not step.done), None),
        started=any(step.done for step in steps),
        ready=status_page.ready_to_answer(steps),
        needed=sum(1 for step in steps if step.need == "needed"),
        **_told(),
    )


@bp.get("/setup/done")
def done() -> str:
    """The end: what is set up, what was left for later, and the first thing to try."""
    app = _app()
    with closing(app.connect()) as conn:
        steps = status_page.setup_progress(app, conn)
        admin = _admin(conn)
    return render_template(
        "setup_done.html",
        steps=steps,
        ready=status_page.ready_to_answer(steps),
        later=[step for step in steps if not step.done],
        bot=status_page.telegram_name(app),
        admin=admin,
        question=WEEKEND_QUESTION,
        **_told(),
    )


@bp.get("/setup/<name>")
def step(name: str) -> str:
    """One step: why, how, the form, and the way on."""
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
    """Your own password: the first admin's, which ends the shared one, or yours to change."""
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
        # The company's lineup, cheapest first, and what each level of it costs.
        "lineup": [
            {"label": model.label, "level": model.level, "price": views.price_text(model.price)}
            for model in providers.catalog.lineup(choice["company"])
        ],
        "limit": live.daily_spend_limit,
    }


def _home(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    return {
        "home": {
            "area": live.home_area,
            "lat": live.home_lat,
            "lon": live.home_lon,
            "tz": live.tzinfo.key,
            "units": live.weather_units,
        },
        "zones": fields.zones(),
    }


def _telegram(app: App, conn: Any) -> dict[str, Any]:
    """The bot, whether it is connected, and whether it knows whoever is setting it up."""
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
        # What to call the bot in Telegram: what she is called everywhere else.
        "assistant": personas.active(live).name,
        "bot": bot,
        "admin": admin,
        "knocks": knocks,
        "refresh": refresh,
        "refresh_seconds": WAIT_SECONDS,
        "gave_up": waiting and refresh is None,
        "digest_here": live.digest_chat_id == "web",
    }


def _family(app: App, conn: Any) -> dict[str, Any]:
    live = app.settings
    return {
        "people": member_store.list_all(conn),
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
