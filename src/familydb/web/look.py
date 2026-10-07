"""The Look page: everybody's own, a kid included. A person's choice is kept with them
(`family.choose_look`), so it follows them to every phone and computer they sign in on, and is
also the browser's cookie (`looks.py`), which the pages before anybody signs in wear. While the
family shares one password nobody in particular is signed in, so it stays in this browser."""

from __future__ import annotations

from contextlib import closing
from typing import Any

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from familydb import family as rules
from familydb.web import auth, looks

bp = Blueprint("look", __name__)

NOTICE = "edit"  # the same stream as the other forms, drawn by the base template
SAVED = "Saved. You'll see {name} on every phone and computer you sign in on."
SAVED_HERE = "Saved. This browser wears {name} from now on."
NOT_ONE = "That is not one of the looks on this page."


@bp.get("/look")
def show() -> str:
    member = auth.visitor().member
    look, mode = looks.parse(member.look if member else request.cookies.get(looks.COOKIE))
    return render_template(
        "look.html",
        looks=looks.LOOKS,
        wearing=look,
        mode=mode,
        mode_words=looks.MODE_WORDS,
        default=looks.DEFAULT,
        follows=member is not None,
    )


@bp.post("/look")
def save() -> Response:
    problem = auth.refused()
    if problem:
        flash(problem, NOTICE)
        return redirect(url_for("look.show"))
    chosen = looks.choose(request.form.get("theme"), request.form.get("mode"))
    if chosen is None:
        flash(NOT_ONE, NOTICE)
        return redirect(url_for("look.show"))
    look, mode = chosen
    app: Any = current_app.config["FAMILYDB_APP"]
    member = auth.visitor().member
    if member is not None:
        with closing(app.connect()) as conn:
            rules.choose_look(conn, member.id, looks.value(look, mode))
    flash((SAVED if member is not None else SAVED_HERE).format(name=look.name), NOTICE)
    response = redirect(url_for("look.show"))
    looks.remember(response, looks.value(look, mode), secure=app.settings.web_trust_proxy)
    return response
