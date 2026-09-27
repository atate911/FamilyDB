-- When somebody asked for an idea to be looked up now rather than with the evening's lookups
-- (the look_up_now tool, the page's button, Telegram's /lookup). Cleared once it has been.
ALTER TABLE ideas ADD COLUMN lookup_wanted_at TEXT;
