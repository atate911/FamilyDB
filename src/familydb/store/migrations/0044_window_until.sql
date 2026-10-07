-- "This weekend" or "sometime this week" in a task's window ends: the last day it means, that
-- week's Sunday, worked out from the day it was said (windows.until). Without it the words could
-- only be read as every weekend from then on, or not at all; past it they are a window nobody can
-- read, as the To do page and the model are told. A date, the family's.
ALTER TABLE tasks ADD COLUMN window_until TEXT;
