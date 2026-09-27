-- Which turn each model call and tool call belonged to, so a lookup (which has no chat message
-- to hang off) can be shown whole on the status page, and what a worker turn was about (the
-- idea looked up, the weekend searched). Null for calls from before this.
ALTER TABLE llm_calls ADD COLUMN turn TEXT;
ALTER TABLE llm_calls ADD COLUMN about TEXT;
ALTER TABLE tool_calls ADD COLUMN turn TEXT;
CREATE INDEX llm_calls_turn_idx ON llm_calls (turn);
CREATE INDEX tool_calls_turn_idx ON tool_calls (turn);
