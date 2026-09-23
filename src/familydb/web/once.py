"""Forms that do their thing once, however many times they arrive.

A double click, a refresh that resends, the back button and Send again: each posts the same
form twice. For most forms that is harmless, but not for these: twice "put it on the calendar"
is two events on everybody's phone, twice "record how it went" counts the visit twice. The
content policy forbids the script that would disable a button after one press, so the page
does it on the other side.

Every such form carries a token drawn fresh when the page is drawn. The first post with a token
does the work and remembers where it sent the browser; any later post with the same token,
from the same session, is sent there too, without doing anything. One that arrives while the
first is still working waits for it.

This guard is in memory and handles rapid repeats. Calendar creation additionally carries the
form identity into the durable calendar operation log, so it survives a restart or lost reply.
Other forms still have only this process-local double-submit guard.
"""

from __future__ import annotations

import secrets
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any
from urllib.parse import urlsplit

from flask import current_app, redirect, request, session

from familydb.web.auth import CSRF_KEY, safe_next

FIELD = "once"
MAX_TOKEN = 64
# Enough for a family's afternoon of forms; the oldest are forgotten first.
MAX_REMEMBERED = 2048
# How long a duplicate waits for the first to finish before being sent back where it came from.
WAIT_SECONDS = 30


def once_token() -> str:
    """A fresh token for one drawing of one form. Used as a template global."""
    return secrets.token_urlsafe(16)


@dataclass
class _Sent:
    done: threading.Event = field(default_factory=threading.Event)
    location: str | None = None


class Once:
    """The tokens this process has seen, and where each one sent the browser."""

    def __init__(self) -> None:
        self._seen: OrderedDict[str, _Sent] = OrderedDict()
        self._lock = threading.Lock()

    def claim(self, key: str) -> tuple[_Sent, bool]:
        """The record for this token, and whether this caller is the first to bring it."""
        with self._lock:
            sent = self._seen.get(key)
            if sent is not None:
                return sent, False
            sent = _Sent()
            self._seen[key] = sent
            while len(self._seen) > MAX_REMEMBERED:
                self._seen.popitem(last=False)
            return sent, True


def once(view: Callable[..., Any]) -> Callable[..., Any]:
    """Run a form's view the first time its token arrives; send repeats where the first went."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = request.form.get(FIELD, "")
        if not token or len(token) > MAX_TOKEN:
            return view(*args, **kwargs)  # a page drawn before this existed: nothing to match
        registry: Once = current_app.config["FAMILYDB_ONCE"]
        # Keyed on the session too, so a token only ever matches the browser it was drawn for.
        sent, first = registry.claim(f"{session.get(CSRF_KEY, '')}:{token}")
        if not first:
            sent.done.wait(WAIT_SECONDS)
            back = safe_next(request.referrer and _path(request.referrer))
            return redirect(sent.location or back or "/")
        response = None
        try:
            response = view(*args, **kwargs)
            return response
        finally:
            if response is not None and getattr(response, "status_code", 200) in (301, 302, 303):
                sent.location = response.headers.get("Location")
            sent.done.set()

    return wrapper


def _path(url: str) -> str:
    """The path and query of a full URL, for sending a browser back to a page on this site."""
    parts = urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "")
