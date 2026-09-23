-- People who messaged the bot but are not on the family list, so the Family page can offer to
-- add them without anybody copying an id across. Who and when, never what they said.
CREATE TABLE knocks (
    channel TEXT NOT NULL,
    channel_user_id TEXT NOT NULL,
    name TEXT,
    chat_id TEXT,
    first_at TEXT NOT NULL,
    last_at TEXT NOT NULL,
    times INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (channel, channel_user_id)
);
CREATE INDEX knocks_last_idx ON knocks (last_at);
