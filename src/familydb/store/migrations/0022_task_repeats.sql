-- A task that comes round again (task_service.py): every `repeat_every` `repeat_unit`s, either on
-- a schedule counted from `repeat_anchor` (the first reminder, as an instant) or counted from
-- when it was last done. All four are set together or none is. `last_done_at` is when it was last
-- marked done, which for a repeating task records it rather than ending it.
ALTER TABLE tasks ADD COLUMN repeat_every INTEGER CHECK (repeat_every IS NULL OR repeat_every > 0);
ALTER TABLE tasks ADD COLUMN repeat_unit TEXT
    CHECK (repeat_unit IS NULL OR repeat_unit IN ('day', 'week', 'month', 'year'));
ALTER TABLE tasks ADD COLUMN repeat_from TEXT
    CHECK (repeat_from IS NULL OR repeat_from IN ('schedule', 'done'));
ALTER TABLE tasks ADD COLUMN repeat_anchor TEXT;
ALTER TABLE tasks ADD COLUMN last_done_at TEXT;
