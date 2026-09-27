-- Questions a stronger model is asked when a change needs judgement (familydb/judgement.py):
-- filed by code when the change is seen, answered together once a day (a refusal at once), and
-- what the answer was and what code made of it. One question per kind and subject.
CREATE TABLE judgements (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,            -- replacement | refused | lineup | price
    subject TEXT NOT NULL,         -- what it is about: company:model, or company:week
    facts TEXT NOT NULL,           -- JSON: what code knows and the options it allows
    asked_at TEXT NOT NULL,        -- when it was filed
    urgent INTEGER NOT NULL DEFAULT 0,
    tries INTEGER NOT NULL DEFAULT 0,  -- asked without an answer coming back
    answered_at TEXT,
    answer TEXT,                   -- JSON: the model's choices, as code accepted them
    reason TEXT,                   -- its one line on why
    outcome TEXT,                  -- what code did with it, in words
    UNIQUE (kind, subject)
);
CREATE INDEX judgements_open_idx ON judgements (answered_at, asked_at);
