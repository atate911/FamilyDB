"""Turn due reminders into durable outgoing messages. No model calls.

This job sends what it queues. One that could not go is the retry job's, on its own interval
(`run_deliveries`), rather than tried again here every minute.
"""

from contextlib import closing
from datetime import datetime, timedelta

from familydb.app import App
from familydb.dates import utc_iso
from familydb.delivery import deliver
from familydb.store import messages, tasks
from familydb.store.db import transaction
from familydb.task_service import reminder_text

# A reminder queued later than this after its time says when it was due.
LATE_AFTER = timedelta(minutes=10)


def run_reminders(app: App) -> int:
    app.refresh()
    moment = app.clock.now()
    now = utc_iso(moment)
    queued: list[int] = []
    with closing(app.connect()) as conn, transaction(conn):
        for reminder in tasks.due_reminders(conn, now):
            task = tasks.get(conn, reminder.task_id)
            if task is None:
                continue
            due = datetime.fromisoformat(reminder.remind_at)
            due_when = (
                due.astimezone(app.clock.tz).strftime("%a %d %b at %H:%M")
                if moment - due > LATE_AFTER
                else None
            )
            out = messages.insert_out(
                conn,
                channel=task.channel,
                chat_id=task.chat_id,
                text=reminder_text(task, due_when=due_when),
                now=now,
            )
            tasks.attach_message(conn, reminder.id, out.id)
            queued.append(out.id)
    return sum(deliver(app, message_id) for message_id in queued)
