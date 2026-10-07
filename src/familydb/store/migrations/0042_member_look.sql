-- A person's look follows them: what the Look page chooses is kept with the member, so signing in
-- on another phone or computer brings it. It holds exactly what the look cookie holds ("rail.dark",
-- `web/looks.value`), and a value that names no look is read as the default, as a bad cookie is.
-- NULL until somebody chooses: Kitchen Table, following the device.
ALTER TABLE members ADD COLUMN look TEXT;
