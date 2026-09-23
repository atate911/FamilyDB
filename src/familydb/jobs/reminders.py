"""Turn due reminders into durable outgoing messages. No model calls."""

from contextlib import closing

from familydb.app import App
from familydb.dates import utc_iso
from familydb.delivery import deliver
from familydb.store import messages, tasks
from familydb.store.db import transaction
from familydb.task_service import reminder_text


def run_reminders(app: App) -> int:
    app.refresh()
    now = utc_iso(app.clock.now())
    with closing(app.connect()) as conn:
        with transaction(conn):
            rows = conn.execute(
                "SELECT r.id,r.task_id FROM reminders r JOIN tasks t ON t.id=r.task_id "
                "WHERE r.cancelled_at IS NULL AND r.message_id IS NULL AND r.remind_at<=? "
                "AND t.status='open' ORDER BY r.remind_at LIMIT 100",
                (now,),
            ).fetchall()
            for row in rows:
                task = tasks.get(conn, row["task_id"])
                out = messages.insert_out(
                    conn,
                    channel=task["channel"],
                    chat_id=task["chat_id"],
                    text=reminder_text(task),
                    now=now,
                )
                conn.execute("UPDATE reminders SET message_id=? WHERE id=?", (out.id, row["id"]))
        pending = conn.execute(
            "SELECT r.message_id FROM reminders r JOIN messages m ON m.id=r.message_id "
            "WHERE r.cancelled_at IS NULL AND m.delivered_at IS NULL AND m.cancelled_at IS NULL"
        ).fetchall()
    return sum(deliver(app, row["message_id"]) for row in pending)
