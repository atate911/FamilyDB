"""Whether an address the family typed is out on the internet, for the places this server reaches
out on a person's say-so: an event calendar (ical.py), a company's chat address (web/settings.py).
SDK-free; resolves the name, so it reaches the network."""

from __future__ import annotations

import ipaddress
import socket


def is_public(host: str) -> bool:
    """Whether every address a host name resolves to is out on the internet: not this machine,
    the home network, a link-local or a reserved address."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    addresses = {info[4][0] for info in infos}
    return bool(addresses) and all(
        ipaddress.ip_address(a.split("%")[0]).is_global for a in addresses
    )
