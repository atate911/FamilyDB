-- Her back pocket (docs/FINDS.md): what the app found keeps more than a dated event. A find may
-- be a place to go any time (no starts_at), says who it is for and why it was found, and keeps
-- what became of it: recommended, saved as an idea, planned, or passed on as "not for us". Where
-- it came from is its kind: a calendar ('feed'), Ticketmaster, scouting ('web'), or a search made
-- while answering somebody ('request'). The facts a lookup fills in, the nightly judgement and
-- when it was last put forward are kept here too, so this is the one rebuild. A NOT NULL and a
-- CHECK cannot be changed in place, so the table is made again; nothing points at it, so foreign
-- keys may stay on, and every row and id is kept.

CREATE TEMP TABLE finds_rebuild_before AS SELECT count(*) AS kept FROM finds;

CREATE TABLE finds_new (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('feed', 'ticketmaster', 'web', 'request')),
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    starts_at TEXT,  -- NULL: any time, a place rather than an event
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
    -- Who it is for, as an idea's participants ("whole family", "grown-ups", a name).
    participants TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(participants)),
    why TEXT,  -- one line: why it suits them, as the search said
    state TEXT NOT NULL DEFAULT 'new'
        CHECK (state IN ('new', 'recommended', 'saved', 'planned', 'passed')),
    idea_id INTEGER REFERENCES ideas (id),  -- the idea it became when saved
    place_id INTEGER REFERENCES places (id),  -- its place, once filled in
    -- The facts a lookup fills in, as an idea's, so a find is checked as an idea is.
    setting TEXT CHECK (setting IS NULL OR setting IN ('indoor', 'outdoor', 'either')),
    cost_level INTEGER CHECK (cost_level IS NULL OR cost_level BETWEEN 0 AND 4),
    duration_min INTEGER,
    min_age INTEGER,
    max_age INTEGER,
    needs_booking INTEGER,
    -- The nightly judgement: why it is worth putting forward, and when.
    judged_at TEXT,
    judged_why TEXT,
    judged_when TEXT,
    put_from TEXT,
    put_until TEXT,
    -- When it was last put forward, and for which days, so it is not again within a week.
    put_forward_at TEXT,
    put_forward_window TEXT,
    saved_at TEXT,
    passed_at TEXT,
    passed_by INTEGER REFERENCES members (id),
    passed_why TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    gone INTEGER NOT NULL DEFAULT 0,
    UNIQUE (source, external_id)
);
INSERT INTO finds_new (
    id, source, kind, external_id, title, starts_at, ends_at, all_day, venue, address, lat, lon,
    url, price_note, summary, category, first_seen_at, last_seen_at, gone
)
    SELECT id, source, kind, external_id, title, starts_at, ends_at, all_day, venue, address, lat,
           lon, url, price_note, summary, category, first_seen_at, last_seen_at, gone
    FROM finds;
DROP TABLE finds;
ALTER TABLE finds_new RENAME TO finds;
CREATE INDEX finds_starts_idx ON finds (starts_at);
CREATE INDEX finds_state_idx ON finds (state);

-- Every row came across. Were one lost, this insert would break its CHECK, and the whole
-- migration would roll back, the old table with it.
CREATE TEMP TABLE finds_rebuild_check (kept INTEGER NOT NULL CHECK (kept = 1));
INSERT INTO finds_rebuild_check (kept)
    SELECT (SELECT count(*) FROM finds) = (SELECT kept FROM finds_rebuild_before);
DROP TABLE finds_rebuild_check;
DROP TABLE finds_rebuild_before;
