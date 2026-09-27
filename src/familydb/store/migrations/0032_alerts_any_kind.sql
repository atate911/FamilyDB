-- The kinds of alert are the code's to name (alerts.KINDS), as they keep growing: a company
-- refusing a request it gives no reason code can read, and a part of a request a company no
-- longer takes. So the table is made again without a CHECK on the kind; nothing points at it.
CREATE TABLE alerts_new (
    kind TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    first_at TEXT NOT NULL,
    last_at TEXT NOT NULL,
    times INTEGER NOT NULL DEFAULT 1,
    told_at TEXT,
    PRIMARY KEY (kind, subject)
);
INSERT INTO alerts_new SELECT kind, subject, detail, first_at, last_at, times, told_at FROM alerts;
DROP TABLE alerts;
ALTER TABLE alerts_new RENAME TO alerts;
