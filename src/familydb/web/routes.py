"""The pages. Every view reads; nothing here writes to the database."""

from __future__ import annotations

from flask import Blueprint, Response

bp = Blueprint("web", __name__)


@bp.get("/healthz")
def healthz() -> Response:
    """A plain-text liveness check for a monitor or a reverse proxy. No password needed."""
    return Response("ok\n", mimetype="text/plain")
