-- Web push (familydb/push.py): each device somebody turned notifications on for, from their own
-- page (/you). Its address at the browser's push service and the keys to encrypt to it; it goes
-- with the person (taken off the list) and when the push service says it has gone.
CREATE TABLE push_subscriptions (
    id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members (id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_ok_at TEXT
);
CREATE INDEX push_subscriptions_member_idx ON push_subscriptions (member_id);
-- The install's own key for signing to push services (VAPID), made once at start. Kept here, not
-- in a file, so a backup and a restore keep every device working; a lost key would silently stop
-- them all.
CREATE TABLE push_key (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    secret TEXT NOT NULL,
    public TEXT NOT NULL,
    created_at TEXT NOT NULL
);
