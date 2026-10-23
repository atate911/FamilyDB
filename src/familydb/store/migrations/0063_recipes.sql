-- Recipes (docs/RECIPES.md): an idea of kind recipe keeps its own facts here, one row per idea, as
-- `places` does for a place. What the family said stands; what a page said fills only what is
-- empty (`filled_by`). Situations are `occasions` (the family's word) and `occasions_guessed`
-- (read from the facts by code, a maybe until a word makes it theirs). Each ingredient is its line
-- as written with the item and amount read out of it, so a grocery list needs no model call.
CREATE TABLE recipes (
    idea_id INTEGER PRIMARY KEY REFERENCES ideas (id) ON DELETE CASCADE,
    name TEXT,
    source_url TEXT,
    source_site TEXT,
    ingredients TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(ingredients)),
    steps TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(steps)),
    active_minutes INTEGER,
    total_minutes INTEGER,
    serves INTEGER,
    occasions TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(occasions)),
    occasions_guessed TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(occasions_guessed)),
    prep_note TEXT,
    filled_at TEXT,
    filled_by TEXT CHECK (filled_by IS NULL OR filled_by IN ('family', 'page', 'lookup')),
    fill_note TEXT,
    name_wanted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE INDEX recipes_source_url_idx ON recipes (source_url);
