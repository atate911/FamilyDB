-- FamilyDB initial schema.
-- Instants are UTC ISO 'YYYY-MM-DDTHH:MM:SSZ'; dates are 'YYYY-MM-DD'; plan times carry an offset.
-- JSON columns are written only through familydb.store.db.to_json (sorted keys, compact).

CREATE TABLE members (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member', 'kid')),
    channel TEXT,
    channel_user_id TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE (channel, channel_user_id)
);
CREATE UNIQUE INDEX members_name_idx ON members (lower(display_name));

CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    channel TEXT NOT NULL,
    channel_update_id TEXT,
    chat_id TEXT NOT NULL,
    member_id INTEGER REFERENCES members (id),
    direction TEXT NOT NULL CHECK (direction IN ('in', 'out')),
    text TEXT NOT NULL,
    received_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'processed', 'failed')),
    actions TEXT CHECK (actions IS NULL OR json_valid(actions)),
    error TEXT,
    reply_to INTEGER REFERENCES messages (id),
    processed_at TEXT,
    UNIQUE (channel, channel_update_id)
);
CREATE INDEX messages_chat_idx ON messages (chat_id, id);
CREATE INDEX messages_status_idx ON messages (status);

CREATE TABLE places (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    summary TEXT,
    address TEXT,
    lat REAL,
    lon REAL,
    website TEXT,
    booking_url TEXT,
    phone TEXT,
    hours TEXT CHECK (hours IS NULL OR json_valid(hours)),
    price_note TEXT,
    travel_minutes INTEGER,
    travel_km REAL,
    source_urls TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(source_urls)),
    last_checked_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE ideas (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    title_norm TEXT NOT NULL,
    description TEXT,
    participants TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(participants)),
    location_name TEXT,
    url TEXT,
    tags TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(tags)),
    setting TEXT NOT NULL DEFAULT 'either' CHECK (setting IN ('indoor', 'outdoor', 'either')),
    seasons TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(seasons)),
    weather TEXT NOT NULL DEFAULT 'any' CHECK (weather IN ('any', 'dry', 'warm', 'snow')),
    duration_min INTEGER,
    duration_max INTEGER,
    cost_level INTEGER CHECK (cost_level IS NULL OR cost_level BETWEEN 0 AND 4),
    needs_booking INTEGER NOT NULL DEFAULT 0,
    lead_time_days INTEGER,
    status TEXT NOT NULL DEFAULT 'idea' CHECK (status IN ('idea', 'planned', 'done', 'dropped')),
    place_id INTEGER REFERENCES places (id),
    enrichment TEXT NOT NULL DEFAULT 'pending'
        CHECK (enrichment IN ('pending', 'done', 'failed', 'skipped')),
    enriched_at TEXT,
    suggested_by INTEGER REFERENCES members (id),
    source_message_id INTEGER REFERENCES messages (id),
    times_done INTEGER NOT NULL DEFAULT 0,
    last_done_at TEXT,
    avg_rating REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX ideas_status_idx ON ideas (status);
CREATE INDEX ideas_kind_idx ON ideas (kind);
CREATE INDEX ideas_title_norm_idx ON ideas (title_norm);

CREATE TABLE plans (
    id INTEGER PRIMARY KEY,
    idea_id INTEGER REFERENCES ideas (id),
    google_event_id TEXT,
    calendar_id TEXT,
    title TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT,
    all_day INTEGER NOT NULL DEFAULT 0,
    location TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('confirmed', 'tentative', 'cancelled')),
    created_by INTEGER REFERENCES members (id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX plans_start_idx ON plans (start);

CREATE TABLE outcomes (
    id INTEGER PRIMARY KEY,
    idea_id INTEGER REFERENCES ideas (id),
    plan_id INTEGER REFERENCES plans (id),
    happened_on TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 10),
    would_repeat INTEGER,
    notes TEXT,
    recorded_by INTEGER REFERENCES members (id),
    created_at TEXT NOT NULL
);
CREATE INDEX outcomes_idea_idx ON outcomes (idea_id);

CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY,
    asked_by INTEGER REFERENCES members (id),
    asked_at TEXT NOT NULL,
    window_start TEXT,
    window_end TEXT,
    candidates TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(candidates)),
    web_finds TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(web_finds)),
    reply_message_id INTEGER REFERENCES messages (id)
);

-- Audit: every tool call and every model call, tied to the message that caused it.
CREATE TABLE tool_calls (
    id INTEGER PRIMARY KEY,
    message_id INTEGER REFERENCES messages (id),
    iteration INTEGER NOT NULL,
    tool_use_id TEXT,
    tool_name TEXT NOT NULL,
    input TEXT NOT NULL CHECK (json_valid(input)),
    output TEXT,
    is_error INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    created_at TEXT NOT NULL
);
CREATE INDEX tool_calls_message_idx ON tool_calls (message_id);

CREATE TABLE llm_calls (
    id INTEGER PRIMARY KEY,
    message_id INTEGER REFERENCES messages (id),
    iteration INTEGER NOT NULL,
    model TEXT NOT NULL,
    served_model TEXT,
    request_id TEXT,
    stop_reason TEXT,
    input_tokens INTEGER,
    cache_creation_input_tokens INTEGER,
    cache_read_input_tokens INTEGER,
    output_tokens INTEGER,
    duration_ms INTEGER,
    created_at TEXT NOT NULL
);
CREATE INDEX llm_calls_message_idx ON llm_calls (message_id);

-- Full-text search over ideas: an external-content table kept in sync by triggers.
CREATE VIRTUAL TABLE ideas_fts USING fts5(
    title, description, tags, location_name,
    content='ideas', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER ideas_ai AFTER INSERT ON ideas BEGIN
    INSERT INTO ideas_fts (rowid, title, description, tags, location_name)
    VALUES (new.id, new.title, new.description, new.tags, new.location_name);
END;
CREATE TRIGGER ideas_ad AFTER DELETE ON ideas BEGIN
    INSERT INTO ideas_fts (ideas_fts, rowid, title, description, tags, location_name)
    VALUES ('delete', old.id, old.title, old.description, old.tags, old.location_name);
END;
CREATE TRIGGER ideas_au AFTER UPDATE ON ideas BEGIN
    INSERT INTO ideas_fts (ideas_fts, rowid, title, description, tags, location_name)
    VALUES ('delete', old.id, old.title, old.description, old.tags, old.location_name);
    INSERT INTO ideas_fts (rowid, title, description, tags, location_name)
    VALUES (new.id, new.title, new.description, new.tags, new.location_name);
END;
