-- Settings the family can change from the web page, on top of whatever the environment says.
-- One row per setting. The value is JSON so a number stays a number and a flag stays a flag.
CREATE TABLE app_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL CHECK (json_valid(value)),
    updated_at  TEXT NOT NULL,
    updated_by  INTEGER REFERENCES members(id) ON DELETE SET NULL
);

-- Every change, so a setting that turns out to be wrong can be traced to when and to whom.
-- A secret's value is never written here, only the fact that it changed.
CREATE TABLE settings_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT,
    secret      INTEGER NOT NULL DEFAULT 0,
    changed_at  TEXT NOT NULL,
    changed_by  INTEGER REFERENCES members(id) ON DELETE SET NULL,
    source      TEXT NOT NULL DEFAULT 'web'
);

CREATE INDEX idx_settings_log_time ON settings_log (changed_at DESC);
