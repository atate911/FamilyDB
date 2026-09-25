-- What the family has told the bot about itself: tastes, needs, routines (docs/MEMORY.md).
-- Written by the chat model's `remember` tool during a turn it was having anyway, or from the
-- memory page; chosen for each message by code (familydb/memory.py). A row is never deleted:
-- a corrected one is marked replaced, pointing at what replaced it, and a forgotten one keeps
-- its words, marked, so the same thing cannot come back from what was said before.
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    member_id INTEGER REFERENCES members (id),  -- who it is about; NULL for the whole family
    category TEXT NOT NULL
        CHECK (category IN ('food', 'activities', 'places', 'health', 'routine', 'other')),
    fact TEXT NOT NULL,
    fact_norm TEXT NOT NULL,  -- casefolded and without punctuation, for the duplicate check
    firm INTEGER NOT NULL DEFAULT 0,  -- a requirement (an allergy, a must, a never), not a taste
    inferred INTEGER NOT NULL DEFAULT 0,  -- read between the lines rather than said outright
    until TEXT,  -- the last day it applies, for something temporary; NULL for no end
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'replaced', 'forgotten')),
    replaced_by INTEGER REFERENCES memories (id),
    source_message_id INTEGER REFERENCES messages (id),  -- NULL when typed on the page
    said_by INTEGER REFERENCES members (id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    forgotten_at TEXT,
    forgotten_by INTEGER REFERENCES members (id)
);
CREATE INDEX memories_status_idx ON memories (status);
CREATE INDEX memories_norm_idx ON memories (fact_norm);
