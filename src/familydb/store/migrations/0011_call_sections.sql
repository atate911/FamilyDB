-- The size in characters of each part of what a model call sent (instructions, tools, the idea
-- list, history, the message, ...), as JSON, so the real input tokens it reports can be shared
-- out and the largest part found. Built in agent/compose.py. Older calls have none.
ALTER TABLE llm_calls ADD COLUMN sections TEXT;
