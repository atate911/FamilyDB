-- Which days the bot was asked to nudge a kid's wording ("we should" for "I want") or to praise
-- it (familydb/wording.py): at most one of each a day, and fewer as she improves.
ALTER TABLE wish_days ADD COLUMN nudged INTEGER NOT NULL DEFAULT 0;
ALTER TABLE wish_days ADD COLUMN praised INTEGER NOT NULL DEFAULT 0;
