-- Durable external operations and renewable claims for processing and delivery.
CREATE TABLE calendar_creations (
    operation_key TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    result TEXT
);
ALTER TABLE messages ADD COLUMN claim_token TEXT;
ALTER TABLE messages ADD COLUMN claim_until TEXT;
ALTER TABLE messages ADD COLUMN delivered_at TEXT;
-- Old messages have no delivery evidence. Do not resend historical conversations.
UPDATE messages SET delivered_at = processed_at WHERE direction = 'out';
CREATE INDEX messages_delivery_idx ON messages(direction, delivered_at);
