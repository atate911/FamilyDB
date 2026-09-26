-- When an idea is on, for one tied to dates: a festival, a show's run, a concert. The first day
-- it is on ('YYYY-MM-DD', or 'YYYY-MM-DDTHH:MM' when a start time was said, family clock time)
-- and the last ('YYYY-MM-DD'; the same day for a one-day thing, empty when it has no end). Both
-- empty for the usual idea, which is not tied to any date. Not in the FTS index.
ALTER TABLE ideas ADD COLUMN happens_from TEXT;
ALTER TABLE ideas ADD COLUMN happens_until TEXT;
