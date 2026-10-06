-- What code can hold a suggestion to, for a firm memory (docs/MEMORY.md, suggest/rules.py): JSON
-- with any of max_travel_minutes, max_cost_level, setting ('indoor' or 'outdoor') and avoid (idea
-- tags). NULL for none, which is every memory before this and every taste.
ALTER TABLE memories ADD COLUMN rule TEXT;
