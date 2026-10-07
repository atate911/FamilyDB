-- Each person gets a colour on the page, one of eight, kept with them (Kitchen Table's `.p1`..`.p8`).
--
-- A slot, not a colour: the stylesheet and the look decide what each looks like, and a look may give
-- its own eight. It is assigned when somebody is added (the lowest slot nobody has), never by
-- name, so renaming a person keeps their colour. NULL reads as "no colour yet" and is drawn
-- like Everyone. Existing people are given theirs in the order they were added.
ALTER TABLE members ADD COLUMN slot INTEGER;

UPDATE members
   SET slot = (SELECT COUNT(*) FROM members AS earlier WHERE earlier.id < members.id) % 8 + 1;
