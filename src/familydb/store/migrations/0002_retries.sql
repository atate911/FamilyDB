-- Retry bookkeeping for inbound messages whose processing failed.
ALTER TABLE messages ADD COLUMN retries INTEGER NOT NULL DEFAULT 0;
