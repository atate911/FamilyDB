"""The Look page: everybody's own, a kid included. The choice is a cookie (`looks.py`), so it
writes no database row and makes no tool call."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from familydb.web import auth, looks

bp = Blueprint("look", __name__)

NOTICE = "edit"  # the same stream as the other forms, drawn by the base template
SAVED = "Saved. This browser wears {name} from now on."
NOT_ONE = "That is not one of the looks on this page."


@bp.get("/look")
def show() -> str:
    look, mode = looks.parse(request.cookies.get(looks.COOKIE))
    return render_template(
        "look.html",
        looks=looks.LOOKS,
        wearing=look,
        mode=mode,
        mode_words=looks.MODE_WORDS,
        default=looks.DEFAULT,
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
    flash(SAVED.format(name=look.name), NOTICE)
    response = redirect(url_for("look.show"))
    settings: Any = current_app.config["FAMILYDB_APP"].settings
    response.set_cookie(
        looks.COOKIE,
        looks.value(look, mode),
        max_age=looks.COOKIE_DAYS * 24 * 3600,
        httponly=True,
        samesite="Lax",
        secure=settings.web_trust_proxy,
    )
    return response
