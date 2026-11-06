-- The message an outcome was recorded for (tools/outcomes.py): a turn answered again after a
-- failure finds the visit it already counted, rather than counting it twice. Empty for one
-- recorded from the page, which its once-only form guards.
ALTER TABLE outcomes ADD COLUMN message_id INTEGER REFERENCES messages (id);
CREATE INDEX outcomes_message_idx ON outcomes (message_id) WHERE message_id IS NOT NULL;
