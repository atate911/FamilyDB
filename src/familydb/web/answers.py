"""Every page of the family's as data (docs/INTERFACE.md section 11).

A page's view builds what the page shows and hands it to `answer`, which draws the template, or,
when the request came through the API (`/api/<path>`, web/api.py), returns the same view-model as
JSON: what the page shows, the box under it (its scope, quick sentences, and what the last
message brought back) and the row of destinations. One answer function, two readers, so the
page and the API cannot disagree. Code only: no page view and no API read asks a model.

What a page's records carry and the page never shows stays out of the JSON: the columns that
reach outside the household (a Telegram id, a chat's id, a calendar's event id), whom a present
is kept from, a person's birthday, sex and look, and anything named like a secret.
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, time
from enum import Enum
from typing import Any

from flask import Response, g, jsonify, render_template, request
from pydantic import BaseModel
from werkzeug.datastructures import ImmutableMultiDict

from familydb.config import Settings

# Set on the request by web/api.py: answer with data, not a page.
API = "api"
# Keys never drawn into an answer, whatever record carries them.
NEVER = frozenset(
    {
        "hidden_from",
        "channel",
        "channel_user_id",
        "chat_id",
        "birth_date",
        "gender",
        "look",
        "operation_key",
        "google_event_id",
        "calendar_id",
        "resume_scope",
        "login",
        "password",
        "password_hash",
        "hash",
        "secret",
        "token",
        "api_key",
        "csrf",
    }
)
_SKIP = object()


def answer(template: str, **context: Any) -> Any:
    """The page, or under the API its view-model as JSON."""
    if not g.get(API):
        return render_template(template, **context)
    return as_json(template.removesuffix(".html"), context)


def as_json(page: str, context: dict[str, Any]) -> Response:
    from familydb.web import chat, shell  # the box and the row, as the frame reads them

    box = chat.current_box()
    row = shell.destinations(shell.frame(chat._app()))
    return jsonify(
        {
            "page": page,
            "answer": plain(context),
            "box": plain({key: value for key, value in box.items() if key != "family"}),
            "row": plain(row),
        }
    )


def plain(value: Any) -> Any:
    """A view-model as JSON can hold it: records as their fields less `NEVER`, dates as ISO text,
    and whatever is neither data nor a record (a function, a connection) left out."""
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return str(value)  # Markup, a str, as plain text
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Enum):
        return plain(value.value)
    if isinstance(value, Settings):
        return _SKIP  # the settings are the settings page's, keys and all
    if isinstance(value, BaseModel):
        return plain(value.model_dump(mode="json"))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return plain(
            {field.name: getattr(value, field.name) for field in dataclasses.fields(value)}
        )
    if isinstance(value, dict):
        kept = {}
        for key, item in value.items():
            name = str(key)
            if name in NEVER or name.startswith("_"):
                continue
            shown = plain(item)
            if shown is not _SKIP:
                kept[name] = shown
        return kept
    if isinstance(value, list | tuple | set | frozenset):
        items = [plain(item) for item in value]
        return [item for item in items if item is not _SKIP]
    return _SKIP


def told(words: str, status: int, **more: Any) -> tuple[Response, int]:
    """An API refusal or failure, said as the page would say it."""
    return jsonify({"error": words, **more}), status


def as_form() -> ImmutableMultiDict[str, str]:
    """What a script sent, as the form the page's own view reads: a JSON object's text, numbers
    and ticks (true is "1", false and null are left out), a list as one value each; a form post
    as it came. From here the request's form is this, so the page's view reads it unchanged."""
    if not request.is_json:
        return request.form
    body = request.get_json(silent=True)
    pairs: list[tuple[str, str]] = []
    for key, given in body.items() if isinstance(body, dict) else ():
        for one in given if isinstance(given, list) else [given]:
            if one is True:
                pairs.append((str(key), "1"))
            elif isinstance(one, str | int | float) and one is not False:
                pairs.append((str(key), str(one)))
    form = ImmutableMultiDict(pairs)
    request.form = form  # type: ignore[misc]
    return form
