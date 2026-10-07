# The server

This page says what FamilyDB puts on its server and how to look after it. [Install and first run](/wiki/operations/install) has the table of what the installer changes; this page adds who owns what, how the service behaves, what must be open, and what grows.

## What is in /opt/familydb

| Path | Owner and mode | What it is |
|---|---|---|
| `src/`, `scripts/`, `deploy/`, `.git` | root; nobody else can write | The code. Bootstrap, and each upgrade of a virtualenv install, run `chmod -R go-w` on it, so the bot can run its code but not change it |
| `.venv/` | root, readable by `familydb` | The Python environment, built by `uv` from `uv.lock`. It can be rebuilt. `.cache/` and `.local/` beside it hold uv's cache and any Python uv fetched |
| `.env` | `familydb`, `600` | The page's address, the first password, and any key you put there. A `.env.<timestamp>.bak` copy holds the same keys |
| `data/` | `familydb`, `700` | The database, `google_key.json` and `web_secret` |
| `backups/` | folder owned by `familydb`, each file `600` | The nightly and safety backups |
| `caddy/` | Docker's `tls` profile only | Caddy's certificate and private key |

On Docker, `data/` belongs to uid 1000, the `familydb` user inside the container, and `.env` stays with whoever ran the installer. [Backup and restore](/wiki/operations/backup-and-restore) has the table of what a backup holds. Neither Caddy's certificates nor `.env` are in one.

## The service

A virtualenv install runs one systemd unit, `/etc/systemd/system/familydb.service`, a copy of `deploy/familydb.service` with `/opt/familydb` replaced by the install's path. It starts `/opt/familydb/.venv/bin/familydb run` as the `familydb` user, with `.env` as its environment file. That one process serves the page, polls Telegram and runs every scheduled job.

```bash
sudo systemctl status familydb
sudo /opt/familydb/scripts/maintain.sh status      # also shows the version, memory and last backup
sudo /opt/familydb/scripts/maintain.sh restart
```

| Setting | What it does |
|---|---|
| `Restart=on-failure`, `RestartSec=5` | Restarts it five seconds after it fails. A stop you asked for stays stopped |
| `TimeoutStopSec=150` | Waits up to 150 seconds for a clean stop before killing it. A lookup in the middle of a model call can be slow to notice; nothing is lost if it is killed |
| `UMask=0077` | Everything it creates is owner-only |
| `ProtectSystem=strict`, `ReadWritePaths=/opt/familydb/data` | The whole file system is read-only to it except `data/`. `FAMILYDB_PATH` must stay in there |
| `ProtectHome=true` | `/home` is hidden. For a checkout under `/home` or `/root` the installer writes `read-only` instead |
| `NoNewPrivileges`, empty `CapabilityBoundingSet` and `AmbientCapabilities` | It gains nothing, and has no capabilities, so `WEB_PORT` must be 1025 or above |
| `PrivateTmp`, `PrivateDevices`, `Protect*`, `Restrict*`, `LockPersonality`, `SystemCallFilter=@system-service` | Its own `/tmp`, no device files, no changing the clock, hostname or kernel, only ordinary network and Unix sockets, and only the system calls a normal service needs |

After editing the unit, run `sudo systemctl daemon-reload` and restart it.

## Docker instead

`--mode docker` runs two containers from `docker-compose.yml`, with no systemd unit and none of the options above.

| | `bot` | `caddy` |
|---|---|---|
| Image | `familydb:local`, built from the `Dockerfile` (Python 3.12, runs as uid 1000) | `caddy:2-alpine` |
| Runs | Always on | Only with the `tls` profile. The installer writes `COMPOSE_PROFILES=tls` in `.env` when you give a domain |
| Volume | `./data` as `/data` | `./caddy` as `/data` |
| Ports | `127.0.0.1:8080:8080`, this machine only | `80:80` and `443:443` (the host side of 443 is `WEB_PUBLIC_PORT`) |
| Restart | `unless-stopped` | `unless-stopped` |

`WEB_PORT` in `.env` moves the first port mapping. Caddy keeps its data apart from `data/` on purpose, so the bot's container cannot read the certificate key and a copy of `data/` does not carry it. The compose file sets no stop timeout, so Docker's own default applies rather than the unit's 150 seconds. `maintain.sh` takes the same commands on Docker; or use Docker directly:

```bash
sudo docker compose --project-directory /opt/familydb ps
sudo docker compose --project-directory /opt/familydb logs -f bot
```

## HTTPS: Caddy

On a virtualenv install the installer puts Caddy on the machine and writes `/etc/caddy/Caddyfile`; `maintain.sh https` writes it again. The file is one site block, `reverse_proxy 127.0.0.1:<WEB_PORT>`, so Caddy holds the certificate and passes the page on to the bot, which listens on the loopback only (`WEB_HOST=127.0.0.1`). Caddy also replaces any `X-Forwarded-For` a visitor sends with the real address, which the sign-in lockout counts, and `WEB_TRUST_PROXY=true` makes the page believe one proxy hop. A Caddyfile that serves something else is left alone, and the installer prints the lines to add.

| The page is at | Certificate |
|---|---|
| A domain | Caddy gets a public one once the name points at the server and ports 80 and 443 are open |
| A public IPv4 address | A short-lived (six-day) Let's Encrypt certificate that Caddy renews. This needs Caddy 2.10 or newer, which the installer takes from Caddy's own apt repository when the system's is older. It waits 90 seconds for the certificate |
| A private address, or no certificate within 90 seconds | One Caddy signs itself (`tls internal`); each browser warns once |

Run `sudo /opt/familydb/scripts/maintain.sh https` again after opening a provider's firewall to try for a real certificate. Caddy keeps what it was issued in `/var/lib/caddy/.local/share/caddy`, outside the install. On Docker, an address alone gets no HTTPS: the page stays on the machine until you set `WEB_DOMAIN`.

The page is on 443 unless `WEB_PUBLIC_PORT` says otherwise. `maintain.sh https --port random` (or a number from 1024 to 65535, or `443` to go back) moves it; `random` picks from 20000 to 29999 (away from the ports nmap tries by default). Caddy then serves HTTPS on that port alone, sends no redirect from 80, and listens on 80 only while a certificate authority checks the machine. `maintain.sh port N|random` moves FamilyDB's own port behind Caddy; the General settings page shows both ports and cannot change them.

### nginx instead

If nginx is already on the server, install with `--local-only` so the installer leaves 80 and 443 to it, then follow the steps at the top of `deploy/nginx-familydb.conf`: copy it into `sites-available`, put your domain in, run `certbot --nginx -d <domain>`, then `nginx -t` and reload. In `.env`, set `WEB_HOST=127.0.0.1`, `WEB_TRUST_PROXY=true` and a `WEB_PASSWORD` of 12 or more characters. The file passes `Host` as `$http_host`, not `$host`, because `$host` drops the port the sign-in's Origin check keeps. It allows 90 seconds for a reply, as a chat turn can take most of a minute, and refuses bodies over 64 KB, since the page takes no uploads. Do not run `maintain.sh https` on such a server: it installs Caddy and writes its own Caddyfile.

## The firewall

The bot makes only outgoing connections (it polls Telegram rather than waiting for it), so the only inbound traffic is the page.

| Port | Open? | Why |
|---|---|---|
| SSH (22) | Yes | Your way in, not FamilyDB's |
| 80/tcp | Yes | Caddy's certificate check, and its redirect to HTTPS |
| 443/tcp, or your `WEB_PUBLIC_PORT` | Yes | The page |
| `WEB_PORT` (8080) | Keep it closed | The bot listens on the loopback, so only Caddy reaches it |

The installer opens `80,443/tcp` (or `80,<port>/tcp`) only if `ufw` is already on, and `maintain.sh https --port` closes the old port only if the installer opened it. A provider's firewall is separate and yours to open.

**Turning on `ufw` without allowing SSH first locks you out of the server;** the only way back is the provider's console.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable
```

## Logs

The bot writes to standard error and keeps no log file: under systemd that is the journal, on Docker the container's log.

```bash
sudo /opt/familydb/scripts/maintain.sh logs 100
```

FamilyDB sets no limit on the journal. Cap it with `SystemMaxUse=500M` in `/etc/systemd/journald.conf` and restart `systemd-journald`; `sudo journalctl --vacuum-size=200M` trims it now. Docker keeps five files of 10 MB for each container. The installer's scripts write transcripts to `/var/log/familydb-bootstrap.log`, `-install.log`, `-maintain.log` and `-uninstall.log`, each owner-only; FamilyDB sets up no rotation for them.

A Telegram bot token travels in the request address, so the bot replaces it with `bot<token>` in every line it logs. Nothing else is scrubbed. The level is **Log detail** on the [General settings](/wiki/controls/settings/general) page (`LOG_LEVEL`); the default is Info. Debug logs every HTTP request, which is loud, so turn it back down after chasing a problem.

## Disk and memory

The install takes about 600 MB, and the installer wants 900 MB free to start. The doctor warns below 500 MB free where the database lives, and a backup needs room for the database plus 50 MB. What grows:

- **The database.** No job prunes messages or the records of model and tool calls.
- **`backups/`.** About two weeks of full copies by default.
- **The journal, Docker's logs and images.** `docker system df` shows what Docker holds.

On "no space left on device", trim the journal first, then `sudo apt-get clean`, then old backups (`maintain.sh schedule-backups --keep-days N` sets how long they live).

The bot needs about 200 MB (the installer's estimate), but building the install needs more, so it warns on under 900 MB. A step that ends with only `Killed` was the kernel running out of memory: check `sudo dmesg -T | grep -i 'killed process'`, add swap, and run the install again; what worked is kept.

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

Caddy on a virtualenv install comes from apt, so those updates cover it. On Docker an upgrade rebuilds the bot's image and does not fetch a newer `caddy:2-alpine`.

After a reboot the service comes back by itself: the installer enables it at boot, and Docker's `unless-stopped` does the same for the containers once Docker is up. `maintain.sh status` and the doctor both say whether it is enabled at boot. On every start the bot applies any pending migrations, then:

- **Scheduled jobs.** They live in memory, so about a minute after start a catch-up runs the follow-ups, and the plan check and the weekend digest if their hour has passed, and the daily model check if a day has gone by. A repeat does nothing new; the digest, for one, logs "digest already sent today".
- **Reminders.** One that fell due while the bot was down goes out once it is back, worded as late.
- **A message in the middle of a turn.** Its [lease](/wiki/reference/glossary#lease) lapses after five minutes, and the retry job (every five minutes by default) answers it, and sends any reply that was stored but not delivered.

## What the installer recorded

Each change the installer makes outside `/opt/familydb` is written as it happens to `/var/lib/familydb-install` (root-only), with a copy of any file it replaced. GitHub's host key is kept there too. That record lets `uninstall.sh --from-zero` undo exactly what the installer did: the packages it added, files and links, the `familydb` account, root's cron line and crontab, firewall rules, Caddy's apt source and key, and replaced files put back. Only a run as root writes it, and not a dry run. [Install and first run](/wiki/operations/install#taking-it-off-again) has the three levels of uninstall.

## Security posture of the host

- **A dedicated account.** `familydb` is a system account with `/opt/familydb` as its home, `/usr/sbin/nologin` as its shell and no password.
- **Owner-only files.** Every `familydb` command sets umask `077`. `familydb run` also removes group and other access from the database, its write-ahead files, `google_key.json` and `web_secret` at start, fixing any an older version left readable.
- **The session key.** `data/web_secret` is 32 random bytes, created `600` the first time the page starts. With `WEB_SECRET_KEY` set, the bot uses that instead of the file, and the page cannot sign everyone out by rotating it. **Anyone who can read the key can forge a sign-in.** If `data/` cannot be written, the bot logs a warning and uses a temporary key, so sign-ins do not survive a restart. [Passwords and sessions](/wiki/security/passwords-and-sessions) covers the rest.
- **The deploy key.** Bootstrap keeps it where you put it (`/root/familydb_deploy`, from the install block), makes it `600`, strips a passphrase if you agree, and records its path in the checkout's git configuration so upgrades can fetch. It is a read-only key on GitHub. A `GITHUB_TOKEN` is used for the clone only and never written down. Deleting the key on GitHub ends the server's access to the code.
- **Root.** Whoever can run `maintain.sh password` on the server can get into the page, so keep SSH access tight. [Recovery](/wiki/operations/recovery) explains why.

Developer docs: `deploy/familydb.service`, `deploy/Caddyfile`, `deploy/nginx-familydb.conf`, `docker-compose.yml`, `scripts/lib/https.sh`, `src/familydb/privacy.py`, `src/familydb/web/keys.py`, `src/familydb/jobs/catch_up.py`; `RUNBOOK.md`, "Virtualenv and systemd" and "Looking after the server"; and `docs/INSTALL.md`, "What the installer changes, and why" and "Looking after the server itself".
