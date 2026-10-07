-- The ages an idea suits, when the family or a page said ("ages 6+", "for under-fives"): the
-- engine leaves out what a kid coming is too young or too old for (suggest/shortlist.py). Not
-- searched as text, so the full-text index is untouched.
ALTER TABLE ideas ADD COLUMN min_age INTEGER;
ALTER TABLE ideas ADD COLUMN max_age INTEGER;
