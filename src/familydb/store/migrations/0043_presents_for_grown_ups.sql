-- A present is kept from every kid, always (the family's rule), so `ideas.hidden_from` now holds
-- only the grown-ups a present is also kept from. Kids are kept from by role, never by a list.
-- A list that named a kid loses that id; NULL stays the default (the grown-ups the present names).
UPDATE ideas
SET hidden_from = (
    SELECT json_group_array(value) FROM json_each(ideas.hidden_from)
    WHERE value NOT IN (SELECT id FROM members WHERE role = 'kid')
)
WHERE hidden_from IS NOT NULL;

-- The idea a to-do is about, so a to-do for a present ("Order Alex's watch") is kept from whoever
-- the present is kept from, on the pages and in the chat's lists.
ALTER TABLE tasks ADD COLUMN idea_id INTEGER REFERENCES ideas (id);

-- Any way of saying present was never kept from anyone; it is saved as "gift" now (ideas.normal_kind).
UPDATE ideas SET kind = 'gift'
WHERE lower(trim(kind)) IN ('gifts', 'present', 'presents', 'gift idea', 'gift ideas');
