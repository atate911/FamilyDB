-- A form drawn again after a lost reply takes over the attempt it found unfinished. Its own
-- identity is linked to that attempt here for good, so sending that form again, even after a
-- restart, finds the finished plan instead of asking Google for a second event.
CREATE TABLE calendar_links (
    operation_key TEXT PRIMARY KEY,
    adopted_key TEXT NOT NULL
);
