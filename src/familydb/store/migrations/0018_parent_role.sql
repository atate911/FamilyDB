-- foreign_keys: off
-- The three roles are admin, parent and kid (familydb/roles.py): what used to be called a member
-- is a parent now. A CHECK constraint cannot be changed in place, so the table is rebuilt the way
-- SQLite's own documentation says (lang_altertable.html, "Making Other Kinds Of Table Schema
-- Changes"): with foreign keys off, which the first line asks the migration runner for, because
-- with them on, dropping the old table would run the ON DELETE SET NULL of settings_log and
-- app_settings, and the page's history would forget who changed what. Every id is kept, so
-- everything that points at a member still points at the same person.

-- References to a member already broken before (by hand, with the sqlite3 shell, whose foreign
-- keys are off), so that the check at the end blames the rebuild for nothing it did not do.
CREATE TEMP TABLE members_rebuild_before AS
    SELECT count(*) AS broken FROM pragma_foreign_key_check WHERE "parent" = 'members';

CREATE TABLE members_new (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'parent', 'kid')),
    channel TEXT,
    channel_user_id TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE (channel, channel_user_id)
);
INSERT INTO members_new (id, display_name, role, channel, channel_user_id, active, created_at)
    SELECT id, display_name, CASE role WHEN 'member' THEN 'parent' ELSE role END,
           channel, channel_user_id, active, created_at
    FROM members;
DROP TABLE members;
ALTER TABLE members_new RENAME TO members;
CREATE UNIQUE INDEX members_name_idx ON members (lower(display_name));

-- Nothing that pointed at a member points at nobody now. Were anything to, this insert would
-- break its CHECK, and the whole migration would roll back, the old table with it.
CREATE TEMP TABLE members_rebuild_check (kept INTEGER NOT NULL CHECK (kept = 1));
INSERT INTO members_rebuild_check (kept)
    SELECT (SELECT count(*) FROM pragma_foreign_key_check WHERE "parent" = 'members')
        <= (SELECT broken FROM members_rebuild_before);
DROP TABLE members_rebuild_check;
DROP TABLE members_rebuild_before;
