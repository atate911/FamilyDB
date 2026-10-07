-- Every tool call is recorded where it is dispatched (tools/registry.py), not only the model's:
-- a button tapped, a page form, a command, a job, a worker turn, the command line. Who made it
-- (`member_id`, unnamed when they are taken off) and from where (`source`), and for a write that
-- can be taken back, how: `undo`, the inverse its tool worked out in its own transaction (JSON),
-- and `undone_at`, so it is never undone twice.
ALTER TABLE tool_calls ADD COLUMN member_id INTEGER REFERENCES members (id) ON DELETE SET NULL;
ALTER TABLE tool_calls ADD COLUMN source TEXT;
ALTER TABLE tool_calls ADD COLUMN undo TEXT CHECK (undo IS NULL OR json_valid(undo));
ALTER TABLE tool_calls ADD COLUMN undone_at TEXT;
CREATE INDEX tool_calls_undo_idx ON tool_calls (member_id, id) WHERE undo IS NOT NULL;
