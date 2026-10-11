"""What's going down?: dated things near home, found by the app (jobs/happening.py).

This module holds what the rest of the app needs to know about it without the job: its name,
how each source is named, which calendars the settings call for, and what its calls have cost
this month. No network.

The family's name for it is written once, here. Everything they read shows it from `NAME` (the
page and its tab, the settings section, the Status card, her lines through `{page}`), so a
rename is this one line; the code's own names (`happening_*`, the `finds` tables, /happening)
stay neutral and do not move with it. A test holds that nothing else spells it out.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, time
from urllib.parse import urlsplit

from familydb.base.config import Settings
from familydb.base.dates import utc_iso
from familydb.store import calls

NAME = "What's going down?"

# How far ahead every source is read, and what the page and the suggestions look at.
HORIZON_DAYS = 28
# The model calls made for it, recorded under these kinds (agent/gateway.KINDS) and held to
# `happening_budget` a month together.
KINDS = ("scout", "find_feeds")

FEED = "feed"
TICKETMASTER = "ticketmaster"
WEB = "web"
# The source names kept in find_sources: one per calendar, one for Ticketmaster, one for the
# weekly search, and one per home area for the lookup that proposes calendars.
FEED_PREFIX = "feed:"
TICKETMASTER_SOURCE = "ticketmaster"
WEB_SOURCE = "web:near-home"
PROPOSALS_PREFIX = "proposals:"


def feed_urls(settings: Settings) -> list[str]:
    """The calendars to read, in the order the setting lists them."""
    return [line for line in settings.event_feeds.splitlines() if line.strip()]


def feed_source(url: str) -> str:
    return FEED_PREFIX + url


def proposals_source(home_area: str) -> str:
    return PROPOSALS_PREFIX + " ".join(home_area.casefold().split())


def source_kind(source: str) -> str:
    """feed, ticketmaster, web, or proposals."""
    if source.startswith(FEED_PREFIX):
        return FEED
    if source == TICKETMASTER_SOURCE:
        return TICKETMASTER
    if source.startswith(PROPOSALS_PREFIX):
        return "proposals"
    return WEB


def host(url: str) -> str:
    """A calendar by the site it is on, which is what the family know it by."""
    name = urlsplit(url).hostname or url
    return name.removeprefix("www.")


def source_name(source: str) -> str:
    """A source as the pages say it."""
    kind = source_kind(source)
    if kind == FEED:
        return host(source[len(FEED_PREFIX) :])
    if kind == TICKETMASTER:
        return "Ticketmaster"
    if kind == "proposals":
        return "looking for calendars near home"
    return "the weekly search"


def spent_this_month(conn: sqlite3.Connection, settings: Settings, now: datetime) -> float:
    """What its model calls have cost since the first of the family's month."""
    local = now.astimezone(settings.tzinfo)
    start = datetime.combine(local.date().replace(day=1), time(), tzinfo=settings.tzinfo)
    return calls.spent_on(conn, KINDS, since=utc_iso(start))
