# Runbook: running FamilyDB on a home server or a VPS

Two supported ways to run it: Docker Compose, or a Python virtualenv managed by systemd. Both use the same `.env` file and the same `data/` folder for the database and tokens. Pick one.

Almost everything is set up on the web page once it is running: the model and its key,
Telegram, Google Calendar, where home is and what it may spend. The files are for what the page
cannot decide for itself, such as how the page is reached and its password.

## Requirements

- Linux with either Docker (with the compose plugin) or Python 3.11+ and [uv](https://docs.astral.sh/uv/).
- Outbound HTTPS. The bot itself needs no inbound ports. The web page is kept to the machine
  itself unless you give it a domain, and then it needs ports 80 and 443 (section 10).
- A key for one of the three providers: OpenAI, which answers by default, Anthropic or Gemini
  (section 11). You type it on the settings page.

## 1. Get the code and the config

**Starting from a bare server, use [docs/INSTALL.md](docs/INSTALL.md) instead of this section.**
It covers preparing the machine, getting the code onto it (the repository is private, so that is
a step of its own), and the one command that does the rest:

```bash
sudo bash scripts/bootstrap.sh
```

This section is the configuration half, for a machine that already has the code and a runtime:

```bash
sudo mkdir -p /opt/familydb && sudo chown "$USER" /opt/familydb
git clone <this repo> /opt/familydb && cd /opt/familydb
sudo scripts/install.sh
```

The installer asks one thing: the domain name for the web page (leave it empty to keep the page
on this machine). Everything else is done on the page afterwards, starting with adding yourself
on the Family page. It writes `.env`, installs the dependencies and creates the database. It picks Docker when it finds it and a virtualenv otherwise, and it is safe to run
again: it never overwrites `.env` without asking and never touches the database. Sections 2a and
2b below are the same steps by hand.

What it decides without asking:

- The web page is on (`WEB_ENABLED=true`) and always has a password. Unless you give one in
  `WEB_PASSWORD` (twelve characters or more), it makes one up and prints it once. Write it down;
  it is in `.env` too, and nowhere else.
- The timezone comes from the machine. The settings page changes it.
- Web lookups are on (`WEB_TOOLS_ENABLED=true`), and the weekend digest goes to the page's own
  chat (`DIGEST_CHAT_ID=web`). Both can be changed on the page.
- With a domain, it writes `WEB_DOMAIN` and `WEB_TRUST_PROXY=true`. With Docker it also writes
  `COMPOSE_PROFILES=tls`, so every `docker compose up -d` starts Caddy for HTTPS as well. With a
  virtualenv it offers to install Caddy with apt, write `/etc/caddy/Caddyfile` from
  `deploy/Caddyfile` with your domain in it, and reload Caddy. Either way, open ports 80 and 443
  (`sudo ufw allow 80,443/tcp`) and point the domain at the machine.
- `data/` is made readable by its owner alone, and a nightly backup is scheduled in root's
  crontab at 03:15, keeping fourteen days (section 7). It installs cron with apt if the machine
  has none. `BACKUPS=no` skips this.

It ends by telling you where the page is: `https://your.domain/`, or, with no domain, through an
SSH tunnel (`ssh -L 8080:127.0.0.1:8080 you@server`, then `http://127.0.0.1:8080/`). Sign in, and
follow the "Finish setting up" list on the home page (section 3).

Useful flags: `--mode docker|venv` to choose, `--config-only` to write `.env` and stop,
`--dry-run` to see what it would do, `--yes` to take every default, and `--non-interactive` to
read every answer from the environment. `scripts/install.sh --help` lists the variables it reads.
For a scripted build it also writes any of `PROVIDER`, the three `*_API_KEY`s,
`TELEGRAM_BOT_TOKEN`, `FAMILYDB_TZ`, `HOME_AREA`, `HOME_LAT`, `HOME_LON`, `WEATHER_UNITS`,
`WEB_HOST`, `WEB_PORT` and `DIGEST_CHAT_ID` that it finds in the environment:

```bash
WEB_DOMAIN=family.example.com ADMIN_NAME=Sam OPENAI_API_KEY=sk-... \
  scripts/install.sh --non-interactive --mode docker
```

To set everything up by hand instead:

```bash
cp .env.example .env
nano .env        # WEB_ENABLED=true and a WEB_PASSWORD of 12+ characters; the rest on the page
mkdir -p data && chmod 700 data
```

`.env.example` leaves the page, the lookups and the digest off, unlike the installer, so turn on
what you want.

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

`FAMILYDB_PATH` and `GOOGLE_TOKEN_PATH` are set inside the container to `/data/...`; the compose
file mounts `./data` there. With `COMPOSE_PROFILES=tls` in `.env`, `docker compose up -d` starts
the Caddy container too (section 10).

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

`scripts/install.sh` does all of this, the user included. Check `User=` and the paths in the unit
if you cloned somewhere other than `/opt/familydb`.

**Clone it into `/opt`, not your home directory.** A home directory is closed to other users on
most systems, and the service runs as `familydb`, so a unit pointing inside `/home/you` cannot
start: systemd reports a permission error on the working directory. The installer checks this
before it writes a unit and tells you to move the checkout rather than leaving you one that will
not start. If you do want it under `/home` anyway, the directory above it has to be traversable
by the service user (`chmod o+x /home/you`), and the unit needs `ProtectHome=read-only` instead
of `ProtectHome=true`, which the installer sets for you.

The unit sets `FAMILYDB_PATH` and `GOOGLE_TOKEN_PATH` under `/opt/familydb/data` and locks the
service down to that folder: `UMask=0077`, so nothing it writes is readable by another account,
and sandboxing such as `PrivateDevices`, the `ProtectKernel*` settings, `RestrictAddressFamilies`
and `SystemCallFilter=@system-service`. To chat from the shell, run commands as the service user
so the database stays owned by it: `sudo -u familydb /opt/familydb/.venv/bin/familydb repl`.

Every `familydb` command runs with a umask of 077 as well, and `familydb run` and `familydb web`
make an older database, its write-ahead files, the Google token and `data/web_secret`
owner-only when they start, if an earlier version left them readable by others.

Without uv: `python3 -m venv .venv && .venv/bin/pip install .` gives the same `.venv/bin/familydb`.

## 3. First run checklist

Open the page (section 10) and sign in with the password the installer printed. The home page has
a "Finish setting up" list of what is missing, most important first, each with a link to where it
is done:

1. Yourself, as an admin, then the rest of the family (the Family page).
2. Your own password, which ends the installer's: from then on everybody signs in as themselves,
   and you give each of them a starting password on the Family page.
3. A model key (settings, API keys). Until there is one, it saves what it is told but cannot answer.
4. Where home is (settings, Home), for the weather and for what is on nearby (section 6).
5. Google Calendar (settings, Google Calendar), so plans land on the family calendar (section 5).
6. A Telegram bot (settings, API keys), so the family can message it from their phones (section 4).
7. Only once there is a Telegram token: each person's Telegram id (the Family page).

The list disappears when everything on it is done. Then try it on the Chat page: "we should try
that new ramen place on Main St sometime" saves idea #1, and "tell me about #1" answers from
history. `/status` says which model answered, what is connected, and what today has cost.

From the shell instead, `familydb doctor` looks at all of this in one command and says what to do
about anything that is wrong; `--online` also asks Telegram and the model API whether the keys
work, and `--fix` puts right the few things that can be put right without a decision. The rest,
one at a time:

1. `familydb config` shows the settings you expect (keys are masked) and where each came from.
2. `familydb db migrate` reports the schema version.
3. `familydb members add` for everyone who will message the bot (admin or member) and for kids (`--role kid`) so they can be named as participants. The Family page does the same.
4. `familydb chat "we should try that new ramen place on Main St sometime"` saves idea #1.
5. `familydb chat "tell me about #1"` answers from history.
6. `familydb db status` shows `cache_read` greater than zero on the second call. If it stays zero, see troubleshooting.
7. `familydb debug validate-tools` confirms the API accepts every tool schema. It works on Claude and Gemini only; on OpenAI, the default, there is no free way to ask, and the first real message is the check.
8. `familydb tool --list` shows which integrations are available; the calendar and weather rows flip to `available` once sections 5 and 6 are done.
9. `familydb suggest --window this-weekend` prints what the engine would say about the ideas so far, with the checks it had to skip.

## 4. Telegram

1. In Telegram, talk to BotFather: `/newbot`, pick a name and a username, and copy the token it
   gives you. Paste it on the settings page under API keys, as the Telegram bot token. It takes
   effect within seconds, with no restart. `/status` then says "connected as @yourbot", "the
   token was refused by Telegram" or "cannot reach Telegram; trying again". A token put in
   `TELEGRAM_BOT_TOKEN` in `.env` instead is read when `familydb run` starts.
2. Each family member sends the bot a direct message. It does not answer strangers, but it
   notes who asked (id, Telegram name, when; never what they said, and only for a month), and
   the Family page lists them under "Asked to talk to the bot" with a button to add each one.
   The reply also tells them their id, for an admin to type into their Telegram id on the Family
   page instead, or to use with `familydb members add NAME --channel telegram --channel-user-id
   12345`. Their next message gets a real answer.
3. For a family group, send BotFather `/setprivacy` and choose Disable so the bot sees every message, then add the bot to the group. A dedicated "Ideas & Plans" group works best. In a busier group set `TELEGRAM_REQUIRE_MENTION=true` so it only answers when @mentioned or replied to.
4. To get suggestions measured from where someone is rather than from home, they share their location with the bot (the paperclip, then Location; a live location keeps itself current for as long as they choose). On the web page's chat, ticking "Send where I am" (beside Send) asks the browser for the location and sends it with each message until the box is unticked; it stays as it was left for that browser, is off to begin with, and needs the page on HTTPS (or opened on the server itself). The bot uses the latest position for three hours for "near here" and "open now" questions, keeps only the latest one per person, deletes it after a day (within ten minutes of that, while the service runs, whether or not anyone shares again), and sends the place's name and coordinates to the model provider with the message. Nothing is sent unless someone shares it or ticks the box.
5. Long polling means nothing is exposed; if the server is off, Telegram keeps updates for a day and the bot catches up on restart without double-processing.
6. Voice notes work like typed messages, as long and rambling as anyone likes: a speech model writes the words down and the bot answers them, doing everything they ask for (an idea, a plan, a change to one, something to remember). The words are kept as the message, marked "(voice note)"; the recording itself is not kept. Claude cannot hear, so voice notes need an OpenAI or Gemini key even when the chat runs on Claude; with neither, the bot says so and asks for the message typed. Settings, "Voice notes": turn them off, cap their length (5 minutes unless changed; a longer one is not heard at all), and choose who hears them and with which model. Hearing is a model call like any other: it counts against the daily limit and shows on `/status` as "listening to voice notes", about $0.003 a minute on OpenAI's gpt-4o-mini-transcribe. A voice note that could not be heard (the service down, no words in it) is not retried, since the recording is gone; the bot asks for it again.

## 5. Google Calendar

The Google Cloud side is done once, in a browser:

1. Create a Google Cloud project and enable the Google Calendar API.
2. Configure the OAuth consent screen as External and set the publishing status to **In production**. Left in Testing, refresh tokens expire after seven days and the bot stops writing to the calendar every week. The "unverified app" warning during consent is expected for a private app.
3. Create OAuth credentials of type **Desktop app** and download the JSON. A client of type Web
   application will not do; the page says so if you paste one.

Then connect it from the settings page, which needs no laptop and nothing copied to the server:

4. On `/settings`, under Google Calendar, paste the client's JSON and press "Get the consent link".
5. Open the link, sign in as the account that owns the family calendar, and allow access.
6. Google then sends the browser to an address starting `http://127.0.0.1:53682/`, which will
   not load. That is expected. Copy the whole address from the address bar, paste it into the
   page, and press Connect. Do this within a quarter of an hour of getting the link, and without
   restarting the bot in between, or start again.
7. Choose the family calendar from the list. A calendar you can only read is marked, since the
   bot could not put plans on it.

The token is saved owner-only at `GOOGLE_TOKEN_PATH` (`data/google_token.json`). This way of
connecting has not yet been tried against a live Google account, so try it first, and if it
will not work, use the laptop instead:

- On a laptop with a browser (not inside Docker), run
  `uv run familydb google auth --client-secrets ~/Downloads/client_secret_XXX.json` and sign in as
  the calendar's owner. It writes `data/google_token.json`.
- `uv run familydb google calendars` lists the calendars and their ids. Put the family calendar's
  id in the Google calendar id box on the settings page (under Home), or in `GOOGLE_CALENDAR_ID`.
- Copy `google_token.json` into the server's `data/` folder, owned by the bot's user and mode
  600, and restart the bot.

Either way, check with `familydb google events`. A dedicated family Google account keeps the
bot's token separate from anyone's personal mail. From chat, "we're going to the symphony next
Saturday at 8" now creates the event; "move that to Sunday" and "cancel the symphony" update it.

## 6. Weather

On the settings page, under Home, type the Home area as you would tell someone ("Vancouver,
WA") and leave latitude and longitude empty: the page looks the place up on OpenStreetMap's map
and fills them in, and says what it found. Coordinates you type yourself win. Units chooses
metric or imperial. In `.env` the same are `HOME_AREA`, `HOME_LAT`, `HOME_LON` and
`WEATHER_UNITS`. Open-Meteo needs no API key. Check with
`familydb tool get_forecast --json '{"start": "2026-09-26", "end": "2026-09-27"}'`.

## 7. Backups

The database is one file, and everything the family has said is in it. The installer already
scheduled a nightly backup; this is the same thing by hand:

```bash
sudo scripts/maintain.sh schedule-backups --keep-days 14
sudo crontab -u root -l
```

That puts one line in root's crontab, for Docker or systemd alike: at 03:15 it takes a backup
into `backups/` with SQLite's online backup, which is safe while the bot runs, and only when that
succeeded deletes backups older than `--keep-days`. `sudo scripts/maintain.sh backup` takes one
now. Each backup is readable by its owner alone.

The same without the script, in root's crontab (`sudo crontab -e`), for a systemd install:

```
15 3 * * * sudo -u familydb env FAMILYDB_PATH=/opt/familydb/data/familydb.sqlite3 /opt/familydb/.venv/bin/familydb db backup /opt/familydb/backups/familydb-$(date +\%F).sqlite3
```

`FAMILYDB_PATH` is set there because cron runs with no working directory to speak of, and the
default path in `.env` is relative to the checkout. Without it the backup would have nothing to
copy; it says so and writes nothing rather than backing up an empty database. The `backups/`
folder must be writable by `familydb`.

With Docker: `docker compose exec bot familydb db backup /data/backups/familydb-$(date +%F).sqlite3`.
Keep a copy off the server: a backup on the same disk is not a backup. Calendar events are also
in Google.

**Restoring one.**

```bash
sudo scripts/maintain.sh restore backups/familydb-XXXX.sqlite3
```

It stops the bot, backs up the database it is about to replace (so a restore can be undone),
puts the backup in place, clears the old write-ahead files, sets the owner and permissions,
migrates and starts it again. By hand, stop the bot first, because the file it has open is the
one being replaced:

```bash
sudo systemctl stop familydb                       # or: docker compose stop bot
sudo -u familydb cp backups/familydb-2026-09-14.sqlite3 data/familydb.sqlite3
sudo -u familydb rm -f data/familydb.sqlite3-wal data/familydb.sqlite3-shm
sudo systemctl start familydb                      # or: docker compose start bot
```

The write-ahead files belong to the database that was replaced, so they go too; SQLite makes new
ones. `familydb db status` afterwards shows the row counts and the schema version, and a restored
file from an older version is migrated on the next start.

An API key or Telegram token stored from the settings page lives in this file, so it is in every
backup. That is the price of being able to change a key from a phone. If these backups go
anywhere you do not control, keep the keys in `.env` instead (section 11) and the backup holds
none.

## 8. Upgrades

```bash
sudo /opt/familydb/scripts/maintain.sh upgrade
```

It takes a backup, fetches, moves to the newer code, reinstalls the locked dependencies (or
rebuilds the Docker image), applies any new migrations and restarts, then prints the command to
go back if it went badly. On a private repository the fetch needs a credential; docs/INSTALL.md,
section 8, says how.

Which code it moves to: while the newest heading in `CHANGELOG.md` says "in progress" (as
`v0.1.0` does now), bootstrap installs the default branch and `upgrade` follows it. Once a
version heading carries a date instead, both follow the newest release tag. An upgrade only
ever moves forward: if the target does not contain what is installed now, it refuses and changes
nothing rather than taking the database back past migrations it has already run. To pin a tag,
branch or commit when installing, use `bootstrap.sh --ref NAME`.

Migrations also run on every start. Never edit an applied migration; add a new numbered file.
Check `systemctl status familydb` or `docker compose logs bot` once it is back: a setting that no
longer validates is named in one line rather than stopping silently.

Two upgrades from an older checkout ask something of you once:

- Everyone signs in to the page again the first time after upgrading past the change that ties a
  session to the password it was opened with. Nothing is wrong; it happens once.
- After upgrading to the version where each person signs in as themselves, the family password
  keeps working until an admin chooses their own (the setup page's "Your own password", or Your
  password at the top of any page). From that moment it opens nothing: give everybody else a
  starting password on the Family page first, or straight after.
- The `tls` profile now keeps Caddy's certificate in `caddy/` rather than `data/caddy`, so that a
  private key is not inside the bot's volume and its backups. Move the old folder across before
  starting, or let Caddy ask for a fresh certificate, which it will do on its own:
  `mv data/caddy caddy`. Any copy you made of the whole `data/` folder holds the old key, so
  delete it; `familydb db backup` copies only the database and never held one.

## 9. Lookups, the weekend digest and follow-ups

**Looking ideas up.** On by default after the installer ("Look ideas up on the web" on the settings page, `WEB_TOOLS_ENABLED` in `.env`). Every `ENRICH_INTERVAL_MINUTES` the bot takes up to `ENRICH_BATCH` new ideas and, in a separate small model call with web search, finds the place, its address, hours, booking link and price notes, geocodes it (OpenStreetMap's Nominatim, no key) and estimates the drive from home. It then posts one line to the chat where the idea was captured ("Looked up #57 Hopscotch Portland: open Sat 10:00-20:00 · about 45 min away (estimate)"); turn off "Say in the chat when an idea is filled in" to keep quiet. Ideas that are not one place ("a picnic somewhere"), and home ideas with no place, link or location, are skipped without a model call, and ideas the worker cannot identify are marked failed and left alone; `familydb enrich --idea 57` redoes one by hand, `familydb ideas list` shows the `details:` state, and `familydb tool describe_idea --json '{"id": 57}'` shows what was saved. Details older than `PLACE_STALE_DAYS` are refreshed the next time the idea comes up in a suggestion. With lookups off, nothing is looked up and suggestions say "hours unknown". Once the daily spending limit is used up, lookups wait for tomorrow.

**Suggestions.** "What should we do this weekend?" runs the engine once: free time from the calendar, the forecast, every idea against the looked-up details, and, with lookups on, a search for time-bound things near the home area (cached for twelve hours, shared by questions that ask for the same window, constraints and kind of thing). Each verdict is logged in `suggestions`. It works in minutes, not parts of the day: "I'm bored, what now?" looks at the next few hours, "tonight" at the evening, and an answer for today says when they could be there ("can go 16:10-17:55 today"). `familydb suggest --window this-weekend --discover` runs the same engine from the shell.

**Weekend digest.** The installer sends it to the chat on the web page (`web`), which needs no id looked up and so works from the first Thursday. To send it to the family's Telegram group instead, add the bot to the group and have somebody on the family list mention it there once; the Digest chat box on the settings page (under "When it speaks first") then offers that group among the chats the bot has seen, by when each was last written in. Pick it and save; empty the box and no digest is sent. A Telegram group's id is a negative number, and can be typed in by hand too. Digest day and hour (default Thursday 18:00 in the family's timezone) are on the same part of the page; `familydb digest` prints the schedule and `familydb digest --now` posts a digest immediately. The digest is asked as the first admin and stored like any message, so it goes out at most once a day; if the model call fails it is retried like a failed message, and if the bot was off at the scheduled hour it sends the digest a minute after it next starts on the same day.

**Follow-ups.** The morning after a plan (`FOLLOW_UP_HOUR`, default 10:00), the bot asks "How was #57 Hopscotch Portland on Saturday? Worth doing again?" in the chat the plan was made in, once per plan, unless someone already said how it went. The answer is recorded as feedback and feeds future suggestions. `familydb follow-ups --now` asks by hand. It makes no model call.

**Reminders.** A task given a reminder time ("remind me on Tuesday at 9 that we need paper towels", or on `/tasks`) is sent once, when it is due, to the chat it was asked in; browser and console reminders go to the page's chat. A job checks every minute and makes no model call. It runs only in `familydb run`, not `familydb web`; one that fell due while the bot was off is sent when it starts again, and says when it was due. If the family is talking in that chat at the time, the reply they are about to get carries it instead; the follow-ups and lookup notes are handled the same way.

**Cost.** Enrichment is at most three searches and three page reads per idea; discovery at most four searches per window and question kind per twelve hours. Both run on the lookup model (GPT-6 Luna by default, the same as chat; section 11), and all of it counts towards the daily spending limit.

## 10. The web page

The page is the bot's front door. The home page shows what is coming up and, until everything is
connected, the "Finish setting up" list (section 3). Then: Chat, to talk to the bot as a family
member would; the ideas list with search and filters, and one idea in full with its hours,
travel estimate and booking link; the restaurants on their own page; the plans as a list or as a
month, read live from Google Calendar when it is connected and from the saved plans when it is
not; things to do and their reminders; Family, for who the bot talks to; and the status and
settings pages (section 11), with the Personality page beside them. The forms add and change
ideas and tasks, record how things went, and create, move and cancel plans, through the
same tools the bot itself uses, so nothing done on the page is anything the bot could not do.

The installer always turns the page on, with a password. There are two ways to reach it.

**Kept to the machine, over a tunnel.** With no domain, the page is bound to `127.0.0.1` (with
Docker, the compose file publishes it to `127.0.0.1:8080`). From your own computer run
`ssh -L 8080:127.0.0.1:8080 you@server` and open `http://127.0.0.1:8080/`, or use Tailscale. That
is the safest option and opens no port.

**On a server on the internet, over HTTPS.** Give the installer a domain, point the domain at the
machine, and open 80 and 443 (`sudo ufw allow 80,443/tcp`). The installer has then written:

```
WEB_ENABLED=true
WEB_PASSWORD=...                 # made up and printed once, unless you gave one
WEB_TRUST_PROXY=true
WEB_DOMAIN=familydb.example.com
COMPOSE_PROFILES=tls             # Docker only: `docker compose up -d` starts Caddy too
```

With Docker, the Caddy container gets the certificate and keeps it, with its private key, in
`caddy/` beside the checkout, deliberately not inside `data/`: a key in there would be readable
from the bot's container and would land in every backup. With a virtualenv, Caddy runs on the
machine from `deploy/Caddyfile`, which the installer offered to install; to do it yourself, the
steps are at the top of that file. If nginx is already there, `deploy/nginx-familydb.conf` does
the same with a certificate from certbot, and works on a port other than 443. Both have been
tested with a real browser signing in and posting a form over HTTPS. Keep `WEB_HOST=127.0.0.1`
on a virtualenv install so nothing but the proxy can reach the page, and never open 8080.

`WEB_TRUST_PROXY` makes the page believe the forwarding headers from exactly one proxy hop, to
learn the real visitor address and that the connection was HTTPS, and marks the login cookie
`Secure` so it never crosses plain HTTP. With the page on the loopback it trusts only a proxy on
this machine; bound to `0.0.0.0`, as in Docker, it trusts whatever connects, which is safe there
only because the compose file publishes the port to `127.0.0.1` alone. A visitor who sends a
forged `X-Forwarded-For` is ignored. Only turn it on with a proxy actually in front. Behind a
proxy a password is always required, however the page is bound.

**On a server on the internet with no domain.** Give the installer the server's public IP
address instead (virtualenv path). It is the same arrangement as a domain, except that Caddy
signs the certificate itself (`tls internal` in `/etc/caddy/Caddyfile`), so every browser warns
once per device before it trusts it. The connection is still encrypted. docs/INSTALL.md section
6 has the Caddyfile, for an install made without it.

**At home, on the local network.** To reach the page from other devices without a domain, set
`WEB_HOST=0.0.0.0` in `.env`, and with Docker change the compose `ports` line to `"8080:8080"`.
The page then answers at `http://<server>:8080/`. A page that faces the network needs passwords
of at least twelve characters, because a password is all that guards it and there is no second
factor. `WEB_PORT` moves it off 8080, a port scanners try early, onto any other above 1024.

**A port scans rarely try.** What a scan of a server finds is what listens on its public
addresses. The page's own port, 8080, is not among them: it listens on `127.0.0.1`, or in Docker
is published to the loopback alone, so only Caddy on the same machine can reach it. What a scan
finds is Caddy, on 443 (and 80, for certificates), and SSH on 22. 443 is the third port nmap
tries and the one every sweep of the internet looks at, so a page there is found by anything that
looks. To serve it on another port instead:

```bash
sudo /opt/familydb/scripts/maintain.sh https --port random   # or --port 24613, or --port 443 to go back
```

`random` picks one from 20000 to 29999 that nothing on the machine uses and that is not among
the thousand ports nmap tries unless told to try more. The page is then
`https://your.domain:PORT/`: bookmark that, since the old address finds nothing. Caddy serves
HTTPS on that port only, and asks for certificates only by the check a certificate authority
makes on port 80 (the other kind needs 443); it listens on 80 just while it is being checked, and
sends nobody who tries it anywhere, so 80 gives nothing away. `ufw` is opened for 80 and the new
port, and the rule for 443 is closed if the installer opened it. Allow the new port in a
provider's own firewall too, if it has one. With Docker, put `WEB_PUBLIC_PORT=PORT` in `.env` and
run `docker compose up -d`: the Caddy container still listens on 443, and the host publishes it
on that port. At install time, `WEB_PUBLIC_PORT=random` in front of the installer does the same.

Be clear about what this buys. It takes the page out of the sweeps that try the usual ports, which
is most of them, and so out of the log noise and the opportunistic guessing that follow; the
lockouts would stop those anyway. It is not a lock: a scan of every port of this one machine
still finds it in minutes, and a domain's certificate is published in the public certificate
logs the moment it is issued, which is how new sites are found. The passwords and lockouts are
what keep the page shut. For a page nobody on the internet can find at all, keep it off the
internet: install with `--local-only` and open it over an SSH tunnel, or use a private network
such as Tailscale, which puts no port on the internet whatever.

**Who signs in.** Each person signs in as themselves, with their name as it is on the Family page
and a password of their own, stored only as a scrypt hash. An admin gives everybody else a starting
password there, shown once, and each person chooses their own the moment they sign in with it; a new
starting password, or taking a password away, signs that person out on every device, which is what
to do for a lost phone. There are three roles. A parent uses the bot (chat, ideas, plans, things to
do, status); an admin also reaches Settings, the setup pages and the Family page; a kid may, for
now, do whatever a parent may, and gets limits of their own if the family ever wants them, in one
table (`src/familydb/roles.py`) that the whole page asks. The chat speaks as whoever is signed in,
and the settings history says who changed what. Until the first admin chooses their own password,
the page takes the one the installer made up, or one the family chose to share on the settings page;
that admin's own password ends it for everyone, and from then on there is always an admin who can
sign in, so it never comes back. For the last admin who forgot theirs, `sudo
/opt/familydb/scripts/maintain.sh password` prints a new starting password (`password NAME` does it
for somebody else).

**What protects it.** Every password is checked in constant time, and a name that is nobody's is
checked against a decoy so it takes as long as a wrong password and gets the same answer. Everyone
types theirs once and the sign-in lasts `WEB_SESSION_DAYS` (30 by default). Five wrong passwords
lock that address out for fifteen minutes and are logged. Fifty failures from anywhere within a
quarter of an hour stop new sign-ins altogether, except from a browser that has signed in before: it
carries a signed "known device" cookie (`familydb_device`) for a year, which stops being honoured
after the password it was earned with changes or after "Sign everyone out". So a guesser with many
addresses gets nowhere and the family still gets in. Every page but the login and `/healthz` needs
the cookie. Responses carry a content security policy that forbids framing and any script but the
page's own one file, which sends the phone's location with a chat message; the chat waits for its
answer with a meta refresh, and everything works with scripts turned off. Every form carries a token
from the session as well, so a link from another site cannot make a change on the family's behalf.
Refusing to start is deliberate: a page bound off the loopback with no password will not serve, and
says so, unless you set `WEB_ALLOW_NO_PASSWORD=true` on purpose, and behind a proxy it will not
serve without one at all.

Be clear-eyed about what signing in buys someone. A parent's password (or, for now, a kid's) is most
of the bot: the chat page spends tokens with every message, and the forms add and change ideas,
record outcomes and put things on the family calendar. An admin's is all of it: the Family page
decides who may message the bot on Telegram and who signs in, and the settings page can change which
model answers, raise the spending limit, show an API key to whoever knows that admin's password, and
point the bot at a different calendar. On a machine on the internet, those passwords are what stand
between a stranger and your API bill; the daily spending limit bounds a day, but the figure is an
estimate, so set a limit on the key with the provider too. Nothing is destroyed — an idea is dropped
rather than deleted, somebody taken off the family list keeps everything they said, and every change
is a row like any other — but it is all reachable. Make the passwords long, and use the status page
to notice a month that does not look like yours.

**Checking it.**

```bash
curl -sI http://127.0.0.1:8080/            # 302 to /login, plus the security headers
curl -s http://127.0.0.1:8080/healthz      # ok
```

`familydb web --port 8099` serves the page alone in the foreground, which is the quickest way to
try settings without restarting the bot.

**Notes.** The login cookie is signed with a key generated once into `data/web_secret`. "Sign
everyone out" on the settings page replaces it, which ends every sign-in on every device. Set
`WEB_SECRET_KEY` instead if you run the page in more than one process, or everyone will be signed
out at random; the page cannot replace a key pinned there. The port must stay above 1024, because
the bot runs unprivileged in both Docker and systemd. The page opens its own database connection
per request, which is safe alongside the bot writing: SQLite is in WAL mode.

**Status.** `/status` answers "is it working?" without a log: which model answers chat and which
does the lookups, whether each key is set and whether it came from `.env` or the page, whether
Telegram is connected ("connected as @name", "the token was refused by Telegram" or "cannot
reach Telegram; trying again"), whether the calendar, the weather and the web lookups are
connected, what today has cost against the daily limit, what each purpose (answering the family,
the digest, lookups, ...) and each model has cost in dollars over the last thirty days, where the
input of each purpose went (instructions, tools, the idea list, history, the message; the real
total shared out by the size of each part), how much came back from the prompt cache, what is
waiting to be looked up, which messages did not go through, and the failures worth a look.
Every dollar figure is an estimate from a price table; one marked with an asterisk is for a model
the table does not list, and is counted high. It asks nothing of a model, so refreshing it is free.

## 11. Settings, and choosing OpenAI, Claude or Gemini

Every setting in this section can be changed in two places: in `.env`, which needs a restart, or
on the settings page at `/settings`, which does not. A value set on the page wins over the same
one in `.env`; empty a box on the page and `.env` applies again, which is what the greyed-out
value in an empty box is showing you. `familydb config` prints the lot and says where each one
came from. The page shows the API keys and Google Calendar first, then the rest in groups.

A change reaches the next message and the next page straight away, a new Telegram bot token
within a few seconds, and the timezone at once. The jobs that run on a schedule — the digest, the
follow-ups, the lookups, the retries — pick a new time or interval up within five minutes, and
the digest and follow-up hours keep the family's timezone as it is set on the page.

**Who answers.** Any of the three can, and the choice is made per surface, so the two halves of
the work can go to different places:

```
PROVIDER=openai            # openai, anthropic or gemini: who writes the replies the family reads
WORKER_PROVIDER=           # empty means the same; set it to send lookups elsewhere
PROVIDER_FALLBACK=true     # ask another one when the first cannot take a message
```

Give whichever keys you have. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` sit side
by side; the ones you did not choose become spares. Each vendor has its own pair of models, one
for chat and one for the mechanical lookups:

```
OPENAI_MODEL=gpt-6-luna
OPENAI_WORKER_MODEL=gpt-6-luna
ANTHROPIC_MODEL=claude-opus-5
WORKER_MODEL=claude-haiku-4-5-20251001
GEMINI_MODEL=gemini-2.5-pro
GEMINI_WORKER_MODEL=gemini-3.8-flash
```

The default is OpenAI's GPT-6 Luna for both chat and lookups, the cheapest capable model of the
three companies: $0.10 per million input tokens, $0.50 per million output tokens, and web search
at $10 per 1,000 searches, as published in September 2026. Claude and Gemini remain a setting
away. The model boxes on the page suggest the models it knows but take any name. When a model
name changes, the page asks that company's model list, which spends no tokens, and refuses the
save only on a definite "no such model"; if the company cannot be reached or has no key yet, the
save goes through. `/status` and `familydb debug cost` both print who is answering each surface
and on which model, which is the quickest way to see that a change took effect.

**Spending.** `DAILY_SPEND_LIMIT` ("Daily spending limit (US$)" on the page, under "What it may
spend") is $2.00 a day by default, counted over the family's day in its timezone; 0 turns it
off. It is checked before every model call, whether for chat, a lookup, discovery or the digest.
Once it is used up, chat says so ("I've reached today's spending limit ($2.00), so I'm stopping
here until tomorrow.") and lookups wait for tomorrow. A turn already under way stops before its next call, so a day can end over the limit
by at most one call. The figure is an estimate from a price table: a model the table does not
list is counted at $15 per million input and $75 per million output tokens, dearer than any it
does list, so the limit errs towards stopping. It is not the bill. Set a spending limit on the
API key in the provider's own console as well, because theirs is.

The other boxes in that group bound a single message: the longest answer (at most 64,000
tokens), tool rounds per message (at most 20) and per lookup (at most 30), and, under "Looking
things up", ideas looked up at a time (at most 20).

**Keys on the page.** The settings page is where keys are meant to be typed, and it has one
consequence worth knowing: a key stored there lives in `data/familydb.sqlite3`, so it is in
every backup you take (section 7) and in every copy of that file. A key in `.env` is not. Either
is fine on a machine you control; if the backups go somewhere you do not control, keep the keys
in `.env`. The page never shows a key back to you or writes one to its change log. "See a key"
shows one only after the password you signed in with is typed again, once, on that screen only.

**Personality.** `/settings/personality` holds who the bot is: the persona (Vera unless changed,
or none), her description rewritten in the family's words, "About the family" (what she should
know about them, sent with every message, so keep it short), and the lines she uses for
everything she says unasked, such as reminders and "how was it?". Those lines are filled in by
code, never by a model call; an emptied one goes back to hers. Her name is written as `{name}`,
in her description and in any line, and filled in wherever she speaks, the chat page included.

**Undoing a change.** The bottom of the settings page lists what has changed, when, and from
where. To put a setting back the way it was, empty its box: the value from `.env` applies again.

**A worthwhile combination.** Filling in an address and opening hours from a page is extraction,
not judgement, and it is most of the volume once lookups are on. If you move chat to another
provider for the way it writes, keep the lookups on the cheaper one:

```
PROVIDER=anthropic
WORKER_PROVIDER=openai
```

**What the fallback does and does not do.** A message the chosen provider cannot take, because it
is rate limited, unreachable or has no key, is asked of the other one. Only before any tool has
run: once the bot has saved an idea or put something on the calendar, starting again elsewhere
would do it twice, so a turn that fails after that stays failed and the retry job picks it up as
usual. A malformed request is not handed over either, since it would fail the same way twice.
Turn it off with `PROVIDER_FALLBACK=false`.

**What differs between them.** Claude's prompt cache is marked explicitly and lasts
`ANTHROPIC_CACHE_TTL`; OpenAI and Gemini cache long prefixes on their own, so that setting does
nothing there. Lookups and discovery work on all three. Conversations sent to OpenAI are sent
with storage off. `familydb debug validate-tools` and `familydb doctor --online` check the key
and the tools on Claude and Gemini, which can be asked to count tokens without generating
anything; OpenAI has no such endpoint, so there the first real message is the check.

## 12. Looking after the server

`scripts/maintain.sh` does most of what follows, and says what it is about to change before it
changes it: `status` (is it running, how big is the database, when was the last backup), `check`
(the full `familydb doctor` report), `backup`, `restore FILE`, `upgrade`, `logs`, `restart` and
`schedule-backups`. The rest of this section is what it does, and how to do it by hand.

Everything above gets the bot running. This is what a machine on the internet needs around it.

**Where things live.** One folder, `/opt/familydb` (or wherever you cloned it). `data/` is
readable by the bot's user alone, and so is everything in it:

| Path | What it is | In backups? |
|---|---|---|
| `data/familydb.sqlite3` | everything: messages, ideas, plans, places, the settings changed from the page, and any key stored there | yes, this is the backup |
| `data/google_token.json` | the calendar's OAuth token | no, connect again instead (section 5) |
| `data/web_secret` | signs the login cookie; "Sign everyone out" replaces it | no |
| `.env` | the page's password and address, and anything not set from the page | no, keep your own copy |
| `backups/` | the nightly backups, owner-only | they are the backups |
| `caddy/` | only with the Docker `tls` profile: the certificate and its private key | no, and keep it that way |

**A firewall.** The bot needs nothing inbound. With the web page behind Caddy or nginx, open 80
and 443 (or 80 and the page's own port, section 10) and nothing else:

```bash
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH           # do this before enabling, or you will lock yourself out
sudo ufw allow 80,443/tcp        # only with a domain; skip it otherwise
sudo ufw enable
```

Do not open 8080. The page listens on `127.0.0.1` so that the proxy, and only the proxy, can
reach it; the firewall is the second lock on the same door.

**Keeping the machine patched.** `sudo apt install unattended-upgrades` and answer yes. It is the
one piece of maintenance that matters more than anything in this file.

**Logs.** With systemd, journald keeps them and honours `SystemMaxUse` in
`/etc/systemd/journald.conf`; set it to something like `500M` on a small disk. With Docker the
compose file caps each container at five files of 10 MB. Nothing here writes a log file of its
own. The Telegram bot token is removed from every log line. `LOG_LEVEL=DEBUG` also logs every
HTTP request and is loud, so turn it back down when you are done.

**Disk.** The install is about 600 MB and the database grows by a few MB a year for a family.
Backups are the part that grows; the nightly schedule keeps `--keep-days` of them (fourteen by
default) and deletes the rest.

**When a secret gets out.**

- *An API key.* Revoke it in the vendor's console first, make a new one, then type it on the
  settings page, where it takes effect immediately, or put it in `.env` and restart. `/status`
  shows which key each provider is using and where it came from.
- *The Telegram bot token.* `/revoke` in BotFather makes a new one and kills the old; paste it on
  the settings page, where it takes effect within seconds, or put it in `.env` and restart.
  Nobody can read the family's messages with the old one afterwards.
- *Somebody's page password.* They change their own on Your password (at the top of every page):
  it asks for the one in force, keeps that browser signed in and signs every other one of theirs
  out, and will not take one under twelve characters. An admin can also make them a new starting
  password on the Family page, which signs them out everywhere at once, or take theirs away.
  Nothing on the server needs editing, and passwords are stored only as hashes. Once an admin has
  their own, the installer's `WEB_PASSWORD` opens nothing. If the only admin forgot theirs,
  `sudo /opt/familydb/scripts/maintain.sh password` prints a new starting password for them.
- *A lost phone, or a sign-in shared too widely.* A new starting password for that person (the
  Family page) signs them out on every device. "Sign everyone out" on the settings page, after
  typing your password again, ends every sign-in on every device, this one included. It cannot
  while `WEB_SECRET_KEY` is set in `.env`; change that and restart instead.
- *The whole server.* The database holds everything the family said. Rotate all of the above, and
  assume anything stored on the settings page was read.

**Stopping it for good.**

```bash
sudo systemctl disable --now familydb && sudo rm /etc/systemd/system/familydb.service
sudo systemctl daemon-reload
# or, with Docker:
docker compose down                 # add -v only if you mean to delete the volumes
```

Take a backup first if the ideas are worth keeping. The database is a plain SQLite file and any
SQLite browser opens it. `scripts/uninstall.sh` does this with a backup and asks first.

## 13. Troubleshooting

- **`cache_read` stays 0 in `db status`.** Something volatile is in the cached prefix. `familydb debug prompt "hi"` prints the request: the two `system` blocks and the `tools` list must be byte-identical between two runs. On Claude, check `ANTHROPIC_CACHE_TTL` is still `1h`, the default: at `5m` a family's gaps between messages are longer than the cache.
- **`database is locked`.** Two processes writing at once. Run one bot process; the CLI can be used alongside it (short transactions, busy timeout), but not a second `familydb run`.
- **"Got it, but I can't get to it right now."** (without a persona: "Saved your message, but I couldn't process it right now.") The model call failed. `journalctl` or `docker compose logs` has the error, and `/status` lists the message. The running bot retries the message every `RETRY_INTERVAL_MINUTES` up to `RETRY_MAX_ATTEMPTS` times and delivers the answer when it succeeds; `familydb db retry-failed` does it by hand, and `--reset` re-arms messages that gave up after a configuration problem you have since fixed.
- **"I've reached today's spending limit ($2.00)"** (or "Today's spending limit ($2.00) is used up" without a persona). The daily limit was reached; `/status` shows today's estimate against it. Nothing more is asked of a model until midnight in the family's timezone, lookups included. Raise it on the settings page ("Daily spending limit (US$)") if the day was genuine; if it was not, look at `/status` for what spent it.
- **"OpenAI says it has no model called X. Check the spelling."** On saving the settings page: the company's own model list has no model of that name, so nothing was saved. Correct the name or pick one of the suggestions. A company that cannot be reached, or has no key yet, never causes this.
- **"Could not find X on the map."** The home area could not be looked up. Type the latitude and longitude as well.
- **Telegram: "the token was refused by Telegram" on `/status`.** The token is wrong, or was revoked in BotFather. Paste the current one on the settings page. A refused token is not tried again until it changes, so nothing is hammering Telegram meanwhile.
- **Telegram: "cannot reach Telegram; trying again" on `/status`.** The server cannot get out to Telegram right now. It tries again every thirty seconds by itself; if it lasts, check the machine's network and DNS.
- **Google: the address will not load.** After allowing access, Google sends the browser to `http://127.0.0.1:53682/...` and it shows an error. That is expected: copy the whole address from the address bar into the page (section 5, step 6).
- **Google: "That address belongs to an earlier try."** The pasted address came from an older consent link. Press "Get the consent link" again and use the newest one. "That connection was started too long ago, or before a restart" means the same: start again. "That client is of type Web application" means the OAuth client must be made again as a Desktop app.
- **"Google credentials are expired or revoked."** Connect again from the settings page (Google Calendar), or run `familydb google auth` on a laptop and copy the new token over. If this happens weekly, the OAuth consent screen is still in Testing (section 5, step 2).
- **"no family members yet".** Add an admin with `familydb members add NAME --role admin`.
- **"a setting will not do" at startup.** A value in `.env` is not of the type the setting takes; the line names it. An empty line is fine and means "not set" — it is a value like `WEB_PORT=eighty` that stops it. Quote anything with a space or a `#` in it.
- **The service will not start under systemd.** `systemctl status familydb` says which. The three that bite: the `familydb` user does not exist or does not own `data/` and `.env`; a checkout inside a home directory, which that user cannot enter at all; and `ProtectHome=true` with a checkout under `/home`. Section 2b covers all three, and `/opt/familydb` avoids the last two.
- **"Sorry, I only talk to the family."** The sender is not on the family list for that channel; they are listed on the Family page under "Asked to talk to the bot", with a button to add them, and the reply includes their id.
- **A refusal.** Rare. `llm_calls.stop_reason` is `refusal`; on Claude, server-side fallbacks are on by default (`ANTHROPIC_FALLBACKS`), so it means every model declined.
- **Replies are coming from the wrong provider.** `/status` or `familydb debug cost` says who answers each surface. If it is not what you set, the other one is probably standing in because the chosen one has no key; the log says so at the time.
- **"validation failed" from `debug validate-tools`.** That check counts tokens, which Claude and Gemini offer and OpenAI does not. With `PROVIDER=openai`, send one real message instead, or point `PROVIDER` at another provider for the length of the check.
- **"details: failed" on an idea.** The lookup worker could not identify the place; `ideas list --json` shows the note. Fix the title or location with "actually it's the one in Vancouver", or on the idea's page, and run `familydb enrich --idea N`.
- **Suggestions say "web discovery off" or "hours unknown".** Lookups are off ("Look ideas up on the web" on the settings page), the idea has not been looked up yet, or the day's spending limit is used up; the enrichment job runs only in the long-running `familydb run` process.
- **The digest never arrives.** The Weekend digest row on `/status` and `familydb digest` show the schedule and the chat; the log says why a run was skipped (no chat, nothing to send with, no admin). For a Telegram group, the bot must be in the group and see its messages (section 4, step 3).
- **"the web page is not serving" in the log.** Either the settings forbid it (a page off the loopback, or behind a proxy, with no `WEB_PASSWORD` or one under twelve characters) or the port is taken. Behind Caddy it shows in the browser as a 502. The log line says which. The bot keeps running either way.
- **The web page asks for the password again and again.** The login cookie could not be stored or its signing key keeps changing. Check that `data/` is writable, or set `WEB_SECRET_KEY`. Over HTTPS, `WEB_TRUST_PROXY` must be true or the `Secure` cookie is never set. Changing a password (anybody's own, or `WEB_PASSWORD` while the family still shares it) or pressing "Sign everyone out" also ends the sessions opened with the old one, on purpose, so those people sign in once after that.
- **"Too many tries. Wait a quarter of an hour and try again."** Five wrong passwords from one address, or fifty from anywhere; a browser that has signed in before is spared the second. Waiting is the only way through, which is the point.
- **The web page is unreachable from another device.** `WEB_HOST` is probably still `127.0.0.1`, or the compose `ports` line still starts with `127.0.0.1:`. Both have to change, and a password has to be set. On a server on the internet, use a domain instead (section 10).
- **A setting in `.env` does nothing.** Something on the settings page is set for it, and that wins. `familydb config` marks every value with where it came from; empty that box on the page and `.env` applies again.
- **"stored settings are not usable" in the log.** A value in the database no longer validates, usually because an upgrade narrowed what a setting will take. The bot keeps running on what `.env` says and names the setting in the same line; fix or empty that box on the settings page.
- **A changed digest hour or lookup interval did not take effect.** Those move within five minutes of the change, not instantly; `journalctl` shows a "settings changed" line when they do. Anything that has not moved after that is worth reporting.
