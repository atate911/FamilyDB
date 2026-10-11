-- Her replies a person keeps at hand (docs/INTERFACE.md section 8): a shelf of their own, beside
-- the box on a big screen and at the top of the conversation. Theirs alone, so they go with them;
-- a reply whose words were let go (the tidy job) is not drawn.
CREATE TABLE pins (
    id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members (id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES messages (id) ON DELETE CASCADE,
    pinned_at TEXT NOT NULL,
    UNIQUE (member_id, message_id)
);
CREATE INDEX pins_member_idx ON pins (member_id, pinned_at);
