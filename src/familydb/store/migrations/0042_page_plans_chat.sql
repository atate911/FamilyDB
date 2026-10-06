-- A plan made on the page had no chat, so it was never checked the evening before nor asked about
-- the day after: both look only at plans with one (store/plans.py). It is given the page's own
-- conversation, which is the family's, from now on (tools/gcal.py create_event); here the plans
-- already made there get it too. A cancelled plan needs none, and one with nobody behind it was
-- left without a chat on purpose (somebody taken off the list: plans.leave_chat).
UPDATE plans
   SET channel = 'web', chat_id = 'web'
 WHERE chat_id IS NULL AND created_by IS NOT NULL AND status != 'cancelled';
