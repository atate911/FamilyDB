-- What each model call cost, so a day's spending can be added up and capped.
-- Numbered 0008, not 0007: PR #2 shipped a 0007_web.sql that was not taken, and a database that
-- ran it must still apply this one. Calls made before this migration have no cost recorded.
ALTER TABLE llm_calls ADD COLUMN provider TEXT;
ALTER TABLE llm_calls ADD COLUMN web_searches INTEGER;
ALTER TABLE llm_calls ADD COLUMN cost_usd REAL;
-- Estimated at UNLISTED prices because the model was not in the price table.
ALTER TABLE llm_calls ADD COLUMN cost_estimated INTEGER NOT NULL DEFAULT 0;
CREATE INDEX llm_calls_created_idx ON llm_calls (created_at);
