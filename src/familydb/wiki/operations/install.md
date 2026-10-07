# Install and first run

## Overview

Installing FamilyDB is three steps and about twenty minutes: paste one block into
the server's terminal, open the page it prints, and follow the setup on the page.
The installer does the server side and says what it is doing; the page does the
rest. This page explains what the install does, what it changes on the server and
why, and how to tell that it worked. The exact block to paste is in step 1 of
`docs/INSTALL.md`, which is the source of truth for the commands.

## What you need

- A server running Ubuntu 24.04 or 26.04, or Debian 12, with at least 1 GB of memory (the smallest plan at most hosting providers). You must be able to log in to it; as root is fine.
- To be signed in to GitHub as the owner of the FamilyDB repository, because the code is in a private repository.
- An account with an AI company (OpenAI, Anthropic or Google). A family's use costs a few dollars a month, and the setup page says where to get a key.

## The three steps

### 1. Paste the block

The block does the one thing the installer cannot do alone: it makes a **deploy
key** (an SSH key that can read this one repository and nothing else, with write
access left off) and shows you a link and a line of text. On GitHub you paste the
line under the repository's **Settings → Deploy keys** and press **Add key**; then
you press Enter on the server. From there it installs everything, asking only
whether to go ahead, once it has listed what it will change, and whether you have a
domain name for the page (press Enter if not).

The key stays at `/root/familydb_deploy` so that [upgrades](/wiki/operations/upgrade-and-rollback)
can fetch new versions. To take the server's access to the code away, delete the key
on GitHub.

### 2. Open the page

The installer ends with an address and a password. Open the address in any browser
and sign in with that password. That password is only for getting in the first
time: the first admin replaces it in the setup, and from then on everybody signs in
as themselves.

Two things commonly happen here:

- **The browser says the connection is not private.** With no domain, the installer could not get a certificate from a public authority and made its own. The connection is still encrypted; choose Advanced, then continue. Giving the page a domain removes the warning for good (see [Choices you can make](#choices-you-can-make)).
- **The page does not open at all.** Almost always the hosting provider's own firewall, which is separate from the server's. Allow incoming TCP on ports 80 and 443, then run `sudo /opt/familydb/scripts/maintain.sh https`, which also gets the page a real certificate if the first try could not.

### 3. Follow the setup

The page opens on its setup: seven short steps, each saying why it matters. You can
skip any and come back, and the home page lists what is left.

| Step | Status | What you need |
|---|---|---|
| Yourself | needed | your name |
| Your own password | recommended | |
| An AI model | needed | an account with OpenAI, Anthropic or Google, and a key |
| Where home is | recommended | your town |
| Telegram | optional | Telegram on your phone |
| The rest of the family | optional | |
| Google Calendar | optional | any Google account, to make a service account and share the family calendar with it |

Until somebody is on the family list and a model can answer, the home page sends an
admin to the setup. Progress is read from what is configured, never stored, so a
step is done when the thing it sets up works.

## What the installer changes, and why

Before it changes anything it lists these and asks. It records each change as it
makes it, in `/var/lib/familydb-install`.

| What | Why |
|---|---|
| Installs `git`, `curl`, `ca-certificates` and `tzdata` if they are missing | To fetch the code, check HTTPS certificates, and know what "this weekend" means where you live |
| Installs `uv` | It fetches the Python version FamilyDB needs and builds its environment; the system Python is left alone |
| Creates a system account, `familydb`, with no password and no login | The bot runs as this, so a mistake in it cannot reach the rest of the machine |
| Puts the program in `/opt/familydb` | One folder holds the program, configuration and database, which keeps backing up and removing simple |
| Writes `/opt/familydb/.env`, readable only by `familydb` | The first password and the page's address; everything else is set on the page |
| Creates the database, `/opt/familydb/data/familydb.sqlite3` | Everything the family tells it lives in that one file |
| Enables a `familydb` service in systemd | So it starts at boot and restarts if it stops |
| Adds a nightly backup to root's crontab | So a bad day can be undone ([Backup and restore](/wiki/operations/backup-and-restore)) |
| Installs Caddy and writes its configuration | Caddy puts HTTPS in front of the page and renews its certificate, so the password never crosses the network in the clear |
| Opens ports 80 and 443 in `ufw`, if it is on | So browsers can reach the page; the bot needs nothing else inbound |

It does not touch your SSH configuration, the system Python, any other service, or
anything in a home directory. Running it again is safe: it installs only what is
missing, keeps `.env` and the database, and picks up where a failed run stopped.
The installer refuses to install a service that cannot run, such as one pointed at a
home directory the `familydb` account cannot enter, which is why the install lives
in `/opt`.

## Choices you can make

- **A domain name.** Add an A record pointing at the server, then `sudo /opt/familydb/scripts/maintain.sh https family.example.com`. Typing the name when the installer asks does the same. This sets `WEB_DOMAIN`, `WEB_TRUST_PROXY=true` and `WEB_HOST=127.0.0.1` in `.env`, so the page listens only to Caddy on the same machine.
- **Off the internet.** Add `--local-only` to the installer and reach the page through an SSH tunnel (`ssh -L 8080:127.0.0.1:8080 you@server`). You can move to a public link later with `maintain.sh https`.
- **Another port.** `maintain.sh https --port random` serves the page on a port that scans rarely try. It keeps the page out of casual sweeps of the usual ports; it is no substitute for good passwords.
- **Docker instead of a virtualenv.** `--mode docker`. The rest works the same, and `maintain.sh` takes the Docker path automatically.
- **Other installer options.** `--dry-run` says what would happen and changes nothing; `--target` and `--user` move the install and rename its account; `--ref` installs a particular tag, branch or commit; `--yes` takes every default. `bootstrap.sh --help` lists them all.

Without `--ref`, which version it installs depends on `CHANGELOG.md`: while the
newest version's heading says "in progress" it installs the default branch, and
once that heading has a date, the newest release tag.

## Check that it worked

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

This runs `familydb doctor`, which checks the settings, the permissions on `.env`,
disk, database and schema, the family, keys and models, Telegram, the calendar, the
weather, lookups, the digest, the web page and the service, and prints a fix under
anything wrong. With `--online` it also asks Telegram whether its token works and
asks Claude or Gemini whether the key works (by counting tokens, which is free).
OpenAI, the default, cannot count tokens without answering, so for it the first real
message is the check. Then send one: on the page's chat, or from the server:

```bash
cd /opt/familydb
sudo -u familydb .venv/bin/familydb chat "we should try that new ramen place on Main St sometime"
sudo -u familydb .venv/bin/familydb chat "tell me about #1"
sudo -u familydb .venv/bin/familydb db status
```

After the second message, `db status` should show `cache_read` above zero. That
means the prompt cache is working and each message is not paying for the whole
prefix again. The Status page shows who answers, what is connected and what it has
cost, and asks no model.

## If it goes wrong

The installer stops and says what went wrong and what to do. Once that is sorted,
paste the same block again; it keeps what already worked. Everything it did is in
`/var/log/familydb-bootstrap.log`, the file to send if you need someone to look.
`docs/INSTALL.md` has a symptom-by-symptom troubleshooting section for the server
side (the clone failing, the service starting and stopping, no space left, a port in
use, and others).

## Taking it off again

| Command | Removes | Keeps |
|---|---|---|
| `uninstall.sh` | the service and the installed program | `.env`, the database and the backups, so reinstalling picks up where it left off |
| `uninstall.sh --purge` | all of FamilyDB, including the database and its account | a backup of the database in `/var/backups/familydb` |
| `uninstall.sh --from-zero` | all of that, and everything the install did around it | nothing, unless `--backup-to DIR` is given |

`--from-zero` undoes exactly what the installer recorded, so the server is as it was
before FamilyDB, which is for trying the install again from the beginning. Like
`--purge` it asks twice, once after listing by name everything it will remove and
once by making you type `remove everything`. `--dry-run` shows the list and removes
nothing. Things outside the server are yours to remove: the deploy key on GitHub,
the Telegram bot (`/deletebot` in BotFather), the Google service account, and the
API keys at each company, which work until revoked.

## Why it is built this way

The install is deliberately small and reversible. One folder and one account keep
backing up, upgrading and removing simple. Caddy handles certificates so nobody
manages them by hand. Nothing the family would change later lives in a file: the
installer writes only what the page cannot (the first password and the page's
address), and the setup walks the rest on the page, where a family member can
change it from a phone.
