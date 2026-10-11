-- Filling in a find (docs/FINDS.md): when a lookup last tried it, and what it said when it found
-- nothing to keep, so the evening's fills move on to the next rather than trying one again. The
-- place it found goes in `place_id`, which 0061 made.
ALTER TABLE finds ADD COLUMN filled_at TEXT;
ALTER TABLE finds ADD COLUMN fill_note TEXT;
