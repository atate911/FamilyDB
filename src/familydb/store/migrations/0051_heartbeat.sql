-- When the scheduler last ticked (familydb/health.py): written when `familydb run` starts, by the
-- settings watch every few minutes, and marked stopped when it stops cleanly. /healthz and
-- `familydb health` call a scheduler that should be running and has gone quiet unwell. One row,
-- none until a scheduler first runs, so a page served without one is judged by its database.
CREATE TABLE heartbeat (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    jobs_at TEXT NOT NULL,
    stopped_at TEXT
);
