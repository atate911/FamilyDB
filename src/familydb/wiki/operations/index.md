# Running it over time

Installing it, keeping it healthy, backing it up, upgrading it, and putting it
right when something is wrong. `RUNBOOK.md` and `docs/INSTALL.md` are the exact
procedures; this page is the map and the things worth knowing before you need them.

## Installing

One block of commands, in step 1 of `docs/INSTALL.md`, makes a deploy key, shows
where to add it on GitHub, and runs the installer. It asks at most for a domain name,
puts HTTPS in front of the page, and schedules nightly backups; the page then walks an
admin through the rest. [Install and first run](/wiki/operations/install) says what it
changes on the server and why, and how to check that it worked.

## Looking after the server

`scripts/maintain.sh` says what it will change before it does. Its commands:

| Command | What it does |
|---|---|
| `status` | Running? Database size? Last backup? |
| `check` | The full `familydb doctor` |
| `backup` / `restore FILE` | A backup now; put one back (checks it first, stops the bot, backs up what it replaces) |
| `upgrade` | Backs up, moves to the newer code, reinstalls, migrates, restarts, and prints how to go back |
| `logs [N]` / `restart` | Read the journal; restart the bot |
| `schedule-backups` | The nightly backup |
| `https` / `port` | Move the public HTTPS port, or FamilyDB's own |
| `password [NAME]` | A new starting password for somebody who forgot |

Never upgrade with `git pull`. [Upgrade and rollback](/wiki/operations/upgrade-and-rollback)
says what `upgrade` does and how to go back.

## Where things live

Everything is one folder, `/opt/familydb`, and its `data/` folder is readable by the
bot's user alone.

| Path | What it is | In the backups? |
|---|---|---|
| `data/familydb.sqlite3` | Everything: messages, ideas, plans, places, settings changed from the page, any key stored there | yes, it is the backup |
| `data/google_key.json` | The calendar service account's key | no; make a new key |
| `data/web_secret` | Signs the login cookie; "Sign everyone out" replaces it | no |
| `.env` | The page's address and shared password, anything not set from the page | no; keep your own copy |
| `backups/` | The nightly backups | they are the backups |

The nightly backup runs at 03:15 and keeps 14 days by default. **Keep a copy off the
server**: a backup on the same disk is not a backup. A key saved on the Settings page lives
in the database, so it is in every backup. [Backup and restore](/wiki/operations/backup-and-restore)
has the rest.

## When something is wrong

- Start with `familydb doctor` (or `maintain.sh check`). It names what is wrong and how to fix it, and `--fix` puts right what it safely can.
- The **Status** page says what is connected, what the models have cost, and what has gone wrong. Admins with a Telegram id are also told on Telegram about the troubles only an admin can fix (a company out of credit, a key refused, the day's limit reached, Google shutting the bot out).
- Logs are in the system journal (or the container's logs under Docker). The Telegram token is removed from every log line.

### If an admin is locked out

This guide cannot be read without signing in, so the one command is here for the admin who
can still reach the server: `sudo /opt/familydb/scripts/maintain.sh password` makes a new
starting password for the first admin (or `password NAME` for somebody else) and prints it
once. [Recovery](/wiki/operations/recovery) has every case and what each does.

### When a secret gets out

Revoke it at its source, make a new one, and put the new one on the Settings page or in
`.env`; for a person's password, make a new starting password. The table is in
[Recovery](/wiki/operations/recovery#when-a-secret-has-been-exposed).

## In this section

- [Install and first run](/wiki/operations/install): the three steps, what the installer changes and why
- [Backup and restore](/wiki/operations/backup-and-restore): the nightly backup, taking one, copying it off, putting one back
- [Upgrade and rollback](/wiki/operations/upgrade-and-rollback): one command forward, three to go back
- [Recovery: when somebody cannot sign in](/wiki/operations/recovery): a new starting password, lockouts, a lost phone

**Still to come:** configuration (every `.env` key), diagnostics, troubleshooting by
symptom, the firewall and host hardening, and cost.

Exact procedures: `RUNBOOK.md` and `docs/INSTALL.md`.
