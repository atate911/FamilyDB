-- Whose birthday or anniversary a task is (task_service.py): its reminder lists the gift ideas
-- saved for them, ideas of kind gift whose participants name them. NULL for any other task.
ALTER TABLE tasks ADD COLUMN gift_for TEXT;
