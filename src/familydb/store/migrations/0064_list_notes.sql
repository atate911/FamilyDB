-- A note on a thing on a list (docs/RECIPES.md, the grocery list): how much each recipe that put
-- it there wants, "2 cups (Fajitas), 1 (Soup)". Drawn small under it; nothing else moves.
ALTER TABLE list_items ADD COLUMN note TEXT;
