-- Whom a present is kept from, chosen on the idea ("Hidden from Maya and Theo").
--
-- A JSON list of member ids. NULL, which is every idea until somebody chooses, means the default:
-- a present is kept from the people it is for (its participants), so nothing has to be filled in
-- for the presents already saved, and a present the chat saves is kept from them too. An empty
-- list is a choice as well: kept from nobody. Only a present (kind "gift") is ever hidden.
ALTER TABLE ideas ADD COLUMN hidden_from TEXT;
