-- A person's birthday and, for a kid, whether she is a girl or he is a boy (familydb/family.py,
-- docs/WISHES.md): set by an admin on the Family page, never by the model. Code works out an
-- age and the days to a birthday from the date; only the age reaches the model. NULL is not given.
ALTER TABLE members ADD COLUMN birth_date TEXT;
ALTER TABLE members ADD COLUMN gender TEXT CHECK (gender IS NULL OR gender IN ('male', 'female'));
