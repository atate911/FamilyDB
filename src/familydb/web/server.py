"""Serving the page with waitress: in the foreground for `familydb web`, on a thread inside
`familydb run`, where a page that cannot start must not take the bot down."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from waitress import create_server as _create_server

from familydb.app import App
from familydb.errors import ConfigError, FamilyDBError
from familydb.web import MAX_BODY_BYTES, create_app

log = logging.getLogger(__name__)

THREAD_NAME = "familydb-web"
IDENT = "FamilyDB"


# Waitress reads these only from the proxy it is told to trust and strips them from anyone else.
PROXY_HEADERS = frozenset({"x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"})


def proxy_options(settings: Any) -> dict[str, Any]:
    """How far to believe the forwarding headers: not at all unless WEB_TRUST_PROXY is set.

    This must be the server's job, not a Flask middleware's: waitress strips the headers from any
    untrusted peer before the app runs, so the app would see none, the Origin check would refuse
    every sign-in and the family would share one lockout.

    On loopback the proxy is this machine. Bound to every interface is a container, where the
    proxy's address is unknown; the compose file publishes the port to the host's loopback only,
    so nothing but the proxy can reach it to lie.
    """
    if not settings.web_trust_proxy:
        return {}
    local = settings.web_host.strip().lower() in {"127.0.0.1", "localhost", "::1"}
    return {
        "trusted_proxy": "127.0.0.1" if local else "*",
        "trusted_proxy_count": 1,
        "trusted_proxy_headers": set(PROXY_HEADERS),
    }


def create_server(app: App) -> Any:
    """A waitress server with the socket already bound, so a clash is reported here."""
    settings = app.settings
    return _create_server(
        create_app(app),
        host=settings.web_host,
        port=settings.web_port,
        ident=IDENT,
        # Flask refuses an oversize body only after waitress has read it (default 1 GB).
        max_request_body_size=MAX_BODY_BYTES,
        **proxy_options(settings),
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
    except (OSError, ValueError, FamilyDBError) as exc:
        # ValueError: waitress rejects a host it cannot parse, such as an empty WEB_HOST.
        log.error("could not serve the web page on %s: %s", address(app), exc)
        return None
    thread = threading.Thread(target=server.run, name=THREAD_NAME, daemon=True)
    thread.start()
    log.info("serving the web page at %s", address(app))
    return server.close
