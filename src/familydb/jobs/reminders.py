"""Turn due reminders into stored outgoing messages and send them through the voice layer (no
model call): in a chat mid-conversation a reminder waits to ride the next reply. A failed send
is the retry job's (`run_deliveries`). Also releases held messages no reply carried."""

from contextlib import closing
from datetime import datetime

from familydb import buttons, routing, voice
from familydb.app import App
from familydb.dates import utc_iso
from familydb.store import messages, tasks
from familydb.store.db import transaction
from familydb.task_service import late_note, reminder_for, schedule_next


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
                # The owner's reminder goes to them, not the group (routing.py); one about a
                # present goes to their own chat whenever they have one, whatever the setting.
                channel, chat = routing.for_person(
                    conn, app.settings, task.channel, task.chat_id, task.owner_id
                )
                if task.idea_id is not None and (channel, chat) == (task.channel, task.chat_id):
                    channel, chat = routing.own_chat(conn, task.owner_id) or (channel, chat)
                out = messages.insert_out(
                    conn,
                    channel=channel,
                    chat_id=chat,
                    text=reminder_for(
                        conn, task, app.settings, channel=channel, chat_id=chat, due_when=due_when
                    ),
                    now=now,
                    buttons=buttons.for_reminder(task.id),
                )
                tasks.attach_message(conn, reminder.id, out.id)
                # A repeating task gets its next reminder now.
                due = datetime.fromisoformat(reminder.remind_at)
                schedule_next(conn, task, after=max(moment, due), zone=app.clock.tz)
                event = "reminder_late" if due_when else "reminder"
                queued.append((out.id, event, channel, chat, task.title))
        # Committed first: sending marks delivery on its own connection.
        sent = sum(
            voice.hand_over(
                app, conn, message_id, event=event, channel=channel, chat_id=chat, mention=title
            )
            for message_id, event, channel, chat, title in queued
        )
    return sent + voice.release(app)
