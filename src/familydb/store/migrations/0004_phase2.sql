-- Phase 2: enrichment notes on ideas; follow-up bookkeeping and the originating chat on plans.
ALTER TABLE ideas ADD COLUMN enrichment_note TEXT;
ALTER TABLE plans ADD COLUMN followed_up_at TEXT;
ALTER TABLE plans ADD COLUMN channel TEXT;
ALTER TABLE plans ADD COLUMN chat_id TEXT;
