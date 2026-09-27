-- What only an admin can fix, while it lasts: a company out of credit or refusing its key, the
-- day's spending limit used up, Google no longer letting the bot in (familydb/alerts.py). One row
-- for each kind of trouble and what it is about (the company, the day), kept until it is seen to
-- work again, with when admins were last told on Telegram so they are not told every minute.
CREATE TABLE alerts (
    kind TEXT NOT NULL CHECK (kind IN ('credit', 'key', 'limit', 'calendar')),
    subject TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    first_at TEXT NOT NULL,
    last_at TEXT NOT NULL,
    times INTEGER NOT NULL DEFAULT 1,
    told_at TEXT,
    PRIMARY KEY (kind, subject)
);
