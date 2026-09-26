"""The key that signs the web session cookie.

Set WEB_SECRET_KEY to pin it. Otherwise one is generated once and kept beside the database, so
a restart does not sign everyone out. Read it through `session_secret` and replace it through
`rotate`, never directly.
"""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

from familydb.config import Settings

log = logging.getLogger(__name__)

SECRET_FILE = "web_secret"
KEY_BYTES = 32


def secret_path(settings: Settings) -> Path:
    """Where the generated key lives: beside the database file."""
    return Path(settings.familydb_path).expanduser().resolve().parent / SECRET_FILE


def _stored(path: Path) -> str | None:
    try:
        return path.read_text("utf-8").strip() or None
    except OSError:
        return None


def session_secret(settings: Settings) -> str:
    """The configured key, the stored one, or a fresh one written with owner-only permissions."""
    if settings.web_secret_key:
        return settings.web_secret_key
    path = secret_path(settings)
    existing = _stored(path)
    if existing:
        return existing

    key = secrets.token_urlsafe(KEY_BYTES)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # O_EXCL so two processes starting at once cannot overwrite each other's key.
        handle = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    except OSError as exc:
        # Either another process won the race, or there is nowhere to keep the key.
        raced = _stored(path)
        if raced:
            return raced
        log.warning(
            "could not store a web session key at %s (%s); using a temporary one, so logins "
            "will not survive a restart. Set WEB_SECRET_KEY to fix this.",
            path,
            exc,
        )
        return key
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(key)
    log.info("generated a web session key at %s", path)
    return key


def rotate(settings: Settings) -> str | None:
    """Replace the stored key, which signs every session and every known browser out at once.

    None when the key is pinned by WEB_SECRET_KEY, which only the file it came from can change.
    Another process serving the page keeps the old key until it restarts.
    """
    if settings.web_secret_key:
        return None
    path = secret_path(settings)
    key = secrets.token_urlsafe(KEY_BYTES)
    fresh = path.with_name(path.name + ".new")
    handle = os.open(fresh, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(key)
    os.replace(fresh, path)
    log.warning("the web session key was replaced: everyone is signed out")
    return key
