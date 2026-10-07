-- What the stronger call chose for a suggestion (suggest/choose.py), when it chose: the picks in
-- order with their reasons, and a line on the whole. Null when the engine's own order was used.
-- Read back so the next question does not repeat what was picked a few days ago.
ALTER TABLE suggestions ADD COLUMN picks TEXT CHECK (picks IS NULL OR json_valid(picks));
