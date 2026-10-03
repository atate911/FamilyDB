-- Asking Google for the same event twice is prevented by one table now, not three.
--
-- `calendar_creations` keeps an attempt's event id before Google is contacted, so a retry after
-- a crash or a lost answer asks for the same event. Whether the attempt finished is no longer
-- stored beside it: it is finished when a plan holds that event id. So the saved `result` goes,
-- and with it `calendar_unfinished` (an attempt a browser session left without a plan, now found
-- by `resume_key` on the attempt itself) and `calendar_links` (a form that took such an attempt
-- over, now a row of its own pointing at the same event, which is why `event_id` is no longer
-- unique).
CREATE TABLE calendar_creations_new (
    operation_key TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    resume_key TEXT
);
INSERT INTO calendar_creations_new(operation_key, event_id, resume_key)
    SELECT c.operation_key, c.event_id,
           (SELECT u.resume_key FROM calendar_unfinished u WHERE u.event_id = c.event_id)
    FROM calendar_creations c;
INSERT OR IGNORE INTO calendar_creations_new(operation_key, event_id)
    SELECT l.operation_key, c.event_id
    FROM calendar_links l JOIN calendar_creations c ON c.operation_key = l.adopted_key;
DROP TABLE calendar_creations;
ALTER TABLE calendar_creations_new RENAME TO calendar_creations;
DROP TABLE calendar_unfinished;
DROP TABLE calendar_links;
CREATE INDEX calendar_creations_resume_idx ON calendar_creations(resume_key)
    WHERE resume_key IS NOT NULL;
-- Which plan holds an event: asked for each attempt, and for every change Google reports.
CREATE INDEX plans_google_event_idx ON plans(google_event_id) WHERE google_event_id IS NOT NULL;
