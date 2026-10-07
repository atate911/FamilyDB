# Install and first run

Installing FamilyDB is three steps: paste one block into the server's terminal, open
the page it prints, and follow the setup on the page. The installer does the server
side and says what it is doing; the page does the rest. This page explains what the
install changes on the server and why, the choices you can make, how to check that it
worked, and how to take it off again. The block itself and the step-by-step commands
are in `docs/INSTALL.md`, which is where to copy them from.

## What you need

- **A server** running Ubuntu or Debian (the guide is written for Ubuntu 24.04 or 26.04 and Debian 12; the installer warns on anything else), with about 1 GB of memory and about 900 MB of free disk. You reach its terminal over SSH, with the login your hosting provider gave you; root is fine.
- **GitHub**: you must be signed in as the owner of the FamilyDB repository, because the code is in a private repository.
- **An AI company account** (OpenAI, Anthropic or Google). A family's use costs a few dollars a month, and the setup page says where to get a key.

## The three steps

### 1. Paste the block

The block does the one thing the installer cannot do alone: it makes a **deploy key**
(an SSH key that can read this one repository and nothing else, with write access left
off) and shows you a link and a line of text. On GitHub, paste the line under the
repository's **Settings → Deploy keys** and press **Add key**, then press Enter on the
server. After that it lists what it will change on the server and asks whether to go
ahead, and whether you have a domain name for the page (Enter if not).

The key stays at `/root/familydb_deploy` so that
[upgrades](/wiki/operations/upgrade-and-rollback) can fetch new versions. To end the
server's access to the code, delete the key on GitHub.

To use an installer option, add it to the end of the `bootstrap.sh ...` line in the
block **before you paste it**.

### 2. Open the page

The installer ends with an address and a password. Open the address in any browser and
sign in with that password. It is only for getting in the first time: the setup's
second step has you choose your own, and until you do, everybody shares this one. Lost
it? On the server, `sudo /opt/familydb/scripts/maintain.sh password` makes a new one.

- **The browser says the connection is not private.** If the server's address is a private one, or the certificate authority could not reach it, the installer makes its own certificate and the browser warns once. The connection is still encrypted: choose Advanced, then continue. A domain name removes the warning for good.
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
admin to the setup. A step counts as done when its result is in place, so nothing is
lost if you leave and come back.

## What the installer changes, and why

The installer lists these and asks before it changes the server, apart from the key and
`git` in step 1. It records each change as it makes it, in `/var/lib/familydb-install`.

| What | Why |
|---|---|
| Installs `git`, `curl`, `ca-certificates` and `tzdata` if missing | To fetch the code, check HTTPS certificates, and know what "this weekend" means where you live |
| Installs `uv` | It fetches the Python FamilyDB needs and builds its environment; the system Python is left alone |
| Creates a system account, `familydb`, with no password and no login | The bot runs as this, so a mistake in it cannot reach the rest of the machine |
| Puts the program in `/opt/familydb` | One folder holds the program, configuration and database, which keeps backing up and removing simple |
| Writes `/opt/familydb/.env`, readable only by `familydb` | The first password and the page's address; everything else is set on the page |
| Creates the database, `/opt/familydb/data/familydb.sqlite3` | Everything the family tells it lives in that one file |
| Enables a `familydb` service in systemd | So it starts at boot and restarts if it stops |
| Adds a nightly backup to root's crontab (installing `cron` if it is missing) | So a bad day can be undone. Copy the backups off the server now and then: [Backup and restore](/wiki/operations/backup-and-restore) |
| Installs Caddy and writes its configuration (not with `--local-only`) | Caddy puts HTTPS in front of the page and renews its certificate, so the password never crosses the network in the clear. It may add Caddy's own apt repository when the system's version is too old |
| Opens ports 80 and 443 in `ufw`, only if it is already on (not with `--local-only`) | So browsers can reach the page; the bot needs nothing else inbound |

It does not touch your SSH configuration, the system Python, any other service, or
anything in a home directory. Running it again is safe: it installs only what is missing,
keeps `.env` and the database, and picks up where a failed run stopped. The install lives
in `/opt` rather than a home directory because the `familydb` account cannot enter one,
and the installer refuses to set up a service it knows cannot run.

## Choices you can make

- **A domain name.** Add an A record at the registrar pointing at the server, then run `sudo /opt/familydb/scripts/maintain.sh https family.example.com`. Typing the name when the installer asks does the same. `docs/INSTALL.md`, "A domain name instead of the address", has the details.
- **Keep the page off the internet.** Add `--local-only` to the installer. You then reach the page through an SSH tunnel, opened **from your own computer, not the server**: `ssh -L 8080:127.0.0.1:8080 you@server`, then `http://127.0.0.1:8080/` in a browser on that computer. `maintain.sh https` moves you to a public link later.
- **Another port.** `sudo /opt/familydb/scripts/maintain.sh https --port random` serves the page on a port scans rarely try. It prints the new address: **bookmark it, and allow that port in your provider's firewall too, or the page will not open.** To undo: `https --port 443`. It keeps the page out of casual sweeps of the usual ports and is no substitute for good passwords.
- **Docker instead of a virtualenv.** `--mode docker`. Docker is installed for you, and the bot and Caddy run as containers instead of a systemd service. Without a domain the page is reachable from the server only, and HTTPS needs `WEB_DOMAIN` set in `.env` (`docs/INSTALL.md` says how). `maintain.sh https DOMAIN` does not work with Docker; it only moves the port of a page already on HTTPS.
- **Other options.** `--dry-run` says what would happen and changes nothing; `--target` installs somewhere other than `/opt/familydb` (not under `/home`); `--ref` installs a particular tag, branch or commit; `--yes` takes every default. `bootstrap.sh --help` lists them all.

Without `--ref`, which version it installs depends on `CHANGELOG.md`: while the newest
version's heading says "in progress" it installs the default branch, and once that heading
has a date, the newest release tag.

## Check that it worked

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

This runs `familydb doctor`, which checks the settings, the permissions on `.env`, disk,
database and schema, the family, keys and models, Telegram, the calendar, the weather,
lookups, the digest, the web page and the service, and prints a fix under anything wrong.
For the deeper check (it also asks Telegram whether its token works, asks Claude or Gemini
whether the key works by counting tokens, which is free, and checks that the pages the
setup links to still answer), run the doctor yourself:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor --online
```

OpenAI, the default, cannot count tokens without answering, so for it the first real
message is the check. After setup steps 1 and 3 (you, and a model), send one from the
page's chat, or from the server:

```bash
cd /opt/familydb
sudo -u familydb .venv/bin/familydb chat "we should try that new ramen place on Main St sometime"
sudo -u familydb .venv/bin/familydb chat "tell me about #1"
sudo -u familydb .venv/bin/familydb db status
```

After the second message `db status` usually shows `cache_read` above zero, meaning the
prompt cache is saving the cost of the repeated start of each request. OpenAI and Gemini
cache on their own and not every repeat is a hit; if it stays at zero, see `RUNBOOK.md`
section 13. The Status page shows who answers, what is connected and what it has cost,
and asks no model.

## If it goes wrong

The installer stops and says what went wrong and what to do. Once that is sorted, paste
the same block again. Everything it did is in `/var/log/familydb-bootstrap.log`, the file
to send if you need someone to look. `docs/INSTALL.md` has a symptom-by-symptom
troubleshooting section for the server side: the clone failing, the service starting and
stopping, no space left, a port in use, and others.

## Taking it off again

**Back up and copy the file off the server first** (`maintain.sh backup`; see
[Backup and restore](/wiki/operations/backup-and-restore)): two of these three delete the
database.

| Command | Removes | Keeps |
|---|---|---|
| `uninstall.sh` | the service, the nightly backup schedule, and the rebuildable virtualenv (on Docker, the containers and image) | the code, `.env`, `data/` and the backups, so reinstalling picks up where it left off |
| `uninstall.sh --purge` | all of FamilyDB, including the database, the `familydb` account and the nightly backups in `/opt/familydb/backups` | one last backup, written to `/var/backups/familydb` (or `--backup-to DIR`) |
| `uninstall.sh --from-zero` | all of that, and what the install did around it | nothing, unless `--backup-to DIR` is given |

`--from-zero` puts the server back as it was before FamilyDB, for trying the install again
from the beginning. It undoes what the installer recorded, plus the leftovers an older or
by-hand install could leave (Caddy only when it serves nothing but FamilyDB, `uv`, the
deploy key, copies of the code). Like `--purge` it asks twice: a yes-or-no after listing by
name everything it will remove (Enter means no), then typing `remove everything`.
`--dry-run` shows the list and removes nothing; `--force` skips both questions and deletes
at once, so it is for scripts. Things outside the server are yours to remove: the deploy key
on GitHub, the Telegram bot (`/deletebot` in BotFather), the Google service account, and
the API keys at each company, which work until revoked.
