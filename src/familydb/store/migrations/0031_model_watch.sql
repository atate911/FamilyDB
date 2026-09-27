-- The models each company offers and what they cost, as the daily check last found them
-- (familydb/model_watch.py): from the company's own list for the family's key, and from two public
-- price lists read against each other. prices.py's built-in table is only where a new install
-- starts, and what is used for anything the check has not found.
CREATE TABLE models (
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    listed INTEGER,              -- the company lists it for the family's key: 1, 0, or NULL unasked
    tools INTEGER,               -- it can use tools, as a price list says
    input REAL,                  -- US$ a million tokens read, written and read from the cache;
    output REAL,                 -- NULL when no price is known for it
    cached REAL,
    priced_by TEXT,              -- which lists gave the price in force: litellm, openrouter, both
    retires_on TEXT,             -- the day a list says it goes, YYYY-MM-DD
    released TEXT,               -- the day a list says it came out, YYYY-MM-DD
    first_seen TEXT NOT NULL,    -- the first check that kept it
    last_seen TEXT,              -- the last check a list named it in; NULL when none ever has
    PRIMARY KEY (provider, model)
);

-- What changed, for the status page and the notices: a model new, gone or back for the key, its
-- price moved, a date set for it to go.
CREATE TABLE model_changes (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    what TEXT NOT NULL CHECK (what IN ('new', 'gone', 'back', 'price', 'retiring')),
    before TEXT,
    after TEXT,
    at TEXT NOT NULL
);
CREATE INDEX model_changes_at_idx ON model_changes (at);

-- Each place the check reads (a company's list, a price list): when, whether it answered, and how
-- many checks in a row it has not.
CREATE TABLE model_sources (
    source TEXT PRIMARY KEY,
    checked_at TEXT NOT NULL,
    ok INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    failures INTEGER NOT NULL DEFAULT 0
);

-- The alerts take the new kinds of notice: a model in use gone or going, its price moved, the
-- price lists unreadable or at odds, new models, and a shift in what the calls cost or do. A CHECK
-- cannot be changed in place, so the table is made again; nothing points at it.
CREATE TABLE alerts_new (
    kind TEXT NOT NULL CHECK (
        kind IN ('credit', 'key', 'limit', 'calendar', 'model', 'price', 'prices', 'new', 'shift')
    ),
    subject TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    first_at TEXT NOT NULL,
    last_at TEXT NOT NULL,
    times INTEGER NOT NULL DEFAULT 1,
    told_at TEXT,
    PRIMARY KEY (kind, subject)
);
INSERT INTO alerts_new SELECT kind, subject, detail, first_at, last_at, times, told_at FROM alerts;
DROP TABLE alerts;
ALTER TABLE alerts_new RENAME TO alerts;
