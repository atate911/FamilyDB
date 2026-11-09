-- When an idea last went from done or dropped back to an idea (tools/ideas.py update_idea: the
-- page's Again? and Bring it back, or the family saying so): a "would not again" given before it
-- no longer keeps the idea out of suggestions or dinner (store/outcomes.py latest_preferences).
-- Never part of the idea record a model reads, so the cached prefix is unchanged.
ALTER TABLE ideas ADD COLUMN reconsidered_at TEXT;
