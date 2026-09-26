-- When a plan was checked the evening before (jobs/plan_checks.py): its weather and its place's
-- hours, once, whether or not anything was said. NULL for a plan not checked.
ALTER TABLE plans ADD COLUMN checked_at TEXT;
