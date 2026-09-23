CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    owner_id INTEGER REFERENCES members(id),
    due_at TEXT,
    preferred_window TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','done','cancelled')),
    revision INTEGER NOT NULL DEFAULT 1,
    operation_key TEXT UNIQUE,
    channel TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    remind_at TEXT NOT NULL,
    message_id INTEGER UNIQUE REFERENCES messages(id),
    cancelled_at TEXT
);
CREATE INDEX reminders_due ON reminders(remind_at) WHERE cancelled_at IS NULL;
ALTER TABLE messages ADD COLUMN cancelled_at TEXT;
