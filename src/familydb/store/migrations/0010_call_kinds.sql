-- What each model call was for (chat, digest, retry, enrich, discover), as declared in
-- agent/gateway.py, so what the bot costs can be told apart by purpose and not only by model.
-- Calls made before this migration have none.
ALTER TABLE llm_calls ADD COLUMN kind TEXT;
