-- The place names a shared location was given (whereabouts.py) and the reply that said one, kept
-- only so that, when the location is forgotten a day on, the name can be taken out of what still
-- holds it (store/place_names.py). Deleted with the scrub.
CREATE TABLE place_names (
    id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members (id),
    label TEXT NOT NULL,
    named_at TEXT NOT NULL,
    message_id INTEGER REFERENCES messages (id)
);
CREATE INDEX place_names_named_idx ON place_names (named_at);
