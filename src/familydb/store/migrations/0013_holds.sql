-- A paid call in flight sets aside its estimated cost here, under one short write transaction,
-- and gives it back when the call is recorded. The limit counts both, so no lock is held over
-- the network. A hold a crash left behind stops counting once it is older than any call.
CREATE TABLE spend_holds (
    id INTEGER PRIMARY KEY,
    cost_usd REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX reminders_task ON reminders(task_id);
-- A calendar event the page asked Google for whose answer never came back, by browser session
-- and event, so asking again from a freshly drawn form finds that event instead of adding one.
CREATE TABLE calendar_unfinished (
    resume_key TEXT PRIMARY KEY,
    event_id TEXT NOT NULL
);
