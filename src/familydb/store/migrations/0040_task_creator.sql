-- Who made a to-do, so a kid's own can say "Set by Alex": the one she did not set herself.
--
-- Set from now on, by the person signed in when a form made it and by whoever's message asked for
-- it in the chat. NULL for everything before this, and while the family shares one password: no
-- "Set by" line is drawn for those, rather than a guess.
ALTER TABLE tasks ADD COLUMN created_by_member_id INTEGER REFERENCES members(id);
