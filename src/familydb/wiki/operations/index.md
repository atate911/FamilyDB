# Running it over time

Installing it, keeping it healthy, backing it up, upgrading it, and putting it
right when something is wrong. `RUNBOOK.md` and `docs/INSTALL.md` are the exact
procedures; this page is the map and the things worth knowing before you need them.

## Installing

One block of commands, in step 1 of `docs/INSTALL.md`, makes a deploy key, shows
where to add it on GitHub, and runs `scripts/bootstrap.sh`, which runs
`scripts/install.sh`. The installer asks at most for a domain name, writes `.env`,
installs, migrates, puts HTTPS in front of the page with Caddy, and schedules
nightly backups, for Docker or a virtualenv. Every failure says what to do and that
running it again carries on. It prints a link and a password, and the page then walks
an admin through the rest: you, your password, an AI model, home, Telegram, the
family, the calendar.

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

Never upgrade with `git pull`: after an upgrade the checkout is on a detached
commit, and it would skip the backup and the dependencies.

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

The nightly backup runs at 03:15 with SQLite's online backup (safe while the bot
runs) and keeps 14 days by default. **Keep a copy off the server**: a backup on the
same disk is not a backup. A key saved on the Settings page lives in the database,
so it is in every backup.

## When something is wrong

- Start with `familydb doctor` (or `maintain.sh check`). It names what is wrong and how to fix it, and `--fix` puts right what it safely can.
- The **Status** page says what is connected, what the models have cost, and what has gone wrong. Admins with a Telegram id are also told on Telegram about the troubles only an admin can fix (a company out of credit, a key refused, the day's limit reached, Google shutting the bot out).
- Logs are in the system journal (or the container's logs under Docker). The Telegram token is removed from every log line.

### If an admin is locked out

This guide cannot be read without signing in, so these steps live here for the
admin who can still reach the server. On the server, `maintain.sh password` (or
`familydb password`) makes a new starting password for the first admin, or for
`NAME`, and prints it once. Signing in with it takes that person to a page where
they choose their own. Nothing on the server needs editing: passwords are only
stored as hashes.

### When a secret gets out

- *An API key*: revoke it in the company's console, make a new one, and enter it on the Settings page or in `.env`.
- *The Telegram token*: `/revoke` in BotFather makes a new one and kills the old; paste it on the Settings page.
- *Somebody's password*: they change their own on Your password, or an admin makes a new starting password (which signs them out everywhere).
- *A lost phone*: a new starting password for that person signs them out everywhere; "Sign everyone out" on the Sign-in and security page ends every sign-in.
- *The whole server*: the database holds everything the family said. Rotate all of the above and assume anything stored on the Settings page was read.

## In this section

**Still to come:** install and first run, configuration (every `.env` key), backup
and restore, upgrade and rollback, diagnostics, troubleshooting by symptom, the
firewall, and removing it.

Exact procedures: `RUNBOOK.md` and `docs/INSTALL.md`.
