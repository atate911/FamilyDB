-- What a shared location is called ("Pearl District, Portland"), looked up once when it is
-- shared, so a reply and the chat model can name it without asking the map again.
ALTER TABLE member_locations ADD COLUMN label TEXT;
