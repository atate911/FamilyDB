-- A submitted idea form may be retried after a redirect or connection loss.
CREATE TABLE web_submissions (
    token TEXT PRIMARY KEY,
    result_id INTEGER NOT NULL REFERENCES ideas(id)
);
