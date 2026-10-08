# Backup and restore

A backup is a copy of one file, taken every night at 03:15 and safe to take while FamilyDB runs. Copy it off the server, or it is not a backup. A restore puts one back and saves what it replaces first.

The family's whole history is one [SQLite](/wiki/reference/glossary#sqlite) file, so there is nothing to export or assemble. The commands are the same on a virtualenv and a Docker install.

## What is in a backup, and what is not

| Path | What it is | In a backup? |
|---|---|---|
| `data/familydb.sqlite3` | Messages, ideas, plans, places, memories, the family, everyone's sign-in passwords (as [hashes](/wiki/reference/glossary#hash)), settings changed on the web page, and the model-company and Telegram keys saved there | Yes: it is the backup |
| `data/google_key.json` | The calendar's key, including one pasted on the Settings page. The calendar's ID is in the database | No. After a restore on a new machine, connect the calendar again with a new key |
| `data/web_secret` | Signs the login cookie | No. A new one only signs everyone out |
| `.env` | The web page's address, the shared password and anything not set on the web page | No. Keep your own copy |

> **Anyone who can read a backup can read the model-company and Telegram keys saved on the Settings page.** They are stored as plain text in the database.

Backup files are mode 600, owned by the `familydb` account (on Docker, the container's user, uid 1000), so root and that account can read them. Keep a copy somewhere private. A key kept in `.env` instead is not in a backup; weigh that when you choose where a key lives.

## The nightly backup

The installer puts one line in root's [crontab](/wiki/reference/glossary#crontab). At 03:15 every night it takes a backup into `/opt/familydb/backups/` and, only if that succeeded, deletes backups more than 14 days old, which in practice means from the fifteenth day. A backup that fails never deletes the good ones. `sudo crontab -u root -l` shows the line; `maintain.sh schedule-backups` puts it back, and `--keep-days N` changes how long backups are kept.

Backups are named `familydb-<timestamp>.sqlite3`. The [safety backup](/wiki/reference/glossary#safety-backup) that a restore or an [upgrade](/wiki/operations/upgrade-and-rollback) takes first uses the same folder and name, so it is pruned on the same schedule: an upgrade's backup is gone after about two weeks. The prune deletes anything named `familydb-*.sqlite3` in that folder, whoever put it there. To keep one longer, copy it out.

Nothing alerts you when the nightly backup stops. Once a week, run `sudo /opt/familydb/scripts/maintain.sh status` and read the `Last backup` line.

## Take a backup by hand

```bash
sudo /opt/familydb/scripts/maintain.sh backup
```

It checks there is room (the database's size plus 50 MB), takes SQLite's online backup, which is consistent even while FamilyDB answers a message, and checks that the file is not empty. On any failure it removes the incomplete file, so a half-written backup never looks usable. It ends with:

```text
✓ Backup written (14M), by SQLite's online backup, which is safe while the bot runs.
...
✓ Backup saved
    File         /opt/familydb/backups/familydb-<timestamp>.sqlite3
    Size         14M, readable only by its owner
```

Under it come the two commands that bring a copy to your own computer, with the real file name filled in.

Use this and not `familydb db backup DEST` for a backup you keep: it makes the file owner-only and works on Docker.

## Keep a copy off the server

A backup on the same disk goes with the disk. Once a month, and after anything you would hate to lose, fetch one to your own computer. `maintain.sh backup` prints the first two commands with the real file name filled in.

On the server, give yourself a copy:

```bash
sudo install -m 600 -o "$USER" /opt/familydb/backups/familydb-XXXX.sqlite3 ~/
```

On your computer:

```bash
scp you@server:familydb-XXXX.sqlite3 .
```

On the server, once it has arrived:

```bash
rm ~/familydb-XXXX.sqlite3
```

Keep the copy on your computer somewhere private.

## Restore a backup

Restore only a file taken by this version of FamilyDB or an older one. `restore` reads the backup's database version first and refuses one from newer code, before it stops FamilyDB or replaces anything. It says to [upgrade](/wiki/operations/upgrade-and-rollback) first or to use an older backup. If you must go back past an upgrade, follow [Upgrade and rollback](/wiki/operations/upgrade-and-rollback#if-it-goes-wrong).

Restoring is also the only way to bring back what was removed for good. Taking a person off the list, for example, is undone only by restoring an older backup.

1. List the backups, newest first, and pick one:

```bash
sudo ls -lt /opt/familydb/backups/ | head
```

2. Restore it. A file from anywhere else works too:

```bash
sudo /opt/familydb/scripts/maintain.sh restore /opt/familydb/backups/familydb-XXXX.sqlite3
```

In order, `restore` checks the file first: it must pass SQLite's quick integrity check, be a FamilyDB database and be no newer than this code, and if it fails nothing is stopped or replaced. It then shows what it is restoring (the file, when it was taken and how long ago, its size) and what it replaces, the plan, and what will be lost: everything FamilyDB was told since that backup was taken. It asks `Replace the database with that backup?`, and you answer `y`. Then, as numbered steps, it takes a safety backup of the database it is about to replace, so the restore can be undone; stops FamilyDB, which on a virtualenv install can take up to 150 seconds if a model call is in progress (`TimeoutStopSec=150`); copies the backup into place, clears the old write-ahead files and sets the owner and mode; applies any migrations the backup lacks; and starts FamilyDB again.

> **Everything FamilyDB was told since that backup was taken is gone.** The safety backup is the way back.

3. Run the check:

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

On a virtualenv install the restore ends like this, and the check shows no `✗`:

```text
✓ It came back up, and the page answers.
...
✓ Restored from 2026-09-14 03:15
    Restored     /opt/familydb/backups/familydb-XXXX.sqlite3
    Before       /opt/familydb/backups/familydb-YYYY.sqlite3

To undo this restore
    sudo /opt/familydb/scripts/maintain.sh restore /opt/familydb/backups/familydb-YYYY.sqlite3
```

`Before` is the safety backup, the database that was there before.

Settings changed on the web page and the saved keys come back with the database. The calendar key does not. Status then shows what is connected.

If the restore stops with `that backup is from a newer FamilyDB than this code`, nothing was changed: [upgrade](/wiki/operations/upgrade-and-rollback) first, then restore again, or pick an older backup. If the restore fails partway, FamilyDB is left stopped. The safety backup is the newest `familydb-*.sqlite3` in the folder (`sudo ls -t /opt/familydb/backups | head -1`); restore it the same way to get back to where you were.

## If the server is gone

You need a backup that is somewhere other than the dead server. Everything else comes back.

1. Install the same version, or a newer one, on the new server, using the block in `docs/INSTALL.md`. To match an older version, add `--ref <tag>` to the `bootstrap.sh` line before you paste.

2. On your computer, copy the backup across:

```bash
scp familydb-XXXX.sqlite3 you@new-server:~
```

3. On the new server, restore it:

```bash
sudo /opt/familydb/scripts/maintain.sh restore ~/familydb-XXXX.sqlite3
```

4. Recreate what the backup does not hold. The installer made a new `.env` with a new shared password and `WEB_DOMAIN`; copy back any other line you kept only there. Model-company keys and the Telegram token saved on Settings, and everyone's own passwords, came back with the database. Make a new Google key and connect the calendar on [Connections](/wiki/controls/settings/connections#google-calendar).

5. If you use a domain, point its DNS record at the new server. If Caddy has no certificate yet, run `sudo /opt/familydb/scripts/maintain.sh https <domain>`.

6. Run `sudo /opt/familydb/scripts/maintain.sh check`.

Calendar events are also in Google, which holds a second copy of every plan. A restore you have never tried is only a hope: once, on a spare machine, run these steps and look at Status.

## Docker

On a Docker install `maintain.sh` runs the backup and restore inside the container for you. The files stay on the host, in `/opt/familydb/backups` and `data/`.

## Why it is built this way

One file means a backup is a copy and a restore is a copy back, with no export to get wrong. The prune follows the success so the schedule can never leave you with no backups because the backup quietly stopped working. The restore checks the file and saves what it replaces because the usual reason for a restore is a bad day, when it is easiest to pick the wrong file.
