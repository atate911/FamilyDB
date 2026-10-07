-- What is on near home, as the family's sources list it (jobs/happening.py): calendars the
-- family keeps, Ticketmaster, and a weekly search. Read by code, kept here, and offered in the
-- suggestions and on a page of its own. Nothing here points at a member.

-- One dated thing, as one source lists it. `starts_at` is the family's wall time, a day
-- (YYYY-MM-DD) or a minute (YYYY-MM-DDTHH:MM), so text order is time order; an all-day thing
-- ends on its last day, as a plan's last day is kept. A thing that drops off its source's list
-- is marked gone rather than deleted, so the next read that lists it again brings it back.
CREATE TABLE finds (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('feed', 'ticketmaster', 'web')),
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    all_day INTEGER NOT NULL DEFAULT 0,
    venue TEXT,
    address TEXT,
    lat REAL,
    lon REAL,
    url TEXT,
    price_note TEXT,
    summary TEXT,
    category TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    gone INTEGER NOT NULL DEFAULT 0,
    UNIQUE (source, external_id)
);
CREATE INDEX finds_starts_idx ON finds (starts_at);

-- Each source, as model_sources is for the daily check: when it was last read, whether it
-- answered, how many reads in a row it has not, and how many things it listed.
CREATE TABLE find_sources (
    source TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    ok INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    failures INTEGER NOT NULL DEFAULT 0,
    found INTEGER NOT NULL DEFAULT 0
);

-- Calendars the app found near home and offers for an admin to tick. Which are ticked is the
-- `event_feeds` setting, not this table, so the settings page never writes here. `misses` is how
-- many proposal runs in a row the address did not read as a calendar; at three it is let go.
CREATE TABLE feed_proposals (
    url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    home_area TEXT NOT NULL,
    events INTEGER NOT NULL DEFAULT 0,
    found_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    misses INTEGER NOT NULL DEFAULT 0
);
