-- Her picks for a moment (familydb/picks.py): the set shown on Now as "What about…", made ahead
-- by the picks job and read by the page, so no page view asks a model. One row a set: whose it is
-- (NULL for the family's, a kid's own by member), the days it is for, the line that drove it, the
-- picks themselves (kind, when, title, why, idea or find) and when it goes stale.
CREATE TABLE pick_sets (
    id INTEGER PRIMARY KEY,
    member_id INTEGER REFERENCES members (id),
    window TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    header TEXT,
    picks TEXT NOT NULL CHECK (json_valid(picks)),
    made_at TEXT NOT NULL,
    stale_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'code'
);
CREATE INDEX pick_sets_made_idx ON pick_sets (member_id, window, made_at);
