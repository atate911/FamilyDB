# State and the database

FamilyDB keeps everything in one file, `data/familydb.sqlite3`. Never edit or copy it by hand while FamilyDB runs. To take or restore a backup, go to [Backup and restore](/wiki/operations/backup-and-restore).

On a server install the file is `/opt/familydb/data/familydb.sqlite3`. The setting is `FAMILYDB_PATH`, in `.env`. It is a [SQLite](/wiki/reference/glossary#sqlite) database, which runs inside the program, so there is no database server.

Four things live outside the file: the Google service-account key (`data/google_key.json`), the login signing key (`data/web_secret`), `.env`, and the logs. A backup copies only the database, and a restore never brings those back.

## What is in it

| Group | Tables | What they are for |
|---|---|---|
| Family and sign-in | `members`, `member_logins`, `telegram_invites`, `member_locations` | Who FamilyDB talks to and their roles; each person's password as a [hash](/wiki/reference/glossary#hash) only, kept apart so a hash never travels with a member into a prompt; hashed one-time Telegram links; the last place each person shared |
| Ideas and places | `ideas`, `ideas_fts`, `places`, `outcomes`, `suggestions` | The ideas, their search index, looked-up facts, how things went, and what each suggestion proposed with its verdicts |
| Plans | `plans`, `calendar_creations`, `calendar_sync_state` | The plans, the event id written before Google is asked, and Google's sync token |
| Things to do | `tasks`, `reminders` | The things to do and their reminders |
| Memories | `memories` | What the family said about itself |
| Wishes | `wishes`, `wish_days` | The kids' wish lists and each kid's daily count |
| Messages and delivery | `messages` | Every message in and out, with its state, claim, delivery mark and buttons |
| Calls | `llm_calls`, `tool_calls`, `spend_holds` | Each model call and what it cost, each tool call with its input and output, and the cost reserved for a call in flight |
| Settings | `app_settings`, `settings_log` | Settings changed on the page, and who changed what (a secret's value is not written to the log) |
| Models and prices | `models`, `model_changes`, `model_sources`, `judgements` | What the daily check found, and the questions a stronger model was asked about it |
| Alerts and knocks | `alerts`, `knocks` | Troubles only an admin can fix, and strangers who messaged FamilyDB: who and when, never what they said |
| Bookkeeping | `schema_version` | Which migrations have run |

> **Anyone who can read the file can read the model-company and Telegram keys saved on the Settings page.** They sit in `app_settings` as plain text, so they are in every backup too. FamilyDB makes the file, and its `-wal` and `-shm` files, readable by their owner only, and tightens an older one when the service starts. Keep it that way wherever you copy it.

[What is stored and for how long](/wiki/security/data-and-privacy) lists the rest.

## How big it gets

The file only grows. Nothing prunes `messages`, `llm_calls`, `tool_calls`, `suggestions` or `settings_log`, and there is no supported way to delete old messages or one person's chat. FamilyDB prunes `knocks`, `alerts`, `judgements`, expired `telegram_invites`, stale `spend_holds`, and `member_locations`.

`sudo /opt/familydb/scripts/maintain.sh status` shows the file's size, and `familydb db status` shows row counts. Taking somebody off for good keeps what they said, with no name on it ([Switch off, or take off for good](/wiki/controls/family#switch-off-or-take-off-for-good)).

## Looking at it safely

`familydb db status` prints the schema version, row counts and the last five model calls. `familydb ideas list` prints each idea in the one-line form the model reads, but over every idea, presents included, and `familydb members list` prints the family. Each applies pending migrations first. Run them as in [The command line](/wiki/operations/command-line#how-to-run-it); for example, `db status`:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb db status
```

On Docker:

```bash
sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb db status
```

For anything else, open the file read-only so nothing can change it, if the `sqlite3` tool is installed. Reading while FamilyDB runs is safe.

```bash
sudo -u familydb sqlite3 -readonly /opt/familydb/data/familydb.sqlite3 'select id, title, status from ideas order by id desc limit 10;'
```

Run it as the account that owns the file, so a `-wal` or `-shm` file it creates is not left owned by root. On Docker the host folder is the same `/opt/familydb/data`, owned by user ID 1000, so use `sudo -u '#1000'` in place of `sudo -u familydb`.

## How it works

### Migrations

The layout of the file changes only through numbered files, `0001` onward, shipped with the software. Each is a *migration*: it runs once, in its own transaction, and is recorded in `schema_version`. They run when the service starts, when you run `familydb db migrate`, when an upgrade runs, and first by most commands. They only go forward, so going back past one means restoring the backup the upgrade took ([Upgrade and rollback](/wiki/operations/upgrade-and-rollback)).

A file that has run a migration the code does not know is newer than the code. `familydb doctor` reports `database is at migration N, newer than this code's M`, and the code may then fail on a column it does not know.

### The write-ahead log and the connections

SQLite keeps recent writes in a write-ahead log, the `familydb.sqlite3-wal` file, with a small `-shm` file beside it, and folds them into the main file from time to time. Both belong to the running database. A copy of the main file alone can miss recent writes, which is why backups use SQLite's own online backup.

Every thread (a page request, a job, Telegram) opens its own connection with the log on, foreign keys on and a wait of up to 5 seconds for a write lock. A write is a short transaction, so two writers take turns instead of overwriting each other, and readers are not held up. A tool that has finished stays saved if a later step of the same turn fails. A power cut can lose the last few commits from the log, without corrupting the file.

### Backups and restores

A restore replaces the whole file, so everything told to FamilyDB since the backup is gone, including delivery, follow-up and check marks, so some reminders, follow-ups or checks may be sent again. Settings and the keys saved on the page come back with it; the Google key file and `.env` do not. An event made in Google after the backup is still there, but no plan owns it, so it shows as added in Google ([Plans and the calendar](/wiki/model/plans-and-calendar)). [Backup and restore](/wiki/operations/backup-and-restore) has the steps.

## Rules for admins

> **Editing the database by hand can lose family data the app would have protected.** Some rules live in code, not in the file: an idea's plain title for the duplicate check, a thing to do's revision number, and what leaves with a person who is taken off for good. Jobs open a write transaction every minute and write whenever something is due.

To change anything, use the page, or `familydb tool` ([The command line](/wiki/operations/command-line)), and take a backup first.

- Never copy over, move or delete the file or its `-wal` and `-shm` files while FamilyDB runs.
- Never run a second copy of the service on the same file: it would repeat the jobs.
- When somebody is taken off for good, FamilyDB removes what was theirs alone and blanks their name wherever else it is stored. A test checks this against the database layout, so a new table cannot forget.
- Keep the file owner-only. `maintain.sh restore` refuses a backup newer than the code it would be restored onto.

Developer docs: src/familydb/store/db.py, src/familydb/store/migrations/, src/familydb/store/members.py, src/familydb/privacy.py; docs/DESIGN.md, "Data model".
