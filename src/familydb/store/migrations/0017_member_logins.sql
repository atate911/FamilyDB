-- Each person's own password for the web page, so the family no longer shares one. Kept apart
-- from `members`, whose records are read everywhere, down to the family context in the model's
-- prompt, so a hash never travels with a name. A row is somebody who can sign in, while they are
-- on the list as an admin or a member; no row, and they cannot.
CREATE TABLE member_logins (
    member_id INTEGER PRIMARY KEY REFERENCES members (id),
    -- passwords.hash_password: scrypt with its own salt, never the password itself.
    password_hash TEXT NOT NULL,
    -- 1 for a starting password somebody else made up (an admin, or `familydb password`): the
    -- person is asked to choose their own the first time they sign in with it.
    temporary INTEGER NOT NULL DEFAULT 0 CHECK (temporary IN (0, 1)),
    set_at TEXT NOT NULL,
    set_by INTEGER REFERENCES members (id)
);
