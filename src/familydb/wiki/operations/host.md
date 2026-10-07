# The server

This page says what the install put on the server, how the service behaves, what grows, and how to take FamilyDB off again. For the web page's HTTPS, ports and firewall, see [HTTPS and the firewall](/wiki/operations/https-and-firewall). For logs, see [Diagnostics](/wiki/operations/diagnostics#logs).

## Everything the install put on the server

The installer records each change outside `/opt/familydb` in `/var/lib/familydb-install` as it makes it, so `uninstall.sh --from-zero` can undo exactly that. [Install and first run](/wiki/operations/install#what-the-installer-changes-and-why) gives the summary.

| Item | Owner | What it is, and why |
|---|---|---|
| `/opt/familydb` code: `src/`, `scripts/`, `deploy/`, `.git` | root; others cannot write | The program. FamilyDB runs it but cannot change it, so a mistake in it cannot rewrite its own code |
| `/opt/familydb/.venv/` | root, readable by `familydb` | The Python environment, built by `uv` and rebuilt by each upgrade. uv's cache and Python sit in `.cache/` and `.local/` beside it |
| `/opt/familydb/.env` | `familydb`, mode 600 | The web page's address, the shared password and any key you put there. If you decline to keep it when you rerun `install.sh`, the old one is saved as `.env.<timestamp>.bak`, root-owned, mode 600 |
| `/opt/familydb/data/` | `familydb`, mode 700 | The database, `google_key.json` and `web_secret`: everything the family tells it |
| `/opt/familydb/backups/` | folder owned by `familydb`; files mode 600 | The nightly and safety backups. [Backup and restore](/wiki/operations/backup-and-restore#what-is-in-a-backup-and-what-is-not) says what a backup holds |
| `/opt/familydb/caddy/` | Docker with a domain only | Caddy's certificate and private key, kept apart from `data/` so FamilyDB's container cannot read the key |
| The `familydb` account | system account | No password and no login, home `/opt/familydb`. FamilyDB runs as it, so a mistake cannot reach the rest of the machine |
| `/etc/systemd/system/familydb.service`, and its link in `multi-user.target.wants` | root | The service, so FamilyDB starts at boot and restarts if it stops. Virtualenv installs only |
| `/etc/caddy/Caddyfile` | root | One site block that passes the web page to FamilyDB. Not written with `--local-only` |
| `/var/lib/caddy/.local/share/caddy` | `caddy` account | Caddy's certificates, outside the install |
| Root's crontab | root | One line, tagged `familydb-maintain-backup`: the nightly backup at 03:15 |
| `/root/familydb_deploy` and `.pub` | root, mode 600 | The deploy key, so upgrades can fetch the code. Deleting it on GitHub ends the server's access |
| `/var/lib/familydb-install` | root only | The record of each change, a copy of any file the installer replaced, and GitHub's host key |
| `/var/log/familydb-bootstrap.log`, `-install.log`, `-maintain.log`, `-uninstall.log` | root, mode 600 | A transcript of each run, the files to send if you need someone to look. Nothing rotates them |
| `/var/backups/familydb` | root | Created only by `uninstall.sh --purge`, which leaves one last backup there |
| Packages and tools | root | `git`, `curl`, `ca-certificates` and `tzdata` if missing, `uv` in `/usr/local/bin`, and `cron`, Caddy or Docker when you need them. For a public address with no domain, a Caddy older than 2.10 is replaced from Caddy's own apt repository |
| A `ufw` rule for ports 80 and 443 | root | Only on a virtualenv install, if `ufw` is already on and you did not pass `--local-only` |

On Docker, `data/` belongs to uid 1000 (the container's `familydb`), `.env` stays with whoever ran the installer, and the image is `familydb:local`.

## The service

A virtualenv install runs one [systemd](/wiki/reference/glossary#systemd) unit, a copy of `deploy/familydb.service`. It runs `/opt/familydb/.venv/bin/familydb run` as `familydb` with `.env` as its environment file. That one process serves the web page, polls Telegram and runs every scheduled job.

```bash
sudo systemctl status familydb
sudo /opt/familydb/scripts/maintain.sh status
sudo /opt/familydb/scripts/maintain.sh restart
```

| Setting | What it does |
|---|---|
| `Restart=on-failure`, `RestartSec=5` | Restarts FamilyDB 5 seconds after it fails. A stop you asked for stays stopped |
| `TimeoutStopSec=150` | Waits up to 150 seconds for a clean stop before killing it. A model call in progress can be slow to notice, and nothing is lost if it is killed |
| Hardening (`ProtectSystem=strict`, no capabilities, `UMask=0077`) | The file system is read-only to FamilyDB except `data/`, so `FAMILYDB_PATH` must stay in `data/`. `WEB_PORT` must be 1025 or above. `ProtectHome=true` hides `/home`, so the installer uses `read-only` for a checkout there |

An upgrade does not rewrite the unit; see [Known limits](/wiki/reference/known-limits#an-upgrade-does-not-rewrite-the-service-file). After any edit to it, run `sudo systemctl daemon-reload` and restart.

## Docker instead

`--mode docker` runs the `bot` container, plus `caddy` when a domain is set, from `docker-compose.yml`. There is no systemd unit.

- `bot`: image `familydb:local`, built from the `Dockerfile` (uid 1000); `./data` is mounted as `/data`; the port is `127.0.0.1:8080:8080`, this machine only.
- `caddy`: `caddy:2-alpine`, only with the `tls` profile (the installer writes `COMPOSE_PROFILES=tls` in `.env` when you give a domain); `./caddy` is mounted as `/data`; ports `80:80` and `443:443`, where the host side of 443 is `WEB_PUBLIC_PORT`.

Both restart `unless-stopped`. `WEB_PORT` in `.env` moves FamilyDB's port. The compose file sets no stop timeout, so Docker's default applies, not 150 seconds. `maintain.sh` takes the same commands, except that `https` only moves the port of a web page already on HTTPS.

## Disk and memory

[Install and first run](/wiki/operations/install#what-you-need) has the minimums and who checks them. What grows afterward is the database (no job prunes messages or the records of model and tool calls), `backups/` (about two weeks of full copies by default), and the journal, Docker's logs and its images (`docker system df` shows them).

On `no space left on device`, trim the journal first, then run `sudo apt-get clean`, then remove old backups. `maintain.sh schedule-backups --keep-days N` sets how long backups live.

```bash
sudo journalctl --vacuum-size=200M
sudo apt-get clean
```

A step that ends with only `Killed` ran out of memory. Confirm with `sudo dmesg -T | grep -i 'killed process'`, add swap, and run the install again. If `fallocate` fails on your file system, the `dd` form works everywhere:

```bash
sudo fallocate -l 1G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Updates and reboots

FamilyDB's code and dependencies change only through [`maintain.sh upgrade`](/wiki/operations/upgrade-and-rollback); the operating system is yours. Turn on security updates at least:

```bash
sudo apt update && sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

That covers your distribution's security updates, not Caddy's own repository, which the installer adds only for a web page at a public address with no domain when the system's Caddy is older than 2.10. Run `sudo apt update && sudo apt upgrade` now and then. On Docker, an upgrade does not fetch a newer `caddy:2-alpine`.

After a reboot the service comes back by itself: the installer enables it at boot, and Docker's `unless-stopped` does the same once Docker is up. `maintain.sh status` and the doctor both say whether it is enabled at boot. On every start FamilyDB applies any pending migrations, then:

- Scheduled jobs: They live in memory, so 60 seconds after start a catch-up runs the follow-ups, the plan check and the weekend ideas job (the last only if today is its day and its hour has passed), and the daily model check if a day has gone by. A repeat does nothing new.
- Reminders: One that fell due while FamilyDB was down goes out once it is back, worded as late.
- A message in the middle of a turn: Its [lease](/wiki/reference/glossary#lease) lapses and the retry job answers it, and sends any reply that was stored but not delivered. [When a message cannot be answered](/wiki/controls/settings/messages#when-a-message-cannot-be-answered) has the numbers.

## Taking it off again

> **`--purge` and `--from-zero` delete the database.** Run `maintain.sh backup` and copy the file off the server first; see [Backup and restore](/wiki/operations/backup-and-restore#keep-a-copy-off-the-server).

| Command | Removes | Keeps |
|---|---|---|
| `uninstall.sh` | The service, the nightly backup line, and the rebuildable virtualenv (on Docker, the containers and image) | The code, `.env`, `data/`, `caddy/` and the backups, so reinstalling picks up where it left off |
| `uninstall.sh --purge` | All of FamilyDB: the database, the `familydb` account and the backups in `/opt/familydb/backups` | One last backup, written to `/var/backups/familydb` (or `--backup-to DIR`) |
| `uninstall.sh --from-zero` | All of that, and what the install did around it | Nothing, unless you give `--backup-to DIR` |

Run it as `sudo /opt/familydb/scripts/uninstall.sh <option>`.

`--from-zero` puts the server back as it was before FamilyDB, for trying the install again from the beginning. It undoes what the installer recorded, plus leftovers an older or by-hand install could leave: Caddy only when it serves nothing but FamilyDB, `uv`, the deploy key and copies of the code. `--purge` and `--from-zero` ask twice: a yes-or-no after listing by name everything they will remove (Enter means no), then you type `remove everything`. `--dry-run` shows the list and removes nothing. `--force` skips both questions and deletes at once, so it is for scripts.

Things outside the server are yours to remove: the deploy key on GitHub, the Telegram bot (`/deletebot` in BotFather), the Google service account, the DNS record and the API keys at each company, which work until revoked.
