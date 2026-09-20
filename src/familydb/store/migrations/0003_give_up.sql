-- A failed message the retry job must leave alone (configuration problems), until reset by hand.
ALTER TABLE messages ADD COLUMN give_up INTEGER NOT NULL DEFAULT 0;
