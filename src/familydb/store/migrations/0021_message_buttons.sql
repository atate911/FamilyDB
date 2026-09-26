-- The buttons a message goes with: a reminder's Done, In an hour and Tomorrow, a follow-up's
-- answers (familydb/buttons.py). Kept with the message, so one sent again carries them. JSON, a
-- list of {label, data}; NULL for none.
ALTER TABLE messages ADD COLUMN buttons TEXT CHECK (buttons IS NULL OR json_valid(buttons));
