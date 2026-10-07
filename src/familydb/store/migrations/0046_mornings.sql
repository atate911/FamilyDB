-- The morning message (jobs/morning.py): at most one a day in each chat, with the day's plans,
-- reminders and deadlines, what is due tomorrow, a reminder nobody acted on, and once a week what
-- has waited. Kept so it is sent once (a restart in the morning sends no second), and with the
-- parts it had, which the Messages page counts.
CREATE TABLE mornings (
    id INTEGER PRIMARY KEY,
    channel TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    day TEXT NOT NULL,
    message_id INTEGER REFERENCES messages (id) ON DELETE SET NULL,
    parts TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(parts)),
    created_at TEXT NOT NULL,
    UNIQUE (channel, chat_id, day)
);
CREATE INDEX mornings_created_idx ON mornings (created_at);
-- A reminder that went and was neither done nor snoozed is chased once, the next morning.
ALTER TABLE reminders ADD COLUMN chased_at TEXT;
-- A dated idea ending this week, with a free day for it, is brought up once.
ALTER TABLE ideas ADD COLUMN nudged_at TEXT;
