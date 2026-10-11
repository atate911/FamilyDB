"""The family's pages share one blueprint (`web`, so every endpoint keeps its name) and a few
things every page module needs. Each page family is a module of its own (ideas_page, plans_page,
tasks_page, wishes_page, lists_page); routes.py keeps the frame's own addresses."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, session

from familydb.app import App
from familydb.store import members as member_store
from familydb.web.chat import WHO_KEY

bp = Blueprint("web", __name__)
MAX_ID = 2**63 - 1  # beyond this SQLite raises rather than simply finding nothing


def familydb_app() -> App:
    return current_app.config["FAMILYDB_APP"]


def who_asks(conn: Any) -> dict[str, Any]:
    """What every form needs to say who is doing this."""
    return {
        "family": [member.display_name for member in member_store.list_all(conn)],
        "who": session.get(WHO_KEY),
    }
