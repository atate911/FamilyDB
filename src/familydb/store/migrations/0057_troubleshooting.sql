-- What the models were sent and said, in words, for an admin to read when something is wrong
-- (store/ai_texts.py). The system prompt and the tool list are the same from one call to the next,
-- so they are kept once, by hash, in ai_blobs; each call keeps only what is its own.
CREATE TABLE ai_blobs (
    hash TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE ai_texts (
    id INTEGER PRIMARY KEY,
    call_id INTEGER REFERENCES llm_calls (id),
    message_id INTEGER REFERENCES messages (id),
    turn TEXT,
    iteration INTEGER NOT NULL DEFAULT 1,
    kind TEXT,
    about TEXT,
    provider TEXT,
    model TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('answered', 'failed')),
    error TEXT,
    system_hash TEXT REFERENCES ai_blobs (hash),
    tools_hash TEXT REFERENCES ai_blobs (hash),
    request TEXT NOT NULL,
    reply TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX ai_texts_created_idx ON ai_texts (created_at);
CREATE INDEX ai_texts_message_idx ON ai_texts (message_id);
CREATE INDEX ai_texts_turn_idx ON ai_texts (turn);
CREATE INDEX ai_texts_call_idx ON ai_texts (call_id);

-- Warnings and errors the program logged, said once with a count (store/problems.py).
CREATE TABLE problems (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    detail TEXT,
    count INTEGER NOT NULL DEFAULT 1,
    first_at TEXT NOT NULL,
    last_at TEXT NOT NULL
);
CREATE INDEX problems_key_idx ON problems (key, last_at);
CREATE INDEX problems_last_idx ON problems (last_at);
