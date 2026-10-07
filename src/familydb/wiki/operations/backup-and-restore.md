# Backup and restore

## Overview

Everything the family has told FamilyDB is one SQLite file, so a backup is a copy of
that file. The installer schedules one every night, and a restore puts one back.
Three things are worth knowing before you need them: backups are safe to take while
the bot is running, a backup on the same disk is not a real backup until you have
copied it elsewhere, and a restore takes a safety backup of whatever it replaces, so
it can be undone.

## What is in a backup, and what is not

| Path | What it is | In the backups? |
|---|---|---|
| `data/familydb.sqlite3` | Everything: messages, ideas, plans, places, memories, the family, settings changed from the page, and any key saved there | yes, it is the backup |
| `data/google_key.json` | The calendar service account's key | no; make a new key if it is lost |
| `data/web_secret` | Signs the login cookie | no; a new one only signs everyone out |
| `.env` | The page's address and the installer's first password, and anything not set from the page | no; keep your own copy |

Because a key or token saved on the Settings page lives in the database, **it is in
every backup**. Treat a backup like the key itself: backups are readable by the
owner and root only, and should stay that way wherever you copy them. A key kept in
`.env` instead is not in a backup, which is the trade to weigh when choosing where a
key lives.

## The nightly backup

The installer puts one line in root's crontab (check it with `sudo crontab -u root -l`;
`maintain.sh schedule-backups` puts it back). At 03:15 every night it takes a backup into
`/opt/familydb/backups/`, and **only if that succeeded** deletes backups older than 14
days. The prune is tied to the success on purpose: a backup that fails never deletes
the good ones. Change how long they are kept with `schedule-backups --keep-days N`.

Backups are named `familydb-<timestamp>.sqlite3`. The same folder and name are used by
the safety backups that a restore and an [upgrade](/wiki/operations/upgrade-and-rollback)
take first, so those are pruned after the same number of days. If you want to keep one
longer, copy it out.

## Taking one by hand

```bash
sudo /opt/familydb/scripts/maintain.sh backup
```

It uses SQLite's online backup, which is consistent even while the bot is answering a
message, then checks that the file is not empty, and removes it if it is not. It also
checks there is room first (the database's size plus 50 MB). On any failure it removes
the incomplete file, so a half-written backup never looks usable.

`familydb db backup DEST` does the same from the command line. It refuses to run when
there is no database at the configured path, so a backup run from the wrong folder
reports an error instead of backing up a new empty database and succeeding every night.

## Keep a copy off the server

A backup on the same disk goes with the disk. Backups are readable by root only, so
hand yourself a copy, then fetch it from your own computer:

```bash
sudo install -m 600 -o "$USER" /opt/familydb/backups/familydb-XXXX.sqlite3 ~/
scp you@server:familydb-XXXX.sqlite3 .       # on your own computer
```

`maintain.sh backup` prints these two commands with the real file name filled in.
Do this now and then, and after anything you would hate to lose.

## Restoring

```bash
sudo /opt/familydb/scripts/maintain.sh restore /opt/familydb/backups/familydb-XXXX.sqlite3
```

In order, it:

1. **Checks the backup first.** The file must pass SQLite's integrity check and be a FamilyDB database (it reads the members table). If it fails, nothing is stopped or replaced.
2. Tells you what will happen and asks. Everything the bot was told since that backup was taken will be gone.
3. **Takes a safety backup of the database it is about to replace**, so the restore itself can be undone. It prints where that is at the end.
4. Stops the bot, copies the backup into place, removes the old write-ahead files (they belong to the database that was replaced), sets the owner and permissions, and applies any migrations the backup is missing.
5. Starts the bot again.

An older backup is migrated forward when the bot starts, so restoring a backup from
before an upgrade is fine. To go back past an upgrade's migrations, restore the backup
the upgrade took, and put the older code back too: see
[Upgrade and rollback](/wiki/operations/upgrade-and-rollback).

After a restore, `familydb db status` shows the schema version and row counts, and the
Status page shows what is connected. Settings changed from the page come back with the
database, so the keys saved there return with it.

## Docker

On a Docker install `maintain.sh` takes the same commands and runs the backup and
restore inside the container for you, so you do not change anything about how you call
it.

## Why it is built this way

- **One file** means a backup is a copy and a restore is a copy back, with no export or import to get wrong. SQLite's online backup is how it stays consistent while the bot runs.
- **The prune follows the success** so the schedule can never leave you with no backups because the backup quietly stopped working.
- **The check before the restore** means a damaged or wrong file is caught while the bot is still running and nothing has been replaced.
- **The safety backup** makes the dangerous step reversible, because the usual reason for a restore is a bad day, and a bad day is exactly when someone picks the wrong file.

A backup you have never restored is only a hope. Once, on a spare machine or after the
install, restore one and look at the Status page.

`RUNBOOK.md` section 7 has the same material with every command, including restoring by
hand.
