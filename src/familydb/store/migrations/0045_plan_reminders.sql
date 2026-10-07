-- A reminder set for a plan ("a week before the concert") is a task tied to it, so that it moves
-- when the plan moves and goes when the plan is cancelled (plan_service.changed). Before this, a
-- reminder for the 11th stayed on the 11th when the concert moved to the 19th, and still went when
-- it was called off. `plan_remind` says which reminder it is: '1 week', '3 days', '1 day',
-- 'morning of', '2 hours', '1 hour' or 'time to leave'; its time is worked out from the plan's
-- start each time the plan moves.
ALTER TABLE tasks ADD COLUMN plan_id INTEGER REFERENCES plans (id) ON DELETE SET NULL;
ALTER TABLE tasks ADD COLUMN plan_remind TEXT;
CREATE INDEX tasks_plan_idx ON tasks (plan_id) WHERE plan_id IS NOT NULL;
