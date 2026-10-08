"""Troubleshooting, for admins: what went wrong lately (the settings page's data) and the words
of every model call, as sent and as answered. Private words from every chat, so `auth.NEEDS`
limits it to admins. Read only: no model call, and nothing here is written."""

from __future__ import annotations

import re
from contextlib import closing
from datetime import timedelta
from typing import Any

from flask import Blueprint, abort, current_app, render_template, request

from familydb import logs
from familydb.agent import gateway
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import ai_texts, problems
from familydb.web import status as status_page
from familydb.web import views

bp = Blueprint("troubleshooting", __name__)

PROBLEMS_SHOWN = 100
FAILED_CALLS_SHOWN = 10
TEXTS_SHOWN = 100
PROBLEM_FILTERS = {"all": "Everything kept", "errors": "Errors only"}
TEXT_FILTERS = {"all": "Every call", "failed": "Failed calls"}


def _app() -> App:
    return current_app.config["FAMILYDB_APP"]


def page_data(app: App, conn: Any) -> dict[str, Any]:
    """What went wrong lately, from the logs and the call records, for the settings page."""
    tz = app.settings.tzinfo
    now = app.clock.now()
    day = utc_iso(now - timedelta(days=1))
    week = utc_iso(now - timedelta(days=7))
    show = request.args.get("show", "")
    show = show if show in PROBLEM_FILTERS else "all"
    seen = problems.counts_since(conn, since=day)
    stuck = status_page.waiting(conn, tz, app.settings.retry_max_attempts)
    failed = ai_texts.recent(conn, limit=FAILED_CALLS_SHOWN, failed_only=True)
    return {
        "attention": status_page.attention(app, conn),
        "stuck": stuck["messages"],
        "failed_lookups": status_page.troubles(conn, week, tz)["lookups"],
        "seen": {
            "errors": seen.get("ERROR", 0) + seen.get("CRITICAL", 0),
            "warnings": seen.get("WARNING", 0),
            "failed_calls": ai_texts.failures_since(conn, since=week),
        },
        "failed_calls": [_failed_row(row, tz) for row in failed],
        "problem_rows": [
            _problem_row(row, tz)
            for row in problems.recent(conn, limit=PROBLEMS_SHOWN, errors_only=show == "errors")
        ],
        "show": show,
        "filters": PROBLEM_FILTERS,
        "kept": ai_texts.sizes(conn),
        "kept_days": app.settings.keep_ai_text_days,
    }


def overview_lines(app: App, conn: Any) -> list[str]:
    """How the page stands, in a line or two, for the list of settings pages."""
    live = app.settings
    seen = problems.counts_since(conn, since=utc_iso(app.clock.now() - timedelta(days=1)))
    broken = seen.get("ERROR", 0) + seen.get("CRITICAL", 0)
    kept = (
        f"{live.keep_ai_text_days} day{'' if live.keep_ai_text_days == 1 else 's'}"
        if live.keep_ai_text_days
        else "no days"
    )
    return [
        f"{broken} error{'' if broken == 1 else 's'} in the last day."
        if broken
        else "No errors in the last day.",
        f"Logging {live.log_level.lower()}; the models' words kept {kept}.",
    ]


def _failed_row(row: dict[str, Any], tz: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "when": views.local_moment(row["created_at"], tz),
        "what": gateway.purpose(row["kind"]),
        "model": row["model"],
        "provider": row["provider"] or "",
        "error": row["error"] or "",
    }


def _problem_row(row: dict[str, Any], tz: Any) -> dict[str, Any]:
    return {
        "when": views.local_moment(row["last_at"], tz),
        "first": views.local_moment(row["first_at"], tz),
        "count": row["count"],
        "level": row["level"],
        "bad": row["level"] != "WARNING",
        "area": logs.area_of(row["source"]),
        "logger": row["source"],
        "message": row["message"],
        "detail": row["detail"] or "",
    }


@bp.get("/settings/troubleshooting/ai")
def texts() -> str:
    """Every model call, newest first: a line each, opening its words."""
    app = _app()
    tz = app.settings.tzinfo
    show = request.args.get("show", "")
    show = show if show in TEXT_FILTERS else "all"
    kind = request.args.get("kind", "")
    with closing(app.connect()) as conn:
        rows = ai_texts.recent(
            conn, limit=TEXTS_SHOWN, failed_only=show == "failed", kind=kind or None
        )
        kept = ai_texts.sizes(conn)
    return render_template(
        "troubleshooting_texts.html",
        rows=[
            {
                **_failed_row(row, tz),
                "about": row["about"],
                "failed": row["outcome"] == "failed",
                "iteration": row["iteration"],
                "size": row["request_chars"] + row["reply_chars"],
                "activity": _activity_key(row),
            }
            for row in rows
        ],
        show=show,
        filters=TEXT_FILTERS,
        kinds=_kinds(),
        kind=kind,
        kept=kept,
        kept_days=app.settings.keep_ai_text_days,
    )


@bp.get("/settings/troubleshooting/ai/<int:text_id>")
def one(text_id: int) -> str:
    """One call in full: what it was sent, and what it said or why it failed."""
    app = _app()
    tz = app.settings.tzinfo
    with closing(app.connect()) as conn:
        found = ai_texts.get(conn, text_id)
    if found is None:
        abort(404)
    return render_template(
        "troubleshooting_text.html",
        call=found,
        when=views.local_moment(found["created_at"], tz),
        what=gateway.purpose(found["kind"]),
        failed=found["outcome"] == "failed",
        activity=_activity_key(found),
    )


def _kinds() -> list[tuple[str, str]]:
    return [
        (kind, gateway.purpose(kind)) for kind in (*gateway.KINDS, gateway.LISTEN, gateway.LOOK)
    ]


KEY = re.compile(r"[0-9a-f]{16}")


def _activity_key(row: dict[str, Any]) -> str | None:
    """The address of the whole message or lookup this call belongs to (web/activity.py)."""
    if row.get("message_id") is not None:
        return f"m{row['message_id']}"
    if row.get("turn") and KEY.fullmatch(row["turn"]):
        return f"t{row['turn']}"
    return None
