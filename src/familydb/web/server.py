"""Serving the page: in the foreground for `familydb web`, on a thread inside `familydb run`.

Waitress, not Flask's development server, and never in debug mode. The bot's own thread must
survive a page that cannot start, so `serve_in_thread` reports the problem and returns nothing
rather than raising.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from waitress import create_server as _create_server

from familydb.app import App
from familydb.errors import ConfigError, FamilyDBError
from familydb.web import create_app

log = logging.getLogger(__name__)

THREAD_NAME = "familydb-web"
IDENT = "FamilyDB"


def create_server(app: App) -> Any:
    """A waitress server with the socket already bound, so a clash is reported here."""
    settings = app.settings
    return _create_server(
        create_app(app), host=settings.web_host, port=settings.web_port, ident=IDENT
    )


def address(app: App) -> str:
    host = app.settings.web_host or "127.0.0.1"
    shown = "localhost" if host in {"0.0.0.0", "::"} else host
    return f"http://{shown}:{app.settings.web_port}/"


def serve(app: App) -> None:
    """Serve until interrupted. Raises ConfigError when the settings forbid it."""
    server = create_server(app)
    log.info("serving the web page at %s", address(app))
    server.run()


def serve_in_thread(app: App) -> Callable[[], None] | None:
    """Start the page on a daemon thread. Returns how to stop it, or None if it did not start."""
    try:
        server = create_server(app)
    except ConfigError as exc:
        log.error("the web page is not serving: %s", exc)
        return None
    except (OSError, FamilyDBError) as exc:
        log.error("could not serve the web page on %s: %s", address(app), exc)
        return None
    thread = threading.Thread(target=server.run, name=THREAD_NAME, daemon=True)
    thread.start()
    log.info("serving the web page at %s", address(app))
    return server.close
