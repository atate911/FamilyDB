"""Whether an address the family typed is out on the internet, for the places this server reaches
out on a person's say-so: an event calendar (ical.py), a company's chat address (web/settings.py).
SDK-free; resolves the name, so it reaches the network."""

from __future__ import annotations

import ipaddress
import socket
from typing import Literal

Reach = Literal["public", "private", "unresolved"]


def classify(host: str) -> Reach:
    """Where a host name leads: out on the internet, to this machine or the home network (a
    link-local or reserved address too), or nowhere this server can find."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return "unresolved"
    addresses = {info[4][0] for info in infos}
    if not addresses:
        return "unresolved"
    public = all(ipaddress.ip_address(a.split("%")[0]).is_global for a in addresses)
    return "public" if public else "private"


def is_public(host: str) -> bool:
    """Whether every address a host name resolves to is out on the internet."""
    return classify(host) == "public"
