# State and the database

Everything FamilyDB keeps is in one SQLite file, and this page says what is in it, how to look at it without harming it, how it changes between versions and what an admin must not do to it. To take or restore a backup, go to [Backup and restore](/wiki/operations/backup-and-restore).

On a default install the file is `data/familydb.sqlite3` in the install folder (`/opt/familydb/data/familydb.sqlite3` on a server install). The setting is `FAMILYDB_PATH`, in `.env`.

## What is in it

| Group | Tables | What they are for |
|---|---|---|
| Family and sign-in | `members`, `member_logins`, `telegram_invites`, `member_locations` | Who the bot talks to and their roles; each person's password as a hash only, kept apart so a hash never travels with a member into a prompt; hashed one-time Telegram links; the last place each person shared |
| Ideas and places | `ideas`, `ideas_fts`, `places`, `outcomes`, `suggestions` | The ideas, their search index, looked-up facts, how things went, and what each suggestion proposed with its verdicts |
| Plans | `plans`, `calendar_creations`, `calendar_sync_state` | The plans, the event id written before Google is asked, and Google's sync token |
| Things to do | `tasks`, `reminders` | The things to do and their reminders |
| Memories | `memories` | What the family said about itself |
| Wishes | `wishes`, `wish_days` | The kids' wish lists and each kid's daily count |
| Messages and delivery | `messages` | Every message in and out, with its state, claim, delivery mark and buttons |
| Calls | `llm_calls`, `tool_calls`, `spend_holds` | Each model call and what it cost, each tool call with its input and output, and the cost set aside for a call in flight |
| Settings | `app_settings`, `settings_log` | Settings changed on the page, and who changed what (a secret's value is not written to the log) |
| Models and prices | `models`, `model_changes`, `model_sources`, `judgements` | What the daily check found, and the questions a stronger model was asked about it |
| Alerts and knocks | `alerts`, `knocks` | Troubles only an admin can fix, and strangers who messaged the bot: who and when, never what they said |
| Bookkeeping | `schema_version` | Which migrations have run |

**Anyone who can read the file can read the model-company and Telegram keys saved on the Settings page.** They sit in `app_settings` as plain text, so they are in every backup too. FamilyDB makes the file, and its `-wal` and `-shm` files, readable by their owner only, and tightens an older one when the service starts. Keep it that way wherever you copy it. See [data and privacy](/wiki/security/data-and-privacy).

## Looking at it safely

These commands show what is stored. Run them as the account that owns the file (the install folder's `familydb` account) and see [the command line](/wiki/controls/command-line) for the exact form.

```bash
familydb db status
familydb ideas list
familydb members list
```

`db status` prints the schema version, the row counts for members, ideas, places, plans, outcomes, messages and tool calls, and the last five model calls. `ideas list` prints each idea as the model sees it, and `members list` the family. Each applies pending migrations first.

For anything else, open the file read-only so nothing can change it, if the `sqlite3` tool is installed:

```bash
sqlite3 -readonly /opt/familydb/data/familydb.sqlite3 'select id, title, status from ideas order by id desc limit 10;'
```

Reading while FamilyDB runs is safe.

## Migrations

The layout of the file changes only through numbered files, `0001` onward, shipped with the software. Each runs once, in its own transaction, and is recorded in `schema_version`. They run when the service starts, when you run `familydb db migrate`, when an upgrade runs, and first by most commands. They are append-only: a migration that has been applied is never edited, and a change to the layout is a new file. They only go forward, so going back past one means restoring the backup the upgrade took ([upgrade and rollback](/wiki/operations/upgrade-and-rollback)).

A file that has run a migration the code does not know is newer than the code. `familydb doctor` reports it as "database is at migration N, newer than this code's M", and the code may then fail on a column it does not know.

## One file, the write-ahead log and the connections

SQLite keeps recent writes in a write-ahead log, the `familydb.sqlite3-wal` file, with a small `-shm` file beside it, and folds them into the main file from time to time. Both belong to the running database. A copy of the main file alone can miss recent writes, which is why backups use SQLite's own online backup.

FamilyDB opens each connection with the log on, foreign keys on, and a wait of up to five seconds for a write lock. Every thread (a page request, a job, Telegram) opens its own connection and does not share one. A write is a short transaction that takes the write lock when it begins, so two writers take turns instead of overwriting each other, and readers are not held up. A tool that has finished stays saved if a later step of the same turn fails.

## Backups and restores

A backup is a copy of the file, taken while the bot runs. Schedule, copying off the server and the commands are on [Backup and restore](/wiki/operations/backup-and-restore).

A restore replaces the whole file, so everything told to FamilyDB since the backup is gone. Settings and keys saved on the page come back with it. The old log files are removed, and migrations the backup lacks are applied. A safety backup of what it replaces is taken before the swap.

Google keeps its own copy of the calendar, which the restore does not touch. An event made after the backup is still in Google, but no plan owns it, so it shows as added in Google. See [plans and the calendar](/wiki/model/plans-and-calendar).

## Rules for admins

**Editing the database by hand can lose family data the app would have protected.** Some rules live in code, not in the file: an idea's plain title for the duplicate check, a thing to do's revision number, the checks on who may be removed, and what leaves with a person who is. A job also writes to the file every minute. To change anything, use the page, or `familydb tool` (see [the command line](/wiki/controls/command-line)), and take a backup first.

- Never copy over, move or delete the file or its `-wal` and `-shm` files while FamilyDB runs.
- Never run a second copy of the service on the same file: it would repeat the jobs.
- `POINTING_AT` is the list in the code of every column that points at a family member, with what removing a person for good does to it (delete the row, or blank the name), and a test holds it to the schema so a new table cannot forget.
- Keep the file owner-only, and a backup no newer than the code it is restored onto.

Developer docs: `src/familydb/store/db.py` (`connect`, `transaction`, `migrate`), `store/migrations/`, `store/members.py` (`POINTING_AT`), `privacy.py`, `cli.py` (`db_status`), and `docs/DESIGN.md`, "Data model".
