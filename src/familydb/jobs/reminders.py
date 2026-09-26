"""Turn due reminders into durable outgoing messages. No model calls.

This job sends what it queues, through the voice layer: in a chat where the family is talking
right now, a reminder waits a moment to be carried by the reply they are about to get. One that
could not go is the retry job's, on its own interval (`run_deliveries`), rather than tried again
here every minute. It also sends, as written, any held message no conversation carried in time.
"""

from contextlib import closing
from datetime import datetime

from familydb import buttons, voice
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import messages, tasks
from familydb.store.db import transaction
from familydb.task_service import gifts_for, late_note, reminder_text, schedule_next


def run_reminders(app: App) -> int:
    app.refresh()
    moment = app.clock.now()
    now = utc_iso(moment)
    queued: list[tuple[int, str, str, str, str]] = []
    with closing(app.connect()) as conn:
        with transaction(conn):
            for reminder in tasks.due_reminders(conn, now):
                task = tasks.get(conn, reminder.task_id)
                if task is None:
                    continue
                due_when = late_note(reminder.remind_at, now, app.clock.tz)
                out = messages.insert_out(
                    conn,
                    channel=task.channel,
                    chat_id=task.chat_id,
                    text=reminder_text(
                        task, app.settings, due_when=due_when, gifts=gifts_for(conn, task)
                    ),
                    now=now,
                    buttons=buttons.for_reminder(task.id),
                )
                tasks.attach_message(conn, reminder.id, out.id)
                # A task on a schedule gets its next time round now, the first one still to come.
                due = datetime.fromisoformat(reminder.remind_at)
                schedule_next(conn, task, after=max(moment, due), zone=app.clock.tz)
                event = "reminder_late" if due_when else "reminder"
                queued.append((out.id, event, task.channel, task.chat_id, task.title))
        # Committed first: sending marks the message delivered from a connection of its own.
        sent = sum(
            voice.hand_over(
                app, conn, message_id, event=event, channel=channel, chat_id=chat, mention=title
            )
            for message_id, event, channel, chat, title in queued
        )
    # Held messages no conversation carried in time go now, as written.
    return sent + voice.release(app)
