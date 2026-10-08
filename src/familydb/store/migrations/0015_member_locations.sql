-- Where a member last shared their location from (Telegram's location button), so "what's near
-- here?" can start from there. One row per member, replaced by the next share; it is used for a
-- few hours and deleted after a day. The engine reads it; the chat model and discovery worker are
-- given the place name and coordinates (docs/DESIGN.md section 10).
CREATE TABLE member_locations (
    member_id INTEGER PRIMARY KEY REFERENCES members(id),
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    live INTEGER NOT NULL DEFAULT 0,
    shared_at TEXT NOT NULL
);
