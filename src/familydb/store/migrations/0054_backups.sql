-- Each backup `familydb db backup` wrote (the nightly one from cron, or by hand), whether its copy
-- passed SQLite's quick_check, and when: the hourly upkeep (familydb/upkeep.py) tells admins when
-- none has worked for a day and a half, once one ever has, and Status and `familydb doctor` say
-- when the last good one was.
CREATE TABLE backups (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    ok INTEGER NOT NULL,
    detail TEXT,
    made_at TEXT NOT NULL
);
CREATE INDEX backups_made_idx ON backups (ok, made_at);
