-- When a task kept for some Saturday morning was last brought up (jobs/nudges.py): each at most
-- once a week, and each chat once a day. NULL for a task never nudged.
ALTER TABLE tasks ADD COLUMN nudged_at TEXT;
