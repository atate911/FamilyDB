"""The Family page: who is on the list, and adding or changing somebody.

Like the edit forms, this module does not know how to save anything. It hands each form to
`familydb.family`, which holds the rules — one person per name, always an admin, no quiet
overwrites — and writes through `store.members`. Nothing here reaches a table itself.
"""

from __future__ import annotations

import logging
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
    url_for,
)

from familydb import family as rules
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import members as member_store
from familydb.web import auth
from familydb.web.once import once

log = logging.getLogger(__name__)

bp = Blueprint("family", __name__)

MAX_ID = 2**63 - 1
NOTICE = "edit"  # the same stream as the other edit forms, drawn by the base template
ADDED = "{name} is on the family list."
CHANGED = "Saved {name}."


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def _say(message: str) -> None:
    flash(message, NOTICE)


@bp.get("/family")
def show() -> str:
    with closing(_app().connect()) as conn:
        everyone = member_store.list_all(conn, active_only=False)
    return render_template(
        "family.html",
        people=[_person(person) for person in everyone],
        roles=member_store.ROLES,
    )


@bp.post("/family")
@once
def add() -> Response:
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return redirect(url_for("family.show"))
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
        _say(str(exc))
        return redirect(url_for("family.show"))
    log.info("family member %s added from the page by %s", person.id, auth.client_address())
    _say(ADDED.format(name=person.display_name))
    return redirect(url_for("family.show"))


@bp.get(f"/family/<int(max={MAX_ID}):member_id>")
def edit(member_id: int) -> str:
    with closing(_app().connect()) as conn:
        person = member_store.get(conn, member_id)
    if person is None:
        abort(404)
    return render_template("member_form.html", person=_person(person), roles=member_store.ROLES)


@bp.post(f"/family/<int(max={MAX_ID}):member_id>")
@once
def change(member_id: int) -> Response:
    back = redirect(url_for("family.edit", member_id=member_id))
    if (complaint := auth.refused()) is not None:
        _say(complaint)
        return back
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
        _say(str(exc))
        return back
    log.info("family member %s changed from the page by %s", member_id, auth.client_address())
    _say(CHANGED.format(name=person.display_name))
    return redirect(url_for("family.show"))


def _person(person: member_store.Member) -> dict[str, Any]:
    telegram = person.channel_user_id if person.channel == rules.TELEGRAM else None
    return {
        "id": person.id,
        "name": person.display_name,
        "role": person.role,
        "active": person.active,
        "telegram_id": telegram,
        # Somebody the bot knows on a channel this page does not edit, such as the console.
        "elsewhere": person.channel if person.channel not in (None, rules.TELEGRAM) else None,
        "revision": rules.revision(person),
    }
