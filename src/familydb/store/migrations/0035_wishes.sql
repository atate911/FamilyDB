-- The kids' wish lists (docs/WISHES.md; the rules are wish_service.py). One row for everything a
-- kid asks for, what the bot turned away included, so the parents see the whole picture.
-- occasion: NULL for her everyday list, else the list it is flagged for. topic: a short key that
-- materially similar asks share (a cat and a dog are both "pet"), which a lockout is counted by.
-- rank: her order within one list, 1 at the top. concern: why a turned-away ask was turned away.
-- locked_until and refusal_rung: set when a parent says not this time. parent_review: whether
-- she may ask a parent about a turned-away one, and whether she has.
CREATE TABLE wishes (
    id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members (id),
    occasion TEXT CHECK (occasion IS NULL OR occasion IN ('christmas', 'birthday')),
    title TEXT NOT NULL,
    title_norm TEXT NOT NULL,
    notes TEXT,
    category TEXT,
    topic TEXT NOT NULL,
    rank INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'granted', 'declined', 'withdrawn', 'turned_away')),
    concern TEXT
        CHECK (concern IS NULL OR concern IN ('rule', 'sibling', 'inappropriate', 'too_many')),
    answer_note TEXT,
    answered_by INTEGER REFERENCES members (id),
    answered_at TEXT,
    locked_until TEXT,
    refusal_rung INTEGER,
    parent_review TEXT NOT NULL DEFAULT 'none'
        CHECK (parent_review IN ('none', 'offered', 'asked')),
    idea_id INTEGER REFERENCES ideas (id),
    source_message_id INTEGER REFERENCES messages (id),
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX wishes_list_idx ON wishes (member_id, occasion, status, rank);
CREATE INDEX wishes_topic_idx ON wishes (member_id, topic);

-- A kid's day with her lists (wish_service.py): how many everyday wishes she asked for, those
-- she moved onto her everyday list from an occasion included, against her daily count; and how
-- many times she moved one, against the cap on excess. day is the family's date, YYYY-MM-DD.
CREATE TABLE wish_days (
    member_id INTEGER NOT NULL REFERENCES members (id),
    day TEXT NOT NULL,
    asks INTEGER NOT NULL DEFAULT 0,
    moves INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (member_id, day)
);
