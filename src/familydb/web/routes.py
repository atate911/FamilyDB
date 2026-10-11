"""The pages. Every view reads; nothing here writes to the database."""

from __future__ import annotations

import json
import logging
from contextlib import closing
from pathlib import Path

from flask import (
    Response,
    current_app,
    url_for,
)

from familydb import export, health, presents
from familydb.store import members as member_store
from familydb.store import memories as memory_store
from familydb.web import (
    auth,
    now,
    views,
)
from familydb.web import status as status_page
from familydb.web.answers import answer
from familydb.web.pages import bp, familydb_app

log = logging.getLogger(__name__)


# The home-screen icon's ground (static/brand/icon-512.png), which the manifest's colours match so
# opening the app is one colour from the icon to the splash.
ICON_GROUND = "#0e1312"


@bp.get("/healthz")
def healthz() -> Response:
    """For a monitor or proxy, open before sign-in: "ok", or 503 and what is wrong (the database
    does not answer, or the scheduled jobs went quiet; familydb/health.py)."""
    ok, words = health.check(familydb_app())
    return Response(f"{words}\n", status=200 if ok else 503, mimetype="text/plain")


@bp.get("/sw.js")
def service_worker() -> Response:
    """The service worker that shows "she has a message" (push.py), served from the top so it
    may show for every page. Open before sign-in, like the manifest: it holds nothing but code."""
    folder = Path(current_app.static_folder or "")
    response = Response((folder / "sw.js").read_text("utf-8"), mimetype="text/javascript")
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.get("/manifest.webmanifest")
def manifest() -> Response:
    """The home-screen manifest. Open before sign-in: a phone asks without the cookie, and it says
    nothing the sign-in page does not."""
    title = familydb_app().settings.web_title
    large = url_for("static", filename="brand/icon-512.png")
    icons = [
        {"src": url_for("static", filename="brand/apple-touch-icon.png"), "sizes": "180x180"},
        {"src": large, "sizes": "512x512"},
        {"src": large, "sizes": "512x512", "purpose": "maskable"},
    ]
    body = {
        "name": title,
        "short_name": title,
        "id": "/",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": ICON_GROUND,
        "theme_color": ICON_GROUND,
        "icons": [{**icon, "type": "image/png"} for icon in icons],
        # Share a link or some words to it from another app (Android): they wait in the chat's
        # box until Send, so nothing is sent by sharing.
        "share_target": {
            "action": "/chat",
            "method": "GET",
            "params": {"title": "title", "text": "text", "url": "url"},
        },
    }
    return Response(json.dumps(body, sort_keys=True), mimetype="application/manifest+json")


@bp.get("/more")
def more() -> str:
    """The phone's menu: what is not in the tab bar, and signing out. It opens from the picture at
    the top of every page and is not a page on a wide screen, where the sidebar holds all of it."""
    return answer("more.html")


@bp.get("/status")
def status() -> str:
    app = familydb_app()
    with closing(app.connect()) as conn:
        return answer("status.html", **status_page.status(app, conn))


@bp.get("/")
def home() -> Response | str:
    """Now, the first screen (web/now.py): the box, her questions, her picks, today's line."""
    return now.show()


@bp.post("/later")
def later() -> Response:
    """Later on a kid's pitch on Now: off this device for a week (web/now.py)."""
    return now.later()


def _download(text: str, name: str, mimetype: str) -> Response:
    log.info("%s was downloaded by %s", name, auth.client_address())
    response = Response(text, mimetype=mimetype)
    response.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/export/plans.ics")
def export_plans() -> Response:
    """The plans as a calendar file any calendar can open (export.py), for a grown-up."""
    app = familydb_app()
    with closing(app.connect()) as conn:
        text = export.plans_ics(conn, app.settings, app.clock.now())
    return _download(text, "familydb-plans.ics", "text/calendar")


@bp.get("/export/ideas.csv")
def export_ideas() -> Response:
    """The ideas as a spreadsheet, without a present kept from whoever asks (presents.py)."""
    with closing(familydb_app().connect()) as conn:
        text = export.ideas_csv(conn, presents.kept_ids(conn, auth.visitor().member))
    return _download(text, "familydb-ideas.csv", "text/csv")


@bp.get("/export/tasks.csv")
def export_tasks() -> Response:
    """The things to do as a spreadsheet, for a grown-up, who sees everybody's."""
    with closing(familydb_app().connect()) as conn:
        text = export.tasks_csv(conn)
    return _download(text, "familydb-to-dos.csv", "text/csv")


@bp.get("/memory")
def memory() -> str:
    app = familydb_app()
    with closing(app.connect()) as conn:
        everything = memory_store.list_all(conn)
        people = member_store.list_all(conn)
    return answer(
        "memory.html",
        **views.memory_page(everything, people, app.clock.today(), app.settings.tzinfo),
        people=people,
        slots=views.slot_map(people),
        kinds=views.MEMORY_KINDS,
    )
