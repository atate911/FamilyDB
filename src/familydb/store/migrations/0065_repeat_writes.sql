-- A write repeated for the same message changes nothing (tests/test_repeat_writes.py). A retry
-- finds what already ran in the tool-call log, which is written after the tool's own
-- transaction, and a model may call a tool twice in one turn; so the two writes that count
-- something keep the request that made them. An outcome is kept once per request, idea and day;
-- a repeating task's round is done once per request.
ALTER TABLE outcomes ADD COLUMN operation_key TEXT;
CREATE UNIQUE INDEX outcomes_operation_key ON outcomes (operation_key)
    WHERE operation_key IS NOT NULL;
ALTER TABLE tasks ADD COLUMN last_done_key TEXT;
