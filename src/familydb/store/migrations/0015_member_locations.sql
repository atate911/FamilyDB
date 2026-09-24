-- Where a member last shared their location from (Telegram's location button), so "what's near
-- here?" can start from there. One row per member, replaced by the next share; it is used for a
-- few hours and deleted after a day. Never sent to a model: the engine reads it, the model only
-- sees that travel is "from Sam's shared location".
CREATE TABLE member_locations (
    member_id INTEGER PRIMARY KEY REFERENCES members(id),
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    live INTEGER NOT NULL DEFAULT 0,
    shared_at TEXT NOT NULL
);
