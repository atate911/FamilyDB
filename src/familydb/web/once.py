"""Forms that do their work once however often they arrive (double click, resend, back button).
Every such form carries a token drawn with the page; the first post with it does the work and
remembers where it redirected, and a later post with the same token and session is sent there
without doing anything. One that arrives while the first works waits for it. The server does
this, not a script, because every form must work with scripts off.

The guard is in memory. Calendar and task creation also carry the form identity into the durable
operation log, which survives a restart."""

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
MAX_REMEMBERED = 2048
WAIT_SECONDS = 30


def once_token() -> str:
    """A fresh token for one drawing of one form."""
    return secrets.token_urlsafe(16)


@dataclass
class _Sent:
    done: threading.Event = field(default_factory=threading.Event)
    location: str | None = None


class Once:
    def __init__(self) -> None:
        self._seen: OrderedDict[str, _Sent] = OrderedDict()
        self._lock = threading.Lock()

    def claim(self, key: str) -> tuple[_Sent, bool]:
        """The record for this token, and whether this caller is the first."""
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

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = request.form.get(FIELD, "")
        if not token or len(token) > MAX_TOKEN:
            return view(*args, **kwargs)  # a form drawn without a token: nothing to match
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
    """The path and query of a full URL."""
    parts = urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "")
