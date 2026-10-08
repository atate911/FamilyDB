# Runbook: running FamilyDB on a home server or a VPS

Two supported ways to run it: Docker Compose, or a Python virtualenv under systemd. Both use the same `.env` and the same `data/` folder (database, tokens). Almost everything is set on the web page once it runs (model and key, Telegram, Google Calendar, home, spending); files hold what the page cannot decide for itself: how it is reached and the first password.

## Requirements

- Linux with Docker (compose plugin) or Python 3.11+ and [uv](https://docs.astral.sh/uv/).
- Outbound HTTPS. The bot needs no inbound ports; the page needs 80 and 443 when served over HTTPS, which the installer does unless told to keep it on the machine (section 10).
- A key for OpenAI (the default), Anthropic or Gemini, typed on the settings page (section 11).

## 1. Get the code and the config

**From a bare server use [docs/INSTALL.md](docs/INSTALL.md)** (preparing the machine, getting the private repository onto it, and `sudo bash scripts/bootstrap.sh`). This section is for a machine that already has the code and a runtime:

```bash
sudo mkdir -p /opt/familydb && sudo chown "$USER" /opt/familydb
git clone <this repo> /opt/familydb && cd /opt/familydb
sudo scripts/install.sh
```

It asks one thing, a domain name for the page. Left empty, a virtualenv install serves HTTPS at the server's own address and a Docker one keeps the page on this machine (section 10). It writes `.env`, installs dependencies, creates the database, picks Docker when it finds it (`bootstrap.sh` defaults to a virtualenv) and is safe to rerun: it never overwrites `.env` without asking and migrates rather than replaces the database. Sections 2a and 2b are the same steps by hand.

Decided without asking:

- The page is on (`WEB_ENABLED=true`) with a password: `WEB_PASSWORD` if given (12+ characters), else one made up, printed and kept in `.env`. It is only the way in until you choose your own (section 10, "Who signs in").
- Timezone from the machine; web lookups on (`WEB_TOOLS_ENABLED=true`); the weekend digest to the page's chat (`DIGEST_CHAT_ID=web`). All changeable on the page.
- HTTPS: `WEB_DOMAIN` (domain or the server's address) and `WEB_TRUST_PROXY=true`. Docker, which needs a domain for this, also gets `COMPOSE_PROFILES=tls`, so every `docker compose up -d` starts Caddy. A virtualenv gets Caddy from apt, `/etc/caddy/Caddyfile` (shape of `deploy/Caddyfile`), a reload, and ports 80 and 443 opened in `ufw` if it is on. Point the domain at the machine and open the same ports in the provider's firewall.
- `data/` owner-only; a nightly backup in root's crontab at 03:15 keeping fourteen days (section 7), cron installed with apt if missing. `BACKUPS=no` skips it.

It does not start the bot. It ends by saying how (`sudo systemctl start familydb` or `docker compose up -d`) and where the page will be: `https://your.domain/`, the server's address, or for a page kept on the machine an SSH tunnel (`ssh -L 8080:127.0.0.1:8080 you@server`, then `http://127.0.0.1:8080/`).

Flags: `--mode docker|venv`, `--local-only`, `--config-only` (write `.env` and stop), `--dry-run`, `--yes`, `--non-interactive` (answers from the environment). `scripts/install.sh --help` lists the variables, including `PROVIDER`, the three `*_API_KEY`s, `TELEGRAM_BOT_TOKEN`, `FAMILYDB_TZ`, `HOME_AREA`, `HOME_LAT`, `HOME_LON`, `WEATHER_UNITS`, `WEB_TOOLS_ENABLED`, `WEB_HOST`, `WEB_PORT`, `DIGEST_CHAT_ID`, which it writes to `.env` when it finds them in the environment:

```bash
WEB_DOMAIN=family.example.com ADMIN_NAME=Sam OPENAI_API_KEY=sk-... \
  scripts/install.sh --non-interactive --mode docker
```

By hand: `cp .env.example .env`, set `WEB_ENABLED=true` and a `WEB_PASSWORD` of 12+ characters, `mkdir -p data && chmod 700 data`. `.env.example` leaves the page, lookups and digest off, unlike the installer.

## 2a. Docker Compose

```bash
sudo chown 1000:1000 data          # the container runs as uid 1000
docker compose build
docker compose run --rm bot familydb db migrate
docker compose run --rm bot familydb members add Sam --role admin
docker compose up -d
docker compose logs -f bot
docker compose exec bot familydb chat "we should try the new ramen place"
docker compose exec -it bot familydb repl
```

`FAMILYDB_PATH` and `GOOGLE_KEY_PATH` are set inside the container to `/data/...`, where the compose file mounts `./data`. With `COMPOSE_PROFILES=tls` in `.env`, `docker compose up -d` starts Caddy too.

## 2b. Virtualenv and systemd

```bash
cd /opt/familydb
uv sync --frozen --no-dev            # creates .venv
.venv/bin/familydb db migrate
.venv/bin/familydb members add Sam --role admin
sudo useradd --system --home-dir /opt/familydb --shell /usr/sbin/nologin familydb
sudo chown -R familydb:familydb /opt/familydb/data /opt/familydb/.env
sudo chmod 700 /opt/familydb/data
sudo cp deploy/familydb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now familydb
journalctl -u familydb -f
```

`scripts/install.sh` does all of this. Without uv: `python3 -m venv .venv && .venv/bin/pip install .`. Check `User=` and paths in the unit if you cloned elsewhere than `/opt/familydb`.

**Clone into `/opt`, not a home directory.** The service runs as `familydb`, which cannot enter a closed home directory, so systemd reports a permission error on the working directory. The installer checks this before writing a unit and tells you to move the checkout. To use `/home` anyway: `chmod o+x /home/you`, and the unit needs `ProtectHome=read-only` rather than `true` (the installer sets it).

The unit sets `FAMILYDB_PATH` and `GOOGLE_KEY_PATH` under `/opt/familydb/data` and sandboxes the service: `UMask=0077`, `PrivateDevices`, `ProtectKernel*`, `RestrictAddressFamilies`, `SystemCallFilter=@system-service`. To use the shell as the service user (so the database stays its own): `sudo -u familydb /opt/familydb/.venv/bin/familydb repl`. Every `familydb` command also runs with umask 077, and `familydb run` and `familydb web` drop group and other access on the database, its write-ahead files, the Google key and `data/web_secret` at start, fixing any an older version left readable.

## 3. First run checklist

Open the page (section 10) and sign in with the installer's password. It opens on `/setup`, seven steps in order, each saying why and what to do: yourself (admin); your own password (ends the installer's; from then on everybody signs in as themselves, with a starting password from you on the Family page); an AI model and key (until then it saves what it is told but cannot answer); where home is (section 6); Telegram, linked to your phone (section 4); the rest of the family; Google Calendar (section 5). Until somebody is on the list and there is a model, the home page sends an admin back to setup; after, it lists what is left under "Finish setting up". Then on Chat: "we should try that new ramen place on Main St sometime" saves idea #1, "tell me about #1" answers from history. `/status` says which model answered, what is connected and what today cost.

From the shell, `familydb doctor` checks all of it and says what to do about anything wrong; `--online` also asks Telegram and the model API whether the keys work; `--fix` corrects what needs no decision. One at a time:

1. `familydb config`: settings (keys masked) and where each came from.
2. `familydb db migrate`: applies new migrations, says which.
3. `familydb members add NAME [--role admin|kid]` for everyone who will message the bot (parent is the default; kids need no channel). The Family page does the same.
4. `familydb chat "we should try that new ramen place on Main St sometime"` then `familydb chat "tell me about #1"`.
5. `familydb db status` shows `cache_read` above zero on the second call; if not, section 13.
6. `familydb debug validate-tools`: the API accepts every tool schema. Claude and Gemini only; on OpenAI the first real message is the check.
7. `familydb tool --list`: calendar and weather rows flip to `available` after sections 5 and 6.
8. `familydb suggest --window this-weekend`: what the engine says about the ideas so far, with the checks it skipped.

## 4. Telegram

1. In Telegram, BotFather `/newbot`; copy the token. Paste it on the settings page under Connections (effective within seconds, no restart), or set `TELEGRAM_BOT_TOKEN` in `.env` (read when `familydb run` starts). `/status` says "connected as @yourbot", "the token was refused by Telegram" or "cannot reach Telegram; trying again". Once connected, the bot's name and description in Telegram are the ones it goes by (hers, or FamilyDB's under none); the BotFather name lasts only until then.
2. Each family member opens t.me/yourbot and presses Start or sends anything. The bot does not answer strangers but notes who asked (id, Telegram name, when; never what they said; kept a month); the Family page lists them under "Asked to talk to the bot" with an add button. The reply tells them their id, for an admin to enter on the Family page or use with `familydb members add NAME --channel telegram --channel-user-id 12345`. For somebody already listed, an admin can instead make them a link on the Family page: opened on their phone, Start links their Telegram. It works once, for a day, is shown once, and whoever opens it first is taken for that person, so send it to them alone.
3. A family group: send BotFather `/setprivacy`, choose Disable so the bot sees every message, then add the bot (one already in the group must be removed and re-added). The settings page, under Connections, says whether it reads every message or only mentions. In a busy group turn on "Answer only when mentioned" (or `TELEGRAM_REQUIRE_MENTION=true`): it then answers only when @mentioned or replied to. Added by somebody on the family list it says hello; added by anyone else it says nothing. A group member not on the list is answered only when they mention it or reply, and is noted on the Family page. Stickers, files and videos in the group are ignored unless sent to the bot.
4. Location: sharing it with the bot (paperclip, Location; a live location keeps itself current) measures suggestions from there. On the web page, ticking "Send where I am" (beside Send, scripts on, remembered per browser, off to begin with, needs HTTPS or the server itself) sends it with each message until unticked. The latest position serves "near here" and "open now" for three hours, one per person, deleted after a day (within ten minutes of that while the service runs), and its place name and coordinates go to the model provider with the message. Nothing is sent unless someone shares or ticks.
5. Long polling exposes nothing; Telegram keeps updates a day while the server is off, and the bot catches up without double-processing.
6. The chat shows typing while an answer is coming. A sticker, file or video is not opened: words sent with it are answered and kept marked "(with a video, not seen)"; with none, the bot says (no model call) that it cannot read that.
7. Voice notes work like typed messages of any length: a speech model writes the words down (kept marked "(voice note)"; the recording is not kept) and the bot does whatever they ask. Claude cannot hear, so this needs an OpenAI or Gemini key even when chat runs on Claude; with neither, the bot asks for the message typed. Settings, AI model, "Voice notes": off, cap (5 minutes default; longer is not heard at all), who hears and with which model. It is a model call: it counts against the daily limit and shows on `/status` as "listening to voice notes", about $0.003 a minute on gpt-4o-mini-transcribe. One that could not be heard (service down, no words) is not retried, since the recording is gone; the bot asks again.
8. Photos work the same way: a photo, or an image sent as a file (JPEG, PNG, WebP), is read by the lookup model, which writes down what it is and every name, date, time, place, price and link; that is answered as if typed, caption after it. Words are kept marked "(photo)"; the picture is not. In a group only a photo sent to the bot (mention in caption, or reply) is looked at. Settings, AI model, "Photos" turns it off. It counts against the daily limit and shows on `/status` as "reading photos", about a tenth of a cent each on GPT-6 Luna. An album is answered once: up to four photos read, the rest counted. One that could not be looked at (over 3.9 MB; service down) is not retried; the bot asks again.

## 5. Google Calendar

FamilyDB reaches the calendar through a **service account**, a robot account with its own address that the family calendar is shared with. Nobody signs in and nothing expires. In a browser, once:

1. Create a Google Cloud project and enable the Google Calendar API.
2. IAM & Admin, Service accounts: create one (name it FamilyDB; no role). Keys, Add key, Create new key, **JSON**.
3. In Google Calendar, the family calendar's settings, Share with specific people: add the service account's address (`client_email` in the file, ending `iam.gserviceaccount.com`) with **Make changes to events**. Under Integrate calendar, copy the calendar ID.
4. On `/settings/connections`, Google Calendar: paste the key file and calendar ID, press Connect. The page tries them first (reads the calendar, adds a test event, removes it) and says what is wrong if anything: not shared, shared read-only, API not enabled.

The key is saved owner-only at `GOOGLE_KEY_PATH` (`data/google_key.json`). From the server: `uv run familydb google connect KEY_FILE CALENDAR_ID`; `familydb google events` checks either. A dedicated family Google account that owns the calendar keeps it apart from anyone's own but is not needed. From chat, "we're going to the symphony next Saturday at 8" creates the event; "move that to Sunday" and "cancel the symphony" update it.

## 6. Weather

Settings, General: type the home town as you would say it ("Vancouver, WA") and leave latitude and longitude (folded under "Exact position and travel times") empty: the page looks the place up on OpenStreetMap and fills them in. Coordinates you type win. Units: metric or imperial. In `.env`: `HOME_AREA`, `HOME_LAT`, `HOME_LON`, `WEATHER_UNITS`. Open-Meteo needs no key. Check: `familydb tool get_forecast --json '{"start": "2026-09-26", "end": "2026-09-27"}'`.

## 7. Backups

The database is one file holding everything the family said (and, for an admin to read when something is wrong, the words of recent calls to a model, for the days set on the settings page's Troubleshooting). The installer scheduled a nightly backup; by hand:

```bash
sudo scripts/maintain.sh schedule-backups --keep-days 14
sudo crontab -u root -l
sudo scripts/maintain.sh backup        # one now
```

One line in root's crontab, for Docker or systemd: at 03:15 a backup into `backups/` with SQLite's online backup (safe while the bot runs), deleting older than `--keep-days` only when it succeeded; each owner-only. It also removes backup lines an older install put in the `familydb` user's crontab. Without the script, for systemd:

```
15 3 * * * sudo -u familydb env FAMILYDB_PATH=/opt/familydb/data/familydb.sqlite3 /opt/familydb/.venv/bin/familydb db backup /opt/familydb/backups/familydb-$(date +\%F).sqlite3
```

Each backup is read back once written (SQLite's `quick_check` on the copy) and recorded in the database: a copy that fails says so and exits 1, so cron mails it. Status and `familydb doctor` say when the last good one was, and once any has been recorded, admins are told when none has worked for a day and a half (the hourly upkeep, which also tells them when the disk has less than 500 MB free).

`FAMILYDB_PATH` is set because cron does not run in the checkout, so `.env` is not read and the relative default path points at nothing (the backup then says so and writes nothing rather than backing up an empty database). `backups/` must be writable by `familydb`. Docker: `docker compose exec bot familydb db backup /data/backups/familydb-$(date +%F).sqlite3`. Calendar events are also in Google.

Keep a copy off the server: a backup on the same disk is not a backup. Backups are readable by owner and root only, so bundle on the server and fetch:

```bash
sudo tar -C /opt/familydb -czf ~/familydb-backups.tar.gz backups && sudo chown "$USER" ~/familydb-backups.tar.gz
scp you@server:familydb-backups.tar.gz .       # on your own computer
```

**Restoring.**

```bash
sudo scripts/maintain.sh restore backups/familydb-XXXX.sqlite3
```

It checks the backup is a sound database and not from a newer version than this code (it refuses one, before touching anything: upgrade first, or use an older backup), stops the bot, backs up the database being replaced (so a restore can be undone), puts the backup in place, clears the old write-ahead files, sets owner and permissions, migrates and starts. By hand, stop the bot first (it has the file open):

```bash
sudo systemctl stop familydb                       # or: docker compose stop bot
sudo -u familydb cp backups/familydb-2026-09-14.sqlite3 data/familydb.sqlite3
sudo -u familydb rm -f data/familydb.sqlite3-wal data/familydb.sqlite3-shm   # belong to the replaced database
sudo systemctl start familydb                      # or: docker compose start bot
```

`familydb db status` then shows row counts and schema version; an older file is migrated on the next start.

A key or token saved on the settings page lives in this file, so it is in every backup; section 11 says when to keep keys in `.env` instead.

**Moving to a new server.**

1. On the new server, install as in section 1 (the installer's block from `docs/INSTALL.md`), then stop the bot: `sudo systemctl stop familydb` (or `docker compose stop bot`).
2. On the old one, take a backup and stop the bot, so nothing is said to it after the copy: `sudo scripts/maintain.sh backup`, then `sudo systemctl stop familydb`.
3. Copy the newest file from the old `backups/` to the new server, with `.env` (it holds what the installer wrote, and any key kept outside the page) and `data/google_key.json` if Google Calendar is connected.
4. On the new server: `sudo scripts/maintain.sh restore /path/to/familydb-XXXX.sqlite3`, which checks it, puts it in place and starts the bot.
5. Point the domain at the new address if there is one; on Telegram nothing changes, since the token moved with the database or `.env`.
6. Check: `familydb health` says ok, `familydb doctor` is clean, and the Status page shows the last good backup once the first night has passed. Each phone that had notices turned on keeps them only if the address is the same; otherwise turn them on again under Your password.

**Taking the data away.** A backup is the database itself, for FamilyDB to read. To take the family's data somewhere else:

```bash
familydb export ~/familydb-export       # docker compose exec bot familydb export /data/export
```

writes `plans.ics` (every plan, for any calendar), `ideas.csv` and `tasks.csv` (spreadsheets), and `everything.json` (people, ideas, places, how things went, plans, things to do, what is remembered, wish lists, lists and every message), with no key, password, Telegram id or device in any of them. On the page, a grown-up downloads the first three from the foot of Plans, Ideas and To do; an admin downloads everything from Sign-in and security, after typing their password again.

## 8. Upgrades

```bash
sudo /opt/familydb/scripts/maintain.sh upgrade
```

It takes a backup, fetches, moves to the newer code, reinstalls locked dependencies (or rebuilds the image), migrates, restarts, then prints the command to go back. Do not `git pull`: after an upgrade the checkout is on a detached commit, where it fails, and it would skip the backup and dependencies. On a private repository the fetch needs a credential (docs/INSTALL.md, Day to day).

Which code: while the newest `CHANGELOG.md` heading says "in progress", bootstrap installs the default branch and `upgrade` follows it; once a version heading carries a date, both follow the newest release tag. An upgrade only moves forward: if the target does not contain what is installed, it refuses and changes nothing rather than take the database back past migrations already run. Pin a tag, branch or commit at install with `bootstrap.sh --ref NAME`.

Migrations also run on every start. After it is back, check `systemctl status familydb` or `docker compose logs bot`: a setting that no longer validates is named in one line.

A Docker install whose Caddy kept its certificate in `data/caddy` should `mv data/caddy caddy` before starting (or delete it and let Caddy get a new one) and delete any copy of `data/` holding it: a private key there is readable from the bot's container.

## 9. Lookups, the weekend digest and follow-ups

**Looking ideas up.** On after the installer ("Look ideas up on the web", `WEB_TOOLS_ENABLED`). Every `ENRICH_INTERVAL_MINUTES` the bot takes up to `ENRICH_BATCH` new ideas and, in a separate small model call with web search, finds the place, address, hours, booking link and price notes, geocodes it (Nominatim, no key) and estimates the drive from home, then posts one line to the chat where the idea was captured ("Looked up #57 Hopscotch Portland: open Sat 10:00-20:00 · about 45 min away (estimate)"); "Say in the chat when an idea is filled in" turns that off. Skipped with no model call: home ideas with no place, link or location, gifts with no place, and ideas that are not one place ("a picnic somewhere"); ones it cannot identify are marked failed and left alone. `familydb enrich --idea 57` redoes one; `familydb ideas list` shows the `details:` state; `familydb tool describe_idea --json '{"id": 57}'` shows what was saved. Details older than `PLACE_STALE_DAYS` refresh the next time the idea comes up in a suggestion. With lookups off nothing is looked up and suggestions say "hours unknown". When the daily limit is used up, lookups wait for tomorrow.

**Suggestions.** "What should we do this weekend?" runs the engine once: free time from the calendar, the forecast, every idea against its looked-up details and, with lookups on, a search for time-bound things near home (cached twelve hours, shared by questions with the same window, constraints and kind). Each verdict is logged in `suggestions`. It works in minutes, not parts of the day: "I'm bored, what now?" looks at the next few hours, "tonight" the evening, and an answer for today says when ("can go 16:10-17:55 today"). `familydb suggest --window this-weekend --discover` runs it from the shell.

**Weekend digest.** The installer sends it to the page's chat (`web`), which needs no id. For the family's Telegram group, add the bot, have somebody on the family list mention it there once, then pick the group in "Weekend ideas go to" (settings, Messages; chats the bot has seen, by last activity); empty the box and nothing is sent. A group id is a negative number and can be typed. Day and time (default Thursday 18:00 family time) are set beside it. `familydb digest` prints the schedule, `familydb digest --now` posts one. It is asked as the first admin and stored like any message, so it goes at most once a day; a failed model call is retried like a failed message; if the bot was off at the hour it sends a minute after the next start the same day.

**Follow-ups.** The morning after a plan (`FOLLOW_UP_HOUR`, default 10:00) the bot asks "How was #57 Hopscotch Portland on Saturday? Worth doing again?" in the plan's chat, once per plan, unless someone already said. The answer feeds future suggestions. `familydb follow-ups --now` asks by hand. No model call.

**Reminders.** A task with a reminder time ("remind me on Tuesday at 9 that we need paper towels", or on `/tasks`) is sent once when due to the chat it was asked in; browser and console reminders go to the page's chat. A job checks every minute, no model call, only in `familydb run` (not `familydb web`). One that fell due while the bot was off is sent at start and says when it was due. If the family is talking in that chat, the reply they are about to get carries it; follow-ups and lookup notes likewise.

**The evening before a plan.** At `PLAN_CHECK_HOUR` (19:00) each plan for tomorrow is rechecked in code: rain forecast for an outdoor idea, or its place listed closed then, gets a heads-up in the plan's chat with another idea for the same time when one fits; all well, nothing is said. No model call; "Check tomorrow's plans the evening before" (settings, Messages) turns it off.

**Tasks kept for a window.** "One of these Saturday mornings" is brought up in the task's chat when such a morning comes round and the calendar is free for the hour ahead: each task once a week at most, one a day per chat. Only plain days and parts of the day count ("before Christmas" is left alone). No model call; the settings page (Messages) turns it off.

**What is on near home.** Under its own page on the settings, named as the family call it. The calendars it reads (an iCal or .ics address a line, or ticked among those it found near home), an optional Ticketmaster key (free, from developer.ticketmaster.com: the Consumer Key of an app made there), and the weekly search with its monthly budget. Each calendar and Ticketmaster are read once a day with no model call; the search runs once a week, and the lookup for calendars every 30 days and when the home area changes, both within `HAPPENING_BUDGET` a month (US$1 unless changed) and the daily limit. `familydb happening` reads what is due now, `--now` everything; the Status page shows each source and what the searches cost this month, and an admin is told on Telegram when one cannot be read three days running. What it finds is offered in the suggestions and listed on the Plans page's third tab.

**Cost.** Enrichment is at most three searches and three page reads per idea; discovery at most four searches per window and question kind per twelve hours. Both run on the lookup model (GPT-6 Luna by default; section 11) and count towards the daily limit.

## 10. The web page

The page is the front door: home (what is coming up, then "Finish setting up", section 3); Chat; ideas with search and filters and each idea in full; restaurants; plans as list or month (from Google Calendar when connected, with an event added on a phone showing within a minute, else the saved plans); things to do and reminders; Memory (what the bot remembers and where each thing came from); Family; status and settings (section 11), with Personality among them. Its forms add and change ideas and tasks, record outcomes, create, move and cancel plans, and add to or forget memories through the same tools the bot uses, so nothing done on the page is anything the bot could not do.

The installer always turns the page on, with a password. Ways to reach it:

**Kept to the machine, over a tunnel.** With `--local-only`, or Docker and no domain, the page binds `127.0.0.1` (Docker publishes `127.0.0.1:8080`). From your computer: `ssh -L 8080:127.0.0.1:8080 you@server`, then `http://127.0.0.1:8080/`; or Tailscale. Safest, opens no port.

**On the internet, over HTTPS.** Give the installer a domain, point it at the machine, open 80 and 443 in the provider's firewall (a virtualenv install opens `ufw`). `.env` then has:

```
WEB_ENABLED=true
WEB_PASSWORD=...                 # made up and printed, unless you gave one
WEB_TRUST_PROXY=true
WEB_DOMAIN=familydb.example.com
COMPOSE_PROFILES=tls             # Docker only: `docker compose up -d` starts Caddy too
```

With Docker, the Caddy container keeps its certificate and private key in `caddy/` beside the checkout, deliberately not in `data/`, where the key would be readable from the bot's container and land in every backup. With a virtualenv, Caddy runs on the machine and the installer writes `/etc/caddy/Caddyfile` (`maintain.sh https` does it again; by hand, the steps are at the top of `deploy/Caddyfile`). With nginx already there, `deploy/nginx-familydb.conf` does the same with a certbot certificate and works on a port other than 443. Keep `WEB_HOST=127.0.0.1` on a virtualenv install and never open 8080.

`WEB_TRUST_PROXY` makes the page believe the forwarding headers from exactly one proxy hop (real visitor address, HTTPS) and marks the login cookie `Secure`. On the loopback it trusts only a proxy on this machine; bound to `0.0.0.0`, as in Docker, it trusts whatever connects, safe only because compose publishes the port to `127.0.0.1` alone. A forged `X-Forwarded-For` is ignored. Turn it on only with a proxy in front. Behind a proxy a password is always required.

**On the internet with no domain.** What a virtualenv install does when given none: the same arrangement at the server's address. A public IPv4 address gets a short-lived Let's Encrypt certificate Caddy renews itself; when the distribution's Caddy is older than 2.10 the installer brings a newer one from Caddy's apt repository. A private address, or a certificate that does not arrive within 90 seconds, gets one Caddy signs itself (`tls internal`), which each browser warns about once per device; the connection is encrypted either way. `sudo /opt/familydb/scripts/maintain.sh https` sets this up on an install made without it, and is the command to rerun once a provider's firewall lets 80 and 443 through. `maintain.sh https DOMAIN` switches to a domain.

**At home, on the local network.** Set `WEB_HOST=0.0.0.0` in `.env` (Docker: also drop the `127.0.0.1:` from the compose `ports` line); the page answers at `http://<server>:8080/`. A page facing the network needs passwords of 12+ characters, the only guard, with no second factor.

**FamilyDB's own port** is 8080 unless `WEB_PORT` says otherwise. When something else needs 8080 or the installer said it was taken:

```bash
sudo /opt/familydb/scripts/maintain.sh port 9090    # any free port 1025-65535, or: port random
```

It writes `WEB_PORT`, points Caddy at it where the installer's Caddyfile passed to the old port (restoring the old Caddyfile if Caddy will not load the change) and restarts FamilyDB; with Docker, compose publishes whatever `WEB_PORT` names and Caddy's container follows, so the containers are started again. Behind Caddy the address people open does not change. The General settings page shows both ports and these commands but cannot change them: how the page is reached stays in `.env`. The port must stay above 1024 because the bot runs unprivileged.

**A port scans rarely try.** A scan finds what listens on public addresses: Caddy on 443 (and 80 for certificates) and SSH on 22; 8080 is on the loopback only. 443 is the third port nmap tries and the one every internet sweep looks at. To serve on another:

```bash
sudo /opt/familydb/scripts/maintain.sh https --port random   # or --port 24613, or --port 443 to go back
```

`random` picks 20000-29999, unused locally and not among the thousand ports nmap tries by default. The page is then `https://your.domain:PORT/`; bookmark it, the old address finds nothing. Caddy serves HTTPS on that port only and gets certificates only through the certificate authority's check on port 80 (the other kind needs 443); it listens on 80 just while checked and sends nobody anywhere. `ufw` opens 80 and the new port and closes 443 if the installer opened it; allow the port in a provider's firewall too. With Docker the command writes `WEB_PUBLIC_PORT` in `.env` and restarts the containers (the Caddy container still listens on 443; the host publishes it on that port). At install, `WEB_PUBLIC_PORT=random` before the installer does the same.

This takes the page out of sweeps of the usual ports (and their log noise), but is not a lock: a scan of all ports finds it in minutes, and a domain's certificate is in the public certificate logs once issued. Passwords and lockouts keep it shut. To be unfindable, keep it off the internet: `--local-only` and an SSH tunnel, or a private network such as Tailscale.

**On a phone, as an app.** iPhone: Safari, Share, *Add to Home Screen*; Android: Chrome menu, *Add to Home screen*. The icon is the mark on the page's charcoal with the page's name (the *Name of this page* setting when added), and it opens full-screen with the page's own tabs. On iPhone it keeps its own sign-in apart from Safari's (lasting `WEB_SESSION_DAYS`). Over HTTPS it needs a certificate the phone already trusts (a domain's, or the public-address one): a Caddy self-signed certificate will not do, as the app has nowhere to accept the warning. Reminders and heads-ups still come on Telegram.

**Who signs in.** Each person signs in with their name as on the Family page and a password of their own, stored only as a scrypt hash. An admin gives everybody else a starting password there, shown once; each chooses their own on first sign-in. A new starting password, or taking one away, signs that person out on every device (the answer to a lost phone). A parent uses the bot (chat, ideas, plans, things to do, status); an admin also reaches Settings, setup and Family; a kid has the permissions and limits in the one table, `src/familydb/roles.py`, which the page asks. The chat speaks as whoever is signed in; the settings history says who changed what. Until the first admin chooses their own password, the page takes the installer's, or one the family chose to share on the settings page; that admin's own password ends it for everyone, and from then on an admin who can sign in always exists, so it never returns. For the last admin who forgot theirs, `sudo /opt/familydb/scripts/maintain.sh password` prints a new starting password (`password NAME` for somebody else).

**What protects it.** Passwords are checked in constant time; a name that is nobody's is checked against a decoy so it takes as long and gets the same answer. A sign-in lasts `WEB_SESSION_DAYS` (30). Five wrong passwords lock that address out for fifteen minutes (logged). Fifty failures from anywhere in a quarter hour stop new sign-ins except from a browser that has signed in before, which carries a signed `familydb_device` cookie for a year (void after its password changes or "Sign everyone out"): a guesser with many addresses gets nowhere and the family still gets in. Every page except the login, `/healthz` and `/manifest.webmanifest` (a phone asks for it without the cookie) needs the cookie. Responses carry a content security policy forbidding framing and any script but the page's own files (the message box's one keeps an unsent message and sends the phone's position when asked); reading, every form and sending a message work with scripts off. Every form carries a session token, so a link from another site cannot act for the family. A page bound off the loopback with no password refuses to serve and says so, unless `WEB_ALLOW_NO_PASSWORD=true` is set on purpose; behind a proxy it never serves without one.

What a sign-in buys: a parent's password (or, for now, a kid's) is most of the bot: chat spends tokens, forms change ideas and outcomes and put things on the family calendar. An admin's is all of it: who may message the bot and who signs in, which model answers, the spending limit, showing an API key to whoever knows that admin's password, and which calendar. On the internet those passwords stand between a stranger and your API bill; the daily limit bounds a day but is an estimate, so also set a limit on the key with the provider. Nothing is destroyed (an idea is dropped not deleted, a removed member keeps everything they said, every change is a row) but it is all reachable. Make passwords long and watch `/status` for a month that does not look like yours.

**Checking it.**

```bash
curl -sI http://127.0.0.1:8080/            # 302 to /login, plus the security headers
curl -s http://127.0.0.1:8080/healthz      # ok
familydb health                            # the same, without the page (exit 1 when unwell)
```

`/healthz` and `familydb health` say "ok" when the database answers and the scheduled jobs are running; otherwise what is wrong, with a 503 (or exit 1): "the database does not answer", or "the scheduled jobs have not run for 20 minutes" when `familydb run` went quiet without stopping. A page served alone (`familydb web`) has no jobs and is judged by its database; a bot stopped on purpose is not trouble. The Docker image runs `familydb health` as its HEALTHCHECK, so `docker compose ps` shows "unhealthy" when it fails three times in a row.

`familydb web --port 8099` serves the page alone in the foreground, with no Telegram or jobs: the quickest way to try a `WEB_` change without restarting the bot.

**Notes.** The login cookie is signed with a key generated once into `data/web_secret`; "Sign everyone out" replaces it and ends every sign-in everywhere. Set `WEB_SECRET_KEY` instead when running more than one process (or everyone is signed out at random); the page cannot replace a pinned key. The page opens its own database connection per request, safe beside the bot writing (WAL mode).

**Status.** `/status` answers "is it working?" without a log: which model answers chat, digest and lookups; whether each key is set and whether from `.env` or the page; whether Telegram is connected; whether calendar, weather, web lookups and digest are set up; today's cost against the limit; cost in dollars over thirty days per purpose and per model; where each purpose's input went (instructions, tools, idea list, history, message; the real total shared out by size); prompt-cache share; what awaits lookup, which messages did not go through, and failures worth a look. Dollar figures are estimates from a price table; an asterisk marks a model the table does not list, counted high. It asks nothing of a model, so refreshing is free. At the bottom, What's new lists what came in the version running, read from the CHANGELOG.md that shipped with it (the Docker image copies it): the section still being written when the install follows the default branch.

## 11. Settings, and choosing OpenAI, Claude or Gemini

Every setting here can be changed in `.env` (restart needed) or on `/settings` (no restart). A value set on the page wins; empty its box and `.env` applies again (the grayed value in an empty box shows it; a dropdown says "Default (Thursday)"); a box set on the page is marked "changed". `familydb config` prints the lot and where each came from. `/settings` is a card to each part, saying how it stands and marking what needs a look: General (home, time zone, units, the page's name), AI model (company, key, checked with the company for free, models), Spending, Messages (what is sent unasked, and when), Lookups, Personality and family, Connections (Telegram, Google Calendar), Sign-in and security, What has changed. Each page has one Save; fine-tuning is folded.

A change reaches the next message and page at once, a new Telegram token within seconds, the timezone at once. Scheduled jobs (digest, follow-ups, evening check, nudges, lookups, retries) pick up a new time or interval within five minutes, hours in the family's timezone.

**Who answers.** Chosen per surface:

```
PROVIDER=openai            # openai, anthropic or gemini: who writes the replies the family reads
WORKER_PROVIDER=           # empty means the same; set it to send lookups elsewhere
PROVIDER_FALLBACK=true     # ask another one when the first cannot take a message
```

`OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` sit side by side; the ones not chosen are spares.

**How strong.** Each company's models are known by level (`src/familydb/agent/providers/catalog.py`); US$ per million tokens in / out, as published September 2026 (Google has said its Flash prices double on January 1, 2027):

| Level | OpenAI | Claude | Gemini |
|---|---|---|---|
| everyday | GPT-6 Luna, $0.10 / $0.50 | Claude Haiku 4.5, $1 / $5 | Gemini 3.1 Flash-Lite, $0.25 / $1.50 |
| better | GPT-6 Sol, $2 / $10 | Claude Sonnet 5, $2 / $10 | Gemini 3.8 Flash, $0.75 / $3.75 |
| best | GPT-6 Astra, $10 / $50 | Claude Opus 5, $5 / $25 | Gemini 3.1 Pro, $2 / $12 |

Everything answers at `everyday` unless chosen otherwise, per situation ("How strong a model answers", AI model page):

```
CHAT_LEVEL=everyday        # answering the family, and answering again after a failure
DIGEST_LEVEL=everyday      # the weekend digest, retries included: once a week, so better costs little
LOOKUP_LEVEL=everyday      # looking ideas up and searching for what is on
```

A level, not a model name, holds on whichever company answers, including after a fallback. A level up never uses a model cheaper than everyday: if the everyday model already costs more than the table's (Claude Opus 5, say) or has no price listed, better and best answer with it too. Each level's box says which model it means for the company answering now, and its cost. A situation on a stronger model than chat has a prompt cache of its own, written on first use.

`everyday` is each company's pair of models, chat and mechanical lookups, defaulting to its cheapest and settable to any name it offers:

```
OPENAI_MODEL=gpt-6-luna
OPENAI_WORKER_MODEL=gpt-6-luna
ANTHROPIC_MODEL=claude-haiku-4-5
WORKER_MODEL=claude-haiku-4-5
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_WORKER_MODEL=gemini-3.1-flash-lite
```

GPT-6 Luna is the default for chat and lookups: the cheapest capable model of the three companies, web search $10 per 1,000. Claude Haiku 4.5 answers without thinking first, so the thinking settings do nothing for it. A model line in `.env` decides everyday until emptied or a page box names another; an older `.env` may still name Claude Opus 5 or Gemini 2.5 Pro, and Opus 5 as everyday leaves nothing stronger for better and best. The page's model boxes suggest known models with level and price but take any name (`claude-fable-5-1`, `claude-opus-5-5`). On a changed name the page asks that company's model list (no tokens) and refuses only on a definite "no such model"; unreachable or keyless, the save goes through. `/status` and `familydb debug cost` print who answers each situation and on which model: the quickest check that a change took.

**Spending.** `DAILY_SPEND_LIMIT` ("Daily spending limit (US$)", Spending page) is $2.00 a day by default over the family's day in its timezone; 0 turns it off. It is checked before every model call (chat, lookup, discovery, digest, voice note). Once used up, chat says "I've reached today's spending limit ($2.00), so I'm stopping here until tomorrow." and lookups wait. A turn under way stops before its next call, so a day can end over by at most one call. The figure is an estimate from a price table; a model the table lacks is counted at $15 / $75 per million input / output tokens, dearer than any listed, so it errs towards stopping. It is not the bill: set a limit on the key in the provider's console too.

Folded under "What one message may use": longest answer (at most 64,000 tokens), steps per message (at most 20) and per lookup (at most 30); on the Lookups page, "How often", ideas looked up at a time (at most 20).

**Keys on the page.** A key stored there lives in `data/familydb.sqlite3`, so it is in every backup (section 7) and copy of that file; a key in `.env` is not. Either is fine on a machine you control; if backups go somewhere you do not, keep keys in `.env`. The page never shows a key back or writes one to its change log. "See a key" (Sign-in and security) shows one once, on that screen, after the password you signed in with is typed again.

**Personality.** `/settings/personality` holds who the bot is: the persona (Vera as first written, Vera in brief, or none), with roughly what each adds to every message; what she is called; her description rewritten in the family's words; "Anything to add", a few sentences on how she talks, which last when her own description is improved; "About the family" (sent with every message, so keep it short); and the lines she uses for everything said unasked. A rewrite is kept for the persona it rewrote, and when her own description has since changed the page says so and shows what. Choosing none keeps every rewrite, name, note and line for when a persona is chosen again. Lines are filled in by code, never a model call; an emptied one goes back to hers. A line may have several wordings, one per row: a message takes one, the same message always the same, and "Reads as" under each box shows it with made-up details. Her name is `{name}` in her description and lines and is filled in wherever she speaks. The bot's name and description in Telegram are her name and her `/start` line, or FamilyDB's under none.

**Undoing a change.** What has changed lists the latest fifty changes (when, by whom, from where). To put a setting back, empty its box: `.env` applies again.

**Worthwhile combination.** Extraction of addresses and hours is most of the volume once lookups are on; if chat moves to another provider for its writing, keep lookups on the cheaper one: `PROVIDER=anthropic`, `WORKER_PROVIDER=openai`.

**Fallback.** A message the chosen provider cannot take (rate limited, unreachable, no key) is asked of another that has a key, but only before any tool has run: once an idea is saved or the calendar written, starting again elsewhere would do it twice, so a turn failing after that stays failed for the retry job. A malformed request is not handed over either (it would fail the same way). `PROVIDER_FALLBACK=false` turns it off.

**Choosing the suggestions.** For a planning question ("what should we do this weekend?", "where should we eat tonight?") and the weekend digest, a stronger model chooses the picks from everything the family has told the bot and done, and the everyday model words them: about 3 to 13 cents a question, depending on the company, within US$5 a month unless changed (AI model, under "Choosing the suggestions"). It goes to the company that answers the chat, nowhere else. Over the month's amount, turned off, or failing, suggestions are made as before. On `/status` it is "choosing what to suggest".

**What differs.** Claude's prompt cache is marked explicitly and lasts `ANTHROPIC_CACHE_TTL`; OpenAI and Gemini cache long prefixes themselves, so that setting does nothing there. Lookups and discovery work on all three. Conversations to OpenAI are sent with storage off. `familydb debug validate-tools` and `familydb doctor --online` check key and tools on Claude and Gemini (token counting, free); OpenAI has no such endpoint, so the first real message checks. Choosing the company and key on the settings page checks the key with the company for free, whichever it is.

## 12. Looking after the server

`scripts/maintain.sh` says what it will change before it does: `status` (running? database size? last backup), `check` (full `familydb doctor`), `backup`, `restore FILE`, `upgrade`, `logs [N]`, `restart`, `schedule-backups`, `https` and `port` (section 10), `password` (a starting password for somebody who forgot). `--help` says more.

**Where things live.** One folder, `/opt/familydb`; `data/` and everything in it is readable by the bot's user alone.

| Path | What it is | In backups? |
|---|---|---|
| `data/familydb.sqlite3` | everything: messages, ideas, plans, places, settings changed from the page, any key stored there | yes, this is the backup |
| `data/google_key.json` | the calendar service account's key | no, make a new key (section 5) |
| `data/web_secret` | signs the login cookie; "Sign everyone out" replaces it | no |
| `.env` | the page's password and address, anything not set from the page | no, keep your own copy |
| `backups/` | the nightly backups, owner-only | they are the backups |
| `caddy/` | Docker `tls` profile only: certificate and private key | no, and keep it that way |

**Firewall.** The bot needs nothing inbound. Behind Caddy or nginx open 80 and 443 (or 80 and the page's own port), and SSH, and nothing else; never 8080, since the page listens on `127.0.0.1` so only the proxy reaches it and the firewall is the second lock on the same door. docs/INSTALL.md, "Looking after the server itself", has the `ufw` commands in the order that does not lock you out, and the two commands that turn on unattended security updates, which matter more than anything else here.

**Logs.** systemd: journald, honoring `SystemMaxUse` in `/etc/systemd/journald.conf` (say `500M` on a small disk). Docker: compose caps each container at five files of 10 MB. Nothing writes a log file of its own. The Telegram token is removed from every log line. `LOG_LEVEL=DEBUG` also logs every HTTP request and is loud.

**Disk.** The install is about 600 MB; the database grows a few MB a year. Backups grow: the nightly schedule keeps `--keep-days` (14) and deletes the rest.

**When a secret gets out.**

- *An API key.* Revoke it in the vendor's console, make a new one, type it on the settings page (immediate) or put it in `.env` and restart. `/status` shows which key each provider uses and from where.
- *The Telegram token.* `/revoke` in BotFather makes a new one and kills the old; paste it on the settings page (within seconds) or in `.env` and restart. The old one then reads nothing.
- *Somebody's page password.* They change their own on Your password (top of every page): it asks for the one in force, keeps that browser signed in, signs their others out, and takes nothing under twelve characters. An admin can make a new starting password (signs them out everywhere) or take theirs away on the Family page. Nothing on the server needs editing; passwords are only hashes. Once an admin has their own, the installer's `WEB_PASSWORD` opens nothing. If the only admin forgot theirs: `maintain.sh password`.
- *A lost phone or too-wide sign-in.* A new starting password for that person signs them out everywhere. "Sign everyone out" (settings, after typing your password again) ends every sign-in on every device, this one included; it cannot while `WEB_SECRET_KEY` is set in `.env`, so change that and restart.
- *The whole server.* The database holds everything the family said. Rotate all the above and assume anything stored on the settings page was read.

**Stopping it for good.** Back up first if the ideas are worth keeping (the database is a plain SQLite file). `scripts/uninstall.sh` does this with a backup and asks first. By hand:

```bash
sudo systemctl disable --now familydb && sudo rm /etc/systemd/system/familydb.service
sudo systemctl daemon-reload
# or, with Docker:
docker compose down                 # add -v only if you mean to delete the volumes
```

## 13. Troubleshooting

Install and server failures (clone, home directory, service starts then stops, permissions, disk, apt lock, out of memory, page does not open, port in use) are in docs/INSTALL.md, Troubleshooting. Log locations are there too.

- **`cache_read` stays 0 in `db status`.** Something volatile is in the cached prefix. `familydb debug prompt "hi"` twice: the instructions (`instructions` on OpenAI, `system` on Claude, `system_instruction` on Gemini) and the `tools` list must be byte-identical; if they differ, a date, name or per-request id has got in, a bug worth reporting with the diff. On Claude, check `ANTHROPIC_CACHE_TTL` is still `1h`: at `5m` a family's gaps between messages outlast the cache. OpenAI and Gemini cache on their own, and not every repeat is a hit.
- **`database is locked`.** Two processes writing. Run one `familydb run`; the CLI alongside it is fine (short transactions, busy timeout).
- **"Got it, but I can't get to it right now."** (no persona: "Saved your message, but I couldn't process it right now.") The model call failed, or the model API is unreachable (wrong or unpaid key, no outbound internet, DNS on a fresh VPS (`ping -c1 1.1.1.1`, `cat /etc/resolv.conf`), a clock more than a day off, which breaks certificates (`date -u`, `sudo timedatectl set-ntp true`)). `journalctl` or `docker compose logs` has the error; `/status` lists the message; `familydb doctor --online` and `curl -sS -o /dev/null -w '%{http_code}\n' https://api.openai.com/v1/models` (401 means reachable) tell the rest. The message is safe: the running bot retries every `RETRY_INTERVAL_MINUTES` up to `RETRY_MAX_ATTEMPTS` and delivers when one succeeds. `familydb db retry-failed` does it by hand; `--reset` re-arms ones that gave up over a configuration problem since fixed. A wrong key goes on `/settings` (immediate) or `.env`.
- **"I've reached today's spending limit ($2.00)"** (no persona: "Today's spending limit ($2.00) is used up"). Nothing more is asked of a model, lookups included, until midnight family time. `/status` shows the estimate against it. Raise it on the settings page if the day was genuine; otherwise see what spent it.
- **"OpenAI says it has no model called X. Check the spelling."** On saving: the company's model list has no such name, so nothing was saved. Correct it or pick a suggestion. An unreachable or keyless company never causes this.
- **"Could not find X on the map."** The home area could not be looked up; type latitude and longitude too.
- **Telegram "the token was refused by Telegram" on `/status`.** Wrong or revoked in BotFather. Paste the current one on the settings page; a refused token is not retried until it changes.
- **Telegram: the bot's name changes back by itself.** The bot sets its name and description in Telegram to the name it goes by and its `/start` line after each connect and whenever either changes on Personality, so a BotFather name lasts only until then. Under none the contact is always FamilyDB; to rename the bot, choose a persona and set her name there. If Telegram refuses, the log says so and it is not retried until either changes or the bot reconnects; if Telegram cannot be reached, it is retried shortly. The bot keeps working.
- **Telegram "cannot reach Telegram; trying again".** The server cannot get out to Telegram; it retries every thirty seconds. If it lasts, check the network and DNS.
- **Google "cannot find that calendar" / "can see that calendar but not change it".** Not shared with the service account, or read-only: the calendar's settings, Share with specific people, "Make changes to events" for the address the page names. The id may also be wrong.
- **Google "Calendar is not turned on in the project".** Enable the Google Calendar API in the key's project, wait a minute, press Connect again.
- **Google Cloud will not make a key.** Some organizations disable key creation; use a project outside the organization.
- **"Google no longer accepts the saved key."** The key or service account was deleted. Make a new key and connect again (section 5). If the page still will not connect, `familydb google connect KEY_FILE CALENDAR_ID` on the server prints Google's answer, and `familydb google events` shows what the bot sees.
- **"no family members yet".** Add yourself on the page (setup opens on it), or `familydb members add NAME --role admin`.
- **"a setting will not do" at startup / `familydb config`.** A value in `.env` is not of the type the setting takes; the line names it. An empty line is fine (not set); `WEB_PORT=eighty` stops it. Quote anything with a space or `#` (a bare value loses everything from the `#`).
- **"stored settings are not usable".** A value in the database no longer validates, usually after an upgrade narrowed what a setting takes. The bot keeps running on `.env` and names the setting; fix or empty that box on the settings page.
- **The service will not start under systemd.** `systemctl status familydb` says why. The three that bite: the `familydb` user missing or not owning `data/` and `.env`; a checkout in a home directory; `ProtectHome=true` with a checkout under `/home`. Section 2b.
- **"Sorry, I only talk to the family."** The sender is not on the family list for that channel; they appear on the Family page under "Asked to talk to the bot" with an add button, and the reply includes their id.
- **A refusal.** Rare. `llm_calls.stop_reason` is `refusal`; Claude's server-side fallbacks are on by default (`ANTHROPIC_FALLBACKS`), so it means every model declined.
- **Replies come from the wrong provider.** `/status` or `familydb debug cost` says who answers each surface. Probably another stands in because the chosen one has no key; the log says so at the time.
- **"validation failed" from `debug validate-tools`.** That check counts tokens, which Claude and Gemini offer and OpenAI does not. With `PROVIDER=openai`, send a real message, or point `PROVIDER` elsewhere for the check.
- **"details: failed" on an idea.** The worker could not identify the place; `ideas list --json` shows the note. Fix the title or location ("actually it's the one in Vancouver", or the idea's page) and run `familydb enrich --idea N`.
- **Suggestions say "web discovery off" or "hours unknown".** Lookups are off, the idea is not looked up yet, or the day's limit is used up; enrichment runs only in the long-running `familydb run`.
- **The digest never arrives.** The Weekend digest row on `/status` and `familydb digest` show schedule and chat; the log says why a run was skipped (no chat, nothing to send, no admin). For a Telegram group the bot must be in it and see its messages (section 4, step 3).
- **"the web page is not serving" in the log.** Settings forbid it (page off the loopback or behind a proxy with no password: no 12+ character `WEB_PASSWORD`, no family password chosen, nobody with their own), or the port is taken (`maintain.sh port`). Behind Caddy the browser shows a 502 (`journalctl -u familydb -n 40 | grep 'not serving'`). The bot keeps running.
- **The page asks for the password again and again.** The login cookie is not coming back: `data/` unwritable so the signing key changes each start (`ls -l data/web_secret`; or set `WEB_SECRET_KEY`, also needed with more than one process), or over HTTPS `WEB_TRUST_PROXY` is not true so the `Secure` cookie is never set. Changing a password (anybody's, or `WEB_PASSWORD` while shared) or "Sign everyone out" ends sessions opened with the old one, on purpose.
- **"Too many tries. Wait a quarter of an hour and try again."** Five wrong passwords from one address, or fifty from anywhere (a browser that has signed in before is spared the second). Waiting is the only way through, which is the point.
- **The page is unreachable from another device.** `WEB_HOST` is still `127.0.0.1` or the compose `ports` line still starts `127.0.0.1:`; both must change, with a password set. On the internet use HTTPS (section 10).
- **A setting in `.env` does nothing.** Something on the settings page is set for it and wins. `familydb config` shows where each value came from; empty the page's box.
- **A changed digest hour or lookup interval did not take effect.** They move within five minutes (`journalctl` shows "settings changed"); beyond that, worth reporting.

## 14. Checking it against live accounts

Tests run against fakes of every provider, Google, Telegram and the weather, and CI installs on a real machine, but nothing automatic talks to a real model, Telegram bot or Google account. Before the family relies on a new install, or after an upgrade touching one of them, go through this with a dedicated test calendar:

1. Install with [docs/INSTALL.md](docs/INSTALL.md), follow the setup, run `familydb doctor --online`, deal with what it says.
2. Save the key and model on the settings page (the company is asked whether the model exists, free; every lineup id in `agent/providers/catalog.py` came from published documentation and this is its first live check). Check capture, a lookup, discovery and scheduling, and that `/status` shows today's spend. Set a limit on the key in the company's console.
3. Paste the Telegram token on the settings page: within seconds `/status` says "connected as @…". Add each person's Telegram id on the Family page; check two people in private chat and in the family group.
4. Connect Google Calendar (section 5).
5. Create, move and cancel a test event from chat. Edit one in Google and check the plans page and the next chat edit follow. A busy all-day trip must block suggestions; a transparent birthday must not.
6. Restart the service mid-answer, interrupt delivery for a while: both recover. Restore a fresh backup onto a separate test install and check recent records.
7. Reboot: it starts, keeps its data, logs, serves the page and takes its backups. Keep the page private or behind HTTPS, an off-machine backup, and a separate copy of `.env` and the Google credentials.
8. With something on the calendar this afternoon, ask "I'm bored, what can we do now?", "anything for tonight?", "what about Saturday morning?": free times exclude the event and the part of today gone, and an option says when it can start ("can go 16:10-17:55 today"). Two differently worded weekend questions with discovery on: one discovery search on `/status`. Within a couple of hours of sunset, "anything outdoors tonight?" offers an outdoor idea longer than the daylight left as one in the dark (sunrise and sunset were read).
9. Add a restaurant idea: its lookup on `/status` ends at `save_place` with no call after; a "home" idea with no place is skipped with no call. A web chat question sent during a lookup must not wait for it.
10. Away from home, share your location on Telegram and ask "what's open near here?": options measured from there, and the reply says so. With a live location, move a few streets and ask again: it names where you are now, with no second "Got it", and none when you stop. On the web chat over HTTPS, tick "Send where I am" and ask the same; untick, send "thanks": no position kept for that message.
11. Reminders, taps and commands:
    - A reminder a few minutes ahead, service stopped past its time and restarted: arrives once, says when due. One a minute ahead while chatting in that chat: the next reply carries it, buttons under it.
    - In the family group tap "In an hour": everyone sees who snoozed and until when, buttons gone, back an hour later; "✓ Done" does not come back. Somebody not on the list who taps is told only the family can; nothing changes. The day after a plan, tap an answer under "how was it?" and check the idea's page.
    - A daily task a few minutes ahead: it comes, and again next day; ticked off, it still comes the day after.
    - "Grandma would love a gardening apron", then Grandma's birthday with a reminder a few minutes ahead: the reminder lists the apron; its page says "not one place to look up", with no lookup in the status costs.
    - Telegram "/": today, week, tasks, now are offered and each answers at once with no model call on the status page (/today, /week as Google shows, /tasks this chat's only, /now what could start in the next few hours). From somebody not on the list, /today gets the stranger's line.
    - An outdoor idea tomorrow when the forecast says rain, evening check set to the next hour: one heads-up, with an indoor idea for the same time if one fits; a dry day gets nothing.
    - On a Wednesday, "one of these Thursday evenings I need to fix the bike light": the answer and tasks page say it comes up on a free Thursday evening. On Thursday it comes up once, with buttons, from 18:00 if clear, or once an hour is free after whatever is on, and not again that day.
12. On `/settings/personality`, rewrite one of her lines and add a sentence to "About the family": the next reminder or follow-up uses the line, the next answer knows the sentence. Rename her: "what's your name?" gets it in chat and Telegram, and within seconds the bot's Telegram name and description are hers. Rewrite her description, add an "Anything to add" line, choose no persona: replies are plain (her lines and your rewrites included) and the Telegram contact is FamilyDB. Choose her again: name, rewrite, notes and lines are all back. Choose Vera in brief: about 740 tokens a message before your notes, and everyday requests answered as well as before.
13. With the chosen model's key in the environment run `uv run python -m evals` (stops once $0.50 is spent unless `--budget` says otherwise, so only the call that crosses it can go over) and read what failed before the family does.

After a week of use read `/status` and `familydb debug cost` by kind before changing anything for cost: at GPT-6 Luna's prices the chat prefix is about $0.0006 a message and each web search $0.01, so lookups and discovery, not chat, are where the money goes.

What these checks will not change, by design:

- Telegram delivery is at least once. It has no idempotency key, so a send that succeeded but whose answer was lost can arrive twice, as can chunks of a split long reply. Resending never runs the model or repeats a calendar write.
- Creating an event is deduplicated within one message (same event, said the same way). A new message can deliberately create another; the operation log does not detect events that merely look alike.
- Travel is a straight-line estimate, from home unless someone shared their location in the last three hours or named where they are; the forecast is per day. Nothing checks real reservations or ticket availability.
- The daily limit is an estimate from a price table checked by hand, not the bill.
- The Anthropic and Gemini request shapes follow the companies' documentation on [extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking), [web search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool), [web fetch](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool) and [combining tools](https://ai.google.dev/gemini-api/docs/generate-content/tool-combination); what a live account accepts is part of these checks.
