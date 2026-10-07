# Backup and restore

## Overview

Everything the family has told FamilyDB is one SQLite file, so a backup is a copy of
that file. The installer schedules one every night, and a restore puts one back.
Four things are worth knowing before you need them: backups are safe to take while
the bot is running; a backup on the same disk is not a real backup until you have
copied it elsewhere; a restore takes a safety backup of whatever it replaces, so it can
be undone; and a backup must never be newer than the code you restore it onto.

## What is in a backup, and what is not

| Path | What it is | In the backups? |
|---|---|---|
| `data/familydb.sqlite3` | Everything: messages, ideas, plans, places, memories, the family, everyone's sign-in passwords (as hashes), settings changed from the page, and the AI and Telegram keys saved there | yes, it is the backup |
| `data/google_key.json` | The calendar service account's key, including one pasted on the Settings page | no. The calendar's ID is in the database, so after a restore on a new machine, connect the calendar again with a new key |
| `data/web_secret` | Signs the login cookie | no; a new one only signs everyone out |
| `.env` | The page's address and the installer's first password, and anything not set from the page | no; keep your own copy |

An AI company's key or the Telegram token saved on the Settings page lives in the
database as plain text, so **it is in every backup**. Treat a backup like the key
itself: backups are readable by the owner and root only, and should stay that way
wherever you copy them. A key kept in `.env` instead is not in a backup, which is the
trade to weigh when choosing where a key lives.

## The nightly backup

The installer puts one line in root's crontab (check it with `sudo crontab -u root -l`;
`maintain.sh schedule-backups` puts it back). At 03:15 every night it takes a backup into
`/opt/familydb/backups/`, and **only if that succeeded** deletes backups more than 14
days old (in practice, from the fifteenth day). The prune is tied to the success on purpose: a backup that fails never deletes
the good ones. Change how long they are kept with `schedule-backups --keep-days N`.

Backups are named `familydb-<timestamp>.sqlite3`. The same folder and name are used by
the safety backups that a restore and an [upgrade](/wiki/operations/upgrade-and-rollback)
take first, so those are pruned on the same schedule: the backup an upgrade took will be
gone after about two weeks, which matters if you roll back late. The prune deletes
anything named `familydb-*.sqlite3` in that folder, whoever put it there. To keep one
longer, copy it out of the folder.

## Taking one by hand

```bash
sudo /opt/familydb/scripts/maintain.sh backup
```

It checks there is room first (the database's size plus 50 MB), uses SQLite's online
backup, which is consistent even while the bot is answering a message, and checks the
file is not empty. On any failure it removes the incomplete file, so a half-written
backup never looks usable. It makes the file owner-only, which is why to use this and
not `familydb db backup DEST` for a backup you will keep. The command-line one refuses
to run when there is no database at the configured path, so a backup run from the wrong
folder reports an error instead of backing up a new empty database every night.

## Keep a copy off the server

A backup on the same disk goes with the disk. Backups are readable by root only, so
hand yourself a copy, then fetch it from your own computer:

```bash
sudo install -m 600 -o "$USER" /opt/familydb/backups/familydb-XXXX.sqlite3 ~/
scp you@server:familydb-XXXX.sqlite3 .       # on your own computer
rm ~/familydb-XXXX.sqlite3                   # on the server, once it has arrived
```

`maintain.sh backup` prints the first two commands with the real file name filled in.
Delete the copy in your home folder afterwards, and keep the one on your computer
somewhere private: it holds the family's keys in plain text. Do this now and then, and
after anything you would hate to lose.

## Restoring

List the backups, newest first, and pick one:

```bash
sudo ls -lt /opt/familydb/backups/ | head
sudo /opt/familydb/scripts/maintain.sh restore /opt/familydb/backups/familydb-XXXX.sqlite3
```

A file from anywhere else works too. In order, it:

1. **Checks the backup first.** The file must pass SQLite's quick integrity check and be a FamilyDB database (it reads the members table). If it fails, nothing is stopped or replaced.
2. Tells you what will happen and asks "Replace the database with that backup?" Answer y. Everything the bot was told since that backup was taken will be gone.
3. **Takes a safety backup of the database it is about to replace** (when there is one), so the restore itself can be undone. Its path is printed at the end.
4. Stops the bot, copies the backup into place, removes the old write-ahead files (they belong to the database that was replaced), sets the owner and permissions, and applies any migrations the backup is missing.
5. Starts the bot again. It is down for a few seconds.

**The backup must not be newer than the code.** An older backup is migrated forward by
the restore itself, so restoring one from before an upgrade is fine. The other way is
the danger: a backup taken by newer code (copied from another machine, say, or after
rolling the code back without the database) is not refused. The migration step sees
nothing to do, the bot starts, and it may then fail on a column it does not know. Check
the code's version with `maintain.sh status` first, and after any restore run:

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

If it warns that the database is "newer than this code", [upgrade the code](/wiki/operations/upgrade-and-rollback)
first and restore again. To go back past an upgrade, restore the backup the upgrade took
*and* put the older code back, as that page describes.

**If it fails partway,** the bot is left stopped. The safety backup is the newest
`familydb-*.sqlite3` in the backups folder (`sudo ls -t /opt/familydb/backups | head -1`);
restore it the same way to get back to where you were, and run `maintain.sh check` to see
what went wrong.

Settings changed on the page, and the AI and Telegram keys saved there, come back with the
database. The calendar key file does not (see the table above). The Status page then shows
what is connected.

## Docker

On a Docker install `maintain.sh` takes the same commands and runs the backup and
restore inside the container for you. The files still sit on the host, in
`/opt/familydb/backups` and `data/`.

## Why it is built this way

One file means a backup is a copy and a restore is a copy back, with no export or import
to get wrong. The prune follows the success so the schedule can never leave you with no
backups because the backup quietly stopped working, and the restore checks the file and
saves what it replaces because the usual reason for a restore is a bad day, when it is
easiest to pick the wrong file.

A backup you have never restored is only a hope. Once, on a spare machine or after the
install, restore one and look at the Status page.

`RUNBOOK.md` section 7 covers restoring by hand, and reminds you that calendar events are
also in Google, which holds the second copy of every plan.
