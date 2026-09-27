-- A link an admin makes for somebody on the family list: opened on their phone, its Start links
-- their Telegram to them (familydb/family.py `invite` and `accept_invite`). Only a hash of the
-- code is kept; the code itself is in the link, shown once. One to a person, since a new one
-- replaces theirs; used once and then gone; past its time it opens nothing.
CREATE TABLE telegram_invites (
    code_hash TEXT PRIMARY KEY,
    member_id INTEGER NOT NULL UNIQUE REFERENCES members (id),
    made_by INTEGER REFERENCES members (id),
    made_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
