-- Where the bot's incremental sync with each Google calendar stands: the token Google handed
-- back last time, so the next check asks only for what changed since, in one request, instead of
-- asking about every plan on its own. Losing it costs one full read of the calendar.
CREATE TABLE calendar_sync_state (
    calendar_id TEXT PRIMARY KEY,
    sync_token TEXT NOT NULL,
    synced_at TEXT NOT NULL
);
