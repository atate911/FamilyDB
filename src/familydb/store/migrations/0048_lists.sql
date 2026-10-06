-- Lists the family keeps (tools/lists.py): the shopping list, and any other they name. One row a
-- thing on a list, kept once however it is written (`folded`), ticked when bought; who added and
-- who ticked are unnamed when they are taken off the list.
CREATE TABLE lists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE list_items (
    id INTEGER PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES lists (id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    folded TEXT NOT NULL,
    added_by INTEGER REFERENCES members (id) ON DELETE SET NULL,
    added_at TEXT NOT NULL,
    ticked_by INTEGER REFERENCES members (id) ON DELETE SET NULL,
    ticked_at TEXT,
    UNIQUE (list_id, folded)
);
CREATE INDEX list_items_list_idx ON list_items (list_id, ticked_at);
