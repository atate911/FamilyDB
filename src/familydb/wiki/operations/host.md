# The server

This page says what FamilyDB puts on its server and how to look after it. [Install and first run](/wiki/operations/install) has the table of what the installer changes; this page adds who owns what, how the service behaves, what must be open, and what grows.

## What is in /opt/familydb

| Path | Owner and mode | What it is |
|---|---|---|
| `src/`, `scripts/`, `deploy/`, `.git` | root; others cannot write | The code. Bootstrap, and each virtualenv upgrade, run `chmod -R go-w`, so the bot runs its code but cannot change it |
| `.venv/` | root, readable by `familydb` | The Python environment, built by `uv`; it can be rebuilt. uv's cache and any Python it fetched are in `.cache/` and `.local/` beside it, but upgrades do not set those paths, so later downloads may land in root's own cache |
| `.env` | `familydb`, `600` | The page's address, the first password, and any key you put there. Declining to keep it when you re-run `install.sh` saves the old one as `.env.<timestamp>.bak`, root-owned, `600` |
| `data/` | `familydb`, `700` | The database, `google_key.json` and `web_secret` |
| `backups/` | folder owned by `familydb` (its mode is not set), files `600` | The nightly and safety backups |
| `caddy/` | Docker's `tls` profile only | Caddy's certificate and private key |

On Docker, `data/` belongs to uid 1000 (the container's `familydb`) and `.env` stays with whoever ran the installer. [Backup and restore](/wiki/operations/backup-and-restore) says what a backup holds.

## The service

A virtualenv install runs one systemd unit, `/etc/systemd/system/familydb.service`, a copy of `deploy/familydb.service`. It runs `/opt/familydb/.venv/bin/familydb run` as `familydb`, with `.env` as its environment file; that one process serves the page, polls Telegram and runs every scheduled job.

```bash
sudo systemctl status familydb
sudo /opt/familydb/scripts/maintain.sh status      # also shows the version, memory and last backup
sudo /opt/familydb/scripts/maintain.sh restart
```

| Setting | What it does |
|---|---|
| `Restart=on-failure`, `RestartSec=5` | Restarts it five seconds after it fails. A stop you asked for stays stopped |
| `TimeoutStopSec=150` | Waits up to 150 seconds for a clean stop before killing it; a lookup mid-call can be slow to notice, and nothing is lost if it is killed |
| `ProtectSystem=strict`, `ReadWritePaths=/opt/familydb/data` | The file system is read-only to it except `data/` and its private `/tmp`. `FAMILYDB_PATH` must stay in `data/` |
| `UMask=0077`, `ProtectHome=true` | Its files are owner-only, and `/home` is hidden (`read-only` for a checkout there) |
| `NoNewPrivileges`, empty `CapabilityBoundingSet` and `AmbientCapabilities` | It gains nothing and has no capabilities, so `WEB_PORT` must be 1025 or above |
| `PrivateTmp`, `PrivateDevices` (a minimal `/dev`), `ProtectClock`, `ProtectHostname`, `ProtectKernel*`, `ProtectControlGroups`, `RestrictAddressFamilies` (Unix and IP sockets only), `RestrictNamespaces`, `RestrictRealtime`, `RestrictSUIDSGID`, `LockPersonality`, `SystemCallArchitectures=native`, `SystemCallFilter=@system-service` | What a bot has no need for, closed off |

Upgrades never rewrite the unit, so a hardening change in a later release reaches you only if you copy `deploy/familydb.service` over it again. After any edit, run `sudo systemctl daemon-reload` and restart.

## Docker instead

`--mode docker` runs the `bot` container, plus `caddy` when a domain is set, from `docker-compose.yml`. There is no systemd unit and none of the options above.

- **`bot`:** image `familydb:local`, built from the `Dockerfile` (Python 3.12, uid 1000); `./data` as `/data`; port `127.0.0.1:8080:8080`, this machine only.
- **`caddy`:** `caddy:2-alpine`, only with the `tls` profile (the installer writes `COMPOSE_PROFILES=tls` in `.env` when you give a domain); `./caddy` as `/data`; ports `80:80` and `443:443`, where the host side of 443 is `WEB_PUBLIC_PORT`.

Both restart `unless-stopped`. `WEB_PORT` in `.env` moves the bot's port. Caddy's data sits apart from `data/` on purpose, so the bot's container cannot read the certificate key. The compose file sets no stop timeout, so Docker's default applies, not 150 seconds. `maintain.sh` takes the same commands (including `logs` and `restart`), except that `https` only moves the port of a page already on HTTPS.

## HTTPS: Caddy

On a virtualenv install the installer puts Caddy on the machine and writes `/etc/caddy/Caddyfile`; `maintain.sh https` writes it again. The file is one site block, `reverse_proxy 127.0.0.1:<WEB_PORT>`: Caddy holds the certificate and passes the page on to the bot, which listens on the loopback only (`WEB_HOST=127.0.0.1`). Caddy replaces any `X-Forwarded-For` a visitor sends with the real address, which the sign-in lockout counts, and `WEB_TRUST_PROXY=true` makes the page believe one proxy hop. A Caddyfile that serves something else is left alone, and the installer prints the lines to add.

| The page is at | Certificate |
|---|---|
| A domain | Caddy gets a public one once the name points at the server and ports 80 and 443 are open |
| A public IPv4 address | A short-lived (six-day) Let's Encrypt certificate that Caddy renews. It needs Caddy 2.10 or newer, which the installer takes from Caddy's own apt repository when the system's is older. It waits 90 seconds for the certificate |
| A private address, no certificate within 90 seconds, or a Caddy still older than 2.10 | One Caddy signs itself (`tls internal`); each browser warns once |

Run `sudo /opt/familydb/scripts/maintain.sh https` again after opening a provider's firewall to try for a real certificate. Caddy keeps its certificates in `/var/lib/caddy/.local/share/caddy`, outside the install. On Docker, an address alone gets no HTTPS: the page stays on the machine until you set `WEB_DOMAIN`.

The page is on 443 unless `WEB_PUBLIC_PORT` says otherwise. `maintain.sh https --port random` (or a number from 1024 to 65535, or `443` to go back) moves it; `random` picks from 20000 to 29999. On a virtualenv install Caddy then serves HTTPS on that port alone, sends no redirect from 80, and listens on 80 only while a certificate authority checks the machine. Docker's Caddy still redirects 80 to 443, which then answers nothing. `maintain.sh port N|random` moves FamilyDB's own port behind Caddy; the General settings page shows both ports and cannot change them.

### nginx instead

If nginx is already on the server, install with `--local-only` so the installer leaves 80 and 443 to it. Then:

1. Copy `deploy/nginx-familydb.conf` into `/etc/nginx/sites-available/`, put your domain in, and link it into `sites-enabled`.
2. Run `certbot --nginx -d <domain>`, then `nginx -t` and reload nginx.
3. In `.env`, set `WEB_HOST=127.0.0.1`, `WEB_TRUST_PROXY=true` and a `WEB_PASSWORD` of 12 or more characters.

The file passes `Host` as `$http_host`, because `$host` drops the port the sign-in's Origin check keeps. Do not run `maintain.sh https` on such a server: it installs Caddy and writes its own Caddyfile.

## The firewall

The bot polls Telegram rather than waiting for it, so the only inbound traffic is the page.

| Port | Open? | Why |
|---|---|---|
| SSH (22) | Yes | Your way in, not FamilyDB's |
| 80/tcp | Yes | Caddy's certificate check, and its redirect to HTTPS |
| 443/tcp, or your `WEB_PUBLIC_PORT` | Yes | The page |
| `WEB_PORT` (8080) | Keep it closed | The bot listens on the loopback, so only Caddy reaches it |

On a virtualenv install the installer opens `80,443/tcp` (or `80,<port>/tcp`) only if `ufw` is already on, and `maintain.sh https --port` closes the old port only if the installer opened it. On Docker the installer opens nothing in `ufw`: Docker publishes Caddy's ports itself, and `ufw` rules normally do not apply to them. What the compose file publishes is what is reachable, which is why the bot's port stays on `127.0.0.1`; keep it there. A provider's own firewall is separate and yours to open.

**Turning on `ufw` without allowing SSH first locks you out of the server;** the only way back is the provider's console.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp          # or 80,<port>/tcp if the page is on another port
sudo ufw enable
```

## Logs

The bot writes to standard error and keeps no log file: under systemd that is the journal, on Docker the container's log.

```bash
sudo /opt/familydb/scripts/maintain.sh logs 100    # the last 100 lines, then follows; Ctrl-C stops
```

FamilyDB sets no limit on the journal. Cap it with `SystemMaxUse=500M` in `/etc/systemd/journald.conf` and restart `systemd-journald`; `sudo journalctl --vacuum-size=200M` trims it now. Docker keeps five files of 10 MB for each container. The installer's scripts keep owner-only transcripts in `/var/log/familydb-*.log`, which nothing rotates.

A Telegram bot token travels in the request address, so the bot replaces it with `bot<token>` in each log message. Exception text attached to a message is not filtered, and nothing else is scrubbed. The level is **Log detail** on the [General settings](/wiki/controls/settings/general) page (`LOG_LEVEL`); the default is Info. Debug logs every HTTP request, so turn it back down after chasing a problem.

## Disk and memory

The install takes about 600 MB. `bootstrap.sh` refuses to start with under 900 MB free; `install.sh` alone warns under 600 MB. The doctor warns below 500 MB free where the database lives, and a backup needs room for the database plus 50 MB. What grows is the database (no job prunes messages or the records of model and tool calls), `backups/` (about two weeks of full copies by default), and the journal, Docker's logs and its images (`docker system df` shows them).

On "no space left on device", trim the journal first, then run `sudo apt-get clean`, then remove old backups (`maintain.sh schedule-backups --keep-days N` sets how long they live).

The bot needs about 200 MB (the installer's estimate); building the install needs more, so it warns on under 900 MB. A step that ends with only `Killed` ran out of memory: confirm with `sudo dmesg -T | grep -i 'killed process'`, add swap, and run the install again.

```bash
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Updates and reboots

FamilyDB's code and dependencies change only through [`maintain.sh upgrade`](/wiki/operations/upgrade-and-rollback); the operating system is yours. Turn on security updates at least:

```bash
sudo apt update && sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

That covers your distribution's security updates, not Caddy's own repository, which the installer adds when the system's Caddy is older than 2.10. Run `sudo apt update && sudo apt upgrade` now and then. On Docker, an upgrade does not fetch a newer `caddy:2-alpine`.

After a reboot the service comes back by itself: the installer enables it at boot, and Docker's `unless-stopped` does the same for the containers once Docker is up. `maintain.sh status` and the doctor both say whether it is enabled at boot. On every start the bot applies any pending migrations, then:

- **Scheduled jobs.** They live in memory, so about a minute after start a catch-up runs the follow-ups, the plan check and the weekend digest (the digest only if today is its day and its hour has passed), and the daily model check if a day has gone by. A repeat does nothing new; the digest, for one, logs "digest already sent today".
- **Reminders.** One that fell due while the bot was down goes out once it is back, worded as late.
- **A message in the middle of a turn.** Its [lease](/wiki/reference/glossary#lease) lapses after five minutes, and the retry job (every five minutes by default) answers it and sends any reply that was stored but not delivered.

## What the installer recorded

Each change the installer makes outside `/opt/familydb` is written as it happens to `/var/lib/familydb-install` (root-only), with a copy of any file it replaced and GitHub's host key. That record lets `uninstall.sh --from-zero` undo exactly what the installer did. Only a run as root writes it, and not a dry run. [Install and first run](/wiki/operations/install#taking-it-off-again) has the three levels of uninstall.

## Security posture of the host

- **A dedicated account.** `familydb` is a system account with `/opt/familydb` as its home, `/usr/sbin/nologin` as its shell and no password.
- **Owner-only files.** Every `familydb` command sets umask `077`, and `familydb run` removes group and other access from the files it owns among the database, its write-ahead files, `google_key.json` and `web_secret`.
- **The session key.** `data/web_secret` is created `600` the first time the page starts. **Anyone who can read it can forge a sign-in.** [Passwords and sessions](/wiki/security/passwords-and-sessions) covers rotating it and `WEB_SECRET_KEY`.
- **The deploy key.** Bootstrap keeps it where you put it (`/root/familydb_deploy`), makes it `600` and records its path in the checkout's git configuration so upgrades can fetch. It is a read-only key on GitHub; deleting it there ends the server's access to the code. A `GITHUB_TOKEN` is used for the clone only and not written down.
- **Root.** Whoever can run `maintain.sh password` on the server can get into the page, so keep SSH access tight. [Recovery](/wiki/operations/recovery) explains why.

Developer docs: `deploy/familydb.service`, `deploy/Caddyfile`, `deploy/nginx-familydb.conf`, `docker-compose.yml`, `scripts/lib/https.sh`, `src/familydb/privacy.py`, `src/familydb/web/keys.py`, `src/familydb/jobs/catch_up.py`; `RUNBOOK.md`, "Virtualenv and systemd" and "Looking after the server"; and `docs/INSTALL.md`, "Looking after the server itself".
