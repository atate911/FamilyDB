-- Which kind of message she sent of her own accord (the voice event that worded it, such as
-- "reminder" or "follow_up", or "digest" for the weekend ideas), so the Messages page can show
-- what goes out unasked and how often. Null for everything else: a reply, a message in.
ALTER TABLE messages ADD COLUMN sent_as TEXT;
CREATE INDEX messages_sent_as_idx ON messages (received_at) WHERE sent_as IS NOT NULL;
