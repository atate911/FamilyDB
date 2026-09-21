# Runbook: running FamilyDB on a home server or a VPS

Two supported ways to run it: Docker Compose, or a Python virtualenv managed by systemd. Both use the same `.env` file and the same `data/` folder for the database and tokens. Pick one.

## Requirements

- Linux with either Docker (with the compose plugin) or Python 3.11+ and [uv](https://docs.astral.sh/uv/).
- Outbound HTTPS only. The bot itself needs no inbound ports, no domain and no reverse proxy;
  the web page, if you turn it on, is the one thing that does (section 10).
- A key for one of the three providers: Anthropic, OpenAI or Gemini (section 11).

## 1. Get the code and the config

```bash
sudo mkdir -p /opt/familydb && sudo chown "$USER" /opt/familydb
git clone <this repo> /opt/familydb && cd /opt/familydb
scripts/install.sh
```

The installer asks a handful of questions, writes `.env`, installs the dependencies, creates the
database and adds you as the first family member. It picks Docker when it finds it and a
virtualenv otherwise, and it is safe to run again: it never overwrites `.env` without asking and
never touches the database. Sections 2a and 2b below are the same steps by hand.

Useful flags: `--mode docker|venv` to choose, `--config-only` to write `.env` and stop,
`--dry-run` to see what it would do, `--yes` to take every default, and `--non-interactive` to
read every answer from the environment. `scripts/install.sh --help` lists the variables it reads,
which is what you want for a scripted VPS build:

```bash
ANTHROPIC_API_KEY=sk-ant-... FAMILYDB_TZ=America/Vancouver HOME_AREA="Vancouver, WA" \
  ADMIN_NAME=Sam WEB_ENABLED=true scripts/install.sh --non-interactive --mode docker
```

Three things it deliberately leaves empty, because nobody can know them before the bot is
running: the Telegram chat id for the digest (section 9), the Google Calendar id and its token
(section 5), and your coordinates if it could not look your town up (section 6).

To set everything up by hand instead:

```bash
cp .env.example .env
nano .env        # ANTHROPIC_API_KEY, FAMILYDB_TZ, HOME_AREA at least
mkdir -p data
```

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

`FAMILYDB_PATH` and `GOOGLE_TOKEN_PATH` are set inside the container to `/data/...`; the compose file mounts `./data` there.

## 2b. Virtualenv and systemd

```bash
cd /opt/familydb
uv sync --frozen --no-dev            # creates .venv
.venv/bin/familydb db migrate
.venv/bin/familydb members add Sam --role admin
sudo useradd --system --home-dir /opt/familydb --shell /usr/sbin/nologin familydb
sudo chown -R familydb:familydb /opt/familydb/data /opt/familydb/.env
sudo cp deploy/familydb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now familydb
journalctl -u familydb -f
```

`scripts/install.sh` does all of this, the user included. Check `User=` and the paths in the unit
if you cloned somewhere other than `/opt/familydb`. A checkout under `/home` needs one change:
`ProtectHome=true` hides `/home` from the service, so the unit would start into an empty
directory. Use `ProtectHome=read-only` there, which the installer does for you.

The unit sets `FAMILYDB_PATH` and `GOOGLE_TOKEN_PATH` under `/opt/familydb/data` and locks the service down to that folder. To chat from the shell, run commands as the service user so the database stays owned by it: `sudo -u familydb /opt/familydb/.venv/bin/familydb repl`.

Without uv: `python3 -m venv .venv && .venv/bin/pip install .` gives the same `.venv/bin/familydb`.

## 3. First run checklist

1. `familydb config` shows the settings you expect (the key is masked).
2. `familydb db migrate` reports the schema version.
3. `familydb members add` for everyone who will message the bot (admin or member) and for kids (`--role kid`) so they can be named as participants.
4. `familydb chat "we should try that new ramen place on Main St sometime"` saves idea #1.
5. `familydb chat "tell me about #1"` answers from history.
6. `familydb db status` shows `cache_read` greater than zero on the second call. If it stays zero, see troubleshooting.
7. `familydb debug validate-tools` confirms the API accepts every tool schema.
8. `familydb tool --list` shows which integrations are available; the calendar and weather rows flip to `available` once sections 5 and 6 are done.
9. `familydb suggest --window this-weekend` prints what the engine would say about the ideas so far, with the checks it had to skip.
10. Optional: `WEB_PASSWORD=test familydb web --port 8099` and open the page in a browser (section 10).

## 4. Telegram

1. In Telegram, talk to BotFather: `/newbot`, pick a name and a username, copy the token into `TELEGRAM_BOT_TOKEN`, then start (or restart) the bot with `familydb run`.
2. Each family member sends the bot a direct message. The reply says "your id on this channel is 12345"; add them with `familydb members add NAME --channel telegram --channel-user-id 12345`. Their next message gets a real answer.
3. For a family group, send BotFather `/setprivacy` and choose Disable so the bot sees every message, then add the bot to the group. A dedicated "Ideas & Plans" group works best. In a busier group set `TELEGRAM_REQUIRE_MENTION=true` so it only answers when @mentioned or replied to.
4. Long polling means nothing is exposed; if the server is off, Telegram keeps updates for a day and the bot catches up on restart without double-processing.

## 5. Google Calendar

1. Create a Google Cloud project and enable the Google Calendar API.
2. Configure the OAuth consent screen as External and set the publishing status to **In production**. Left in Testing, refresh tokens expire after seven days and the bot stops writing to the calendar every week. The "unverified app" warning during consent is expected for a private app.
3. Create OAuth credentials of type Desktop app and download the JSON.
4. On a laptop with a browser (not inside Docker), run `uv run familydb google auth --client-secrets ~/Downloads/client_secret_XXX.json` and sign in as the account that owns the shared family calendar. It writes `data/google_token.json`.
5. Run `uv run familydb google calendars` to list the calendars and their ids, and put the family calendar's id in `GOOGLE_CALENDAR_ID`. A dedicated family Google account keeps the bot's token separate from anyone's personal mail.
6. Copy `google_token.json` into the server's `data/` folder (it must be readable by the bot's user), restart the bot, and check with `familydb google events`. From chat, "we're going to the symphony next Saturday at 8" now creates the event; "move that to Sunday" and "cancel the symphony" update it.

## 6. Weather

Set `HOME_LAT` and `HOME_LON` (and `WEATHER_UNITS=imperial` for Fahrenheit). Open-Meteo needs no API key. Check with `familydb tool get_forecast --json '{"start": "2026-09-26", "end": "2026-09-27"}'`.

## 7. Backups

The database is one file, and everything the family has said is in it. Nightly:

```
# crontab -e (as the user that owns data/, which is `familydb` after a systemd install:
#   sudo -u familydb crontab -e)
15 3 * * * FAMILYDB_PATH=/opt/familydb/data/familydb.sqlite3 /opt/familydb/.venv/bin/familydb db backup /opt/familydb/backups/familydb-$(date +\%F).sqlite3
```

`FAMILYDB_PATH` is set here because cron runs with no working directory to speak of, and the
default path in `.env` is relative to the checkout. Without it the backup would have nothing to
copy; it now says so and writes nothing rather than backing up an empty database.

With Docker: `docker compose exec bot familydb db backup /data/backups/familydb-$(date +%F).sqlite3`.
The backup uses SQLite's online backup API and is safe while the bot runs. Keep a copy off the
server: a backup on the same disk is not a backup. Calendar events are also in Google.

**Restoring one.** Stop the bot first, because the file it has open is the one being replaced:

```bash
sudo systemctl stop familydb                       # or: docker compose stop bot
sudo -u familydb cp backups/familydb-2026-09-14.sqlite3 data/familydb.sqlite3
sudo -u familydb rm -f data/familydb.sqlite3-wal data/familydb.sqlite3-shm
sudo systemctl start familydb                      # or: docker compose start bot
```

The write-ahead files belong to the database that was replaced, so they go too; SQLite makes new
ones. `familydb db status` afterwards shows the row counts and the schema version, and a restored
file from an older version is migrated on the next start.

An API key stored from the settings page lives in this file, so it is in every backup. That is
the price of being able to change a key from a phone. If these backups go anywhere you do not
control, keep the keys in `.env` instead (section 11) and the backup holds none.

## 8. Upgrades

```bash
cd /opt/familydb && git pull
docker compose up -d --build               # Docker
# or
uv sync --frozen --no-dev && sudo systemctl restart familydb
```

Migrations run automatically on start. Never edit an applied migration; add a new numbered file.
Check `systemctl status familydb` or `docker compose logs bot` once it is back: a setting that no
longer validates is named in one line rather than stopping silently.

Two upgrades ask something of you once:

- Everyone signs in to the page again the first time after upgrading past the change that ties a
  session to the password it was opened with. Nothing is wrong; it happens once.
- The `tls` profile now keeps Caddy's certificate in `caddy/` rather than `data/caddy`, so that a
  private key is not inside the bot's volume and its backups. Move the old folder across before
  starting, or let Caddy ask for a fresh certificate, which it will do on its own:
  `mv data/caddy caddy`. Delete any backup taken before this that might hold the old key.

## 9. Lookups, the weekend digest and follow-ups

**Looking ideas up.** Set `WEB_TOOLS_ENABLED=true` and restart. Every `ENRICH_INTERVAL_MINUTES` the bot takes up to `ENRICH_BATCH` new ideas and, in a separate small model call with web search, finds the place, its address, hours, booking link and price notes, geocodes it (OpenStreetMap's Nominatim, no key) and estimates the drive from `HOME_LAT`/`HOME_LON`. It then posts one line to the chat where the idea was captured ("Filled in #57 Hopscotch Portland: open Sat 10:00-20:00 · about 45 min away (estimate)"); set `ENRICHMENT_NOTES=false` to keep quiet. Ideas that are not one place ("a picnic somewhere") are skipped, and ideas the worker cannot identify are marked failed and left alone; `familydb enrich --idea 57` redoes one by hand, `familydb ideas list` shows the `details:` state, and `familydb tool describe_idea --json '{"id": 57}'` shows what was saved. Details older than `PLACE_STALE_DAYS` are refreshed the next time the idea comes up in a suggestion. With web tools off, nothing is looked up and suggestions say "hours unknown".

**Suggestions.** "What should we do this weekend?" runs the engine once: free time from the calendar, the forecast, every idea against the looked-up details, and, with web tools on, a search for time-bound things near `HOME_AREA` (cached for twelve hours per weekend). Each verdict is logged in `suggestions`. `familydb suggest --window this-weekend --discover` runs the same engine from the shell.

**Weekend digest.** Set `DIGEST_CHAT_ID` to the family group's Telegram chat id. Group ids are negative numbers; find it once someone has written in the group with `sqlite3 data/familydb.sqlite3 "select distinct chat_id from messages where channel = 'telegram'"` (or `docker compose exec bot sqlite3 /data/familydb.sqlite3 ...`), or ask the bot in the group and read the id from the log line. `DIGEST_DAY` and `DIGEST_HOUR` (default Thursday 18:00 in `FAMILYDB_TZ`) set the schedule; `familydb digest` prints it and `familydb digest --now` posts a digest immediately. The digest is asked as the first admin and stored like any message, so it goes out at most once a day; if the model call fails it is retried like a failed message, and if the bot was off at the scheduled hour it sends the digest a minute after it next starts on the same day.

**Follow-ups.** The morning after a plan (`FOLLOW_UP_HOUR`, default 10:00), the bot asks "How was #57 Hopscotch Portland on Saturday? Worth doing again?" in the chat the plan was made in, once per plan, unless someone already said how it went. The answer is recorded as feedback and feeds future suggestions. `familydb follow-ups --now` asks by hand.

**Cost.** Enrichment is at most three searches and three page reads per idea; discovery at most four searches per weekend per twelve hours. Both run on the smaller worker model (`WORKER_MODEL` and its OpenAI and Gemini counterparts), not on the one that writes the replies.

## 10. The web page

Five pages: the ideas list with search and filters, one idea in full with its hours, travel
estimate and booking link, the restaurants on their own page, what is on the calendar, and two
that are about the bot rather than the family — a status page and a settings page (section 11).
Ideas, plans and outcomes are never changed here; they are still added by messaging the bot.

**At home.** Put a password in `.env`, turn the page on, and restart:

```
WEB_ENABLED=true
WEB_HOST=0.0.0.0          # 127.0.0.1 keeps it on the server itself
WEB_PASSWORD=something-long-the-family-can-remember    # at least 12 characters
```

With Docker, uncomment nothing else: the compose file publishes the page to the server itself
(`127.0.0.1:8080`). To reach it from other devices on the network, change that line to
`"8080:8080"`. The page then answers at `http://<server>:8080/`. Everyone types the password once;
the login lasts `WEB_SESSION_DAYS` (30 by default). A page that faces the network needs at least twelve
characters, because that one password guards everything and there is no second factor.

If you would rather not put it on the network at all, leave `WEB_HOST=127.0.0.1` and reach it over
Tailscale or `ssh -L 8080:127.0.0.1:8080 you@server`. That is the safest option and needs no
password, though setting one anyway costs nothing.

**On a server on the internet.** Plain HTTP would send the password in the clear, so put Caddy in
front and let it get a certificate. Point a domain at the machine, then:

```
WEB_ENABLED=true
WEB_HOST=0.0.0.0
WEB_PASSWORD=a-long-random-password
WEB_TRUST_PROXY=true
WEB_DOMAIN=familydb.example.com
```

```bash
docker compose --profile tls up -d          # starts the bot and Caddy
```

Leave the bot's own port published to `127.0.0.1` only, so the internet reaches Caddy and nothing
else, and let the firewall through on 80 and 443 alone (`ufw allow 80,443/tcp`). `WEB_TRUST_PROXY`
makes the page read the real visitor address and the HTTPS scheme from Caddy's headers, and marks
the login cookie `Secure` so it never crosses plain HTTP. Only turn it on with a proxy actually in
front: it means trusting those headers. Caddy keeps the certificate and its private key in
`caddy/` beside the checkout, which is deliberately not inside `data/`: a key in there would be
readable from the bot's container and would land in every backup.

Running without Docker, put nginx or Caddy in front the same way and keep `WEB_HOST=127.0.0.1`.

**What protects it.** One shared password, checked in constant time. Five wrong guesses lock that
address out for fifteen minutes and are logged, and fifty failures from anywhere within a quarter
of an hour stop the page answering logins at all, so a guesser with many addresses gets nowhere.
Every page but the login and `/healthz` needs the cookie. Responses carry a content security
policy that forbids scripts and framing. Every form carries a token from the session as well, so a
link from another site cannot make a change on the family's behalf. Refusing to start is
deliberate: a page bound off the loopback with no password will not serve, and says so, unless you
set `WEB_ALLOW_NO_PASSWORD=true` on purpose.

Be clear-eyed about what signing in now buys someone: the ideas and plans are read-only, but the
settings page can change which model answers, read the API keys, and point the bot at a different
calendar. On a machine on the internet, that one password is what stands between a stranger and
your API bill. Make it long, and use the status page at the end of this section to notice a
month that does not look like yours.

**Checking it.**

```bash
curl -sI http://127.0.0.1:8080/            # 302 to /login, plus the security headers
curl -s http://127.0.0.1:8080/healthz      # ok
```

`familydb web --port 8099` serves the page alone in the foreground, which is the quickest way to
try settings without restarting the bot.

**Notes.** The login cookie is signed with a key generated once into `data/web_secret`; set
`WEB_SECRET_KEY` instead if you run the page in more than one process, or everyone will be signed
out at random. The port must stay above 1024, because the bot runs unprivileged in both Docker and
systemd. The page opens its own database connection per request, which is safe alongside the bot
writing: SQLite is in WAL mode.

**Status.** `/status` answers "is it working?" without a log: which model answers chat and which
does the lookups, whether each key is set and whether it came from `.env` or the page, whether
the calendar, the weather and the web lookups are connected, what the models have cost over the
last thirty days and how much of that came back from the prompt cache, what is waiting to be
looked up, which messages did not go through, and the failures worth a look. It asks nothing of a
model, so refreshing it is free.

## 11. Settings, and choosing Claude, OpenAI or Gemini

Every setting in this section can be changed in two places: in `.env`, which needs a restart, or
on the settings page at `/settings`, which does not. A value set on the page wins over the same
one in `.env`; empty a box on the page and `.env` applies again, which is what the greyed-out
value in an empty box is showing you. `familydb config` prints the lot and says where each one
came from.

A change reaches the next message and the next page straight away. The jobs that run on a
schedule — the digest, the follow-ups, the lookups, the retries — pick a new time or interval up
within five minutes. Nothing here needs `familydb run` restarted.

**Who answers.** Any of the three can, and the choice is made per surface, so the two halves of
the work can go to different places:

```
PROVIDER=anthropic         # anthropic, openai or gemini: who writes the replies the family reads
WORKER_PROVIDER=           # empty means the same; set it to send lookups elsewhere
PROVIDER_FALLBACK=true     # ask another one when the first cannot take a message
```

Give whichever keys you have. `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `GEMINI_API_KEY` sit side
by side; the ones you did not choose become spares, tried in that order. Each vendor has its own
pair of models, a larger one for chat and a smaller one for the mechanical lookups:

```
ANTHROPIC_MODEL=claude-opus-5
WORKER_MODEL=claude-haiku-4-5-20251001
OPENAI_MODEL=gpt-5
OPENAI_WORKER_MODEL=gpt-5-mini
GEMINI_MODEL=gemini-2.5-pro
GEMINI_WORKER_MODEL=gemini-2.5-flash
```

Check those names against your own account before relying on them; model names change and these
are only defaults. `/status` and `familydb debug cost` both print who is answering each surface
and on which model, which is the quickest way to see that a change took effect.

**Keys on the page.** The settings page can store an API key, which is convenient and has one
consequence worth knowing: a key stored there lives in `data/familydb.sqlite3`, so it is in every
backup you take (section 7) and in every copy of that file. A key in `.env` is not. Either is
fine on a machine you control; if the backups go somewhere you do not control, keep the keys in
`.env`. The page never shows a key back to you or writes one to its change log — seeing one means
typing the family password again, and it is shown once, on that screen only.

**Undoing a change.** The bottom of the settings page lists what has changed, when, and from
where. To put a setting back the way it was, empty its box: the value from `.env` applies again.

**A worthwhile combination.** Filling in an address and opening hours from a page is extraction,
not judgement, and it is most of the volume once lookups are on. Sending that to the cheaper
provider while chat stays wherever writes best is a real saving:

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
with storage off. `familydb debug validate-tools` works on Claude and Gemini, which can be asked
to count tokens without generating anything; OpenAI has no such endpoint, so there the first real
message is the check.

## 12. Looking after the server

Everything above gets the bot running. This is what a machine on the internet needs around it.

**Where things live.** One folder, `/opt/familydb` (or wherever you cloned it):

| Path | What it is | In backups? |
|---|---|---|
| `data/familydb.sqlite3` | everything: messages, ideas, plans, places, the settings changed from the page, and any key stored there | yes, this is the backup |
| `data/google_token.json` | the calendar's OAuth token | no, re-authorise instead (section 5) |
| `data/web_secret` | signs the login cookie; delete it to sign everyone out | no |
| `.env` | the secrets not set from the page | no, keep your own copy |
| `caddy/` | only with the `tls` profile: the certificate and its private key | no, and keep it that way |

**A firewall.** The bot needs nothing inbound. With the web page behind Caddy, open 80 and 443
and nothing else:

```bash
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH           # do this before enabling, or you will lock yourself out
sudo ufw allow 80,443/tcp        # only with the tls profile; skip it otherwise
sudo ufw enable
```

Do not open 8080. Compose publishes the page to `127.0.0.1` so that Caddy, and only Caddy, can
reach it; the firewall is the second lock on the same door.

**Keeping the machine patched.** `sudo apt install unattended-upgrades` and answer yes. It is the
one piece of maintenance that matters more than anything in this file.

**Logs.** With systemd, journald keeps them and honours `SystemMaxUse` in
`/etc/systemd/journald.conf`; set it to something like `500M` on a small disk. With Docker the
compose file caps each container at five files of 10 MB. Nothing here writes a log file of its
own. `LOG_LEVEL=DEBUG` also logs every HTTP request, and a Telegram request carries the bot token
in its URL, so turn it back down when you are done.

**Disk.** The install is about 600 MB and the database grows by a few MB a year for a family.
Backups are the part that grows; keep a fortnight and delete the rest:

```
30 3 * * * find /opt/familydb/backups -name 'familydb-*.sqlite3' -mtime +14 -delete
```

**When a secret gets out.**

- *An API key.* Revoke it in the vendor's console first, make a new one, then put the new one in
  `.env` and restart, or on the settings page, where it takes effect immediately. `/status` shows
  which key each provider is using and where it came from.
- *The Telegram bot token.* `/revoke` in BotFather makes a new one and kills the old; put it in
  `.env` and restart. Nobody can read the family's messages with the old one afterwards.
- *The page password.* Change `WEB_PASSWORD` in `.env` and restart. Every session opened with the
  old password ends at that point, so a stolen cookie stops working too. `WEB_PASSWORD` is
  deliberately not on the settings page: a form cannot change the lock on its own door.
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
SQLite browser opens it.

## 13. Troubleshooting

- **`cache_read` stays 0 in `db status`.** Something volatile is in the cached prefix. `familydb debug prompt "hi"` prints the request: the two `system` blocks and the `tools` list must be byte-identical between two runs. Check `ANTHROPIC_CACHE_TTL` is still `1h`, the default: at `5m` a family's gaps between messages are longer than the cache.
- **`database is locked`.** Two processes writing at once. Run one bot process; the CLI can be used alongside it (short transactions, busy timeout), but not a second `familydb run`.
- **"Saved your message, but I couldn't process it right now."** The model call failed. `journalctl` or `docker compose logs` has the error. The running bot retries the message every `RETRY_INTERVAL_MINUTES` up to `RETRY_MAX_ATTEMPTS` times and delivers the answer when it succeeds; `familydb db retry-failed` does it by hand, and `--reset` re-arms messages that gave up after a configuration problem you have since fixed.
- **"Google credentials are expired or revoked."** Run `familydb google auth` again on a laptop and copy the new token over. If this happens weekly, the OAuth consent screen is still in Testing (section 5, step 2).
- **"no family members yet".** Add an admin with `familydb members add NAME --role admin`.
- **"a setting will not do" at startup.** A value in `.env` is not of the type the setting takes; the line names it. An empty line is fine and means "not set" — it is a value like `WEB_PORT=eighty` that stops it. Quote anything with a space or a `#` in it.
- **The service will not start under systemd.** `systemctl status familydb` says which. The two that bite: the `familydb` user does not exist or does not own `data/` and `.env`, and a checkout under `/home` with `ProtectHome=true` (section 2b).
- **"Sorry, I only talk to the family."** The sender is not in `members` for that channel; the reply includes the id to add.
- **A refusal.** Rare. `llm_calls.stop_reason` is `refusal`; server-side fallbacks are on by default (`ANTHROPIC_FALLBACKS`), so it means every model declined.
- **Replies are coming from the wrong provider.** `familydb debug cost` says who answers each surface. If it is not what you set, the other one is probably standing in because the chosen one has no key; the log says so at the time.
- **"validation failed" from `debug validate-tools`.** That check counts tokens, which Claude and Gemini offer and OpenAI does not. With `PROVIDER=openai`, send one real message instead, or point `PROVIDER` at another provider for the length of the check.
- **"details: failed" on an idea.** The lookup worker could not identify the place; `ideas list --json` shows the note. Fix the title or location with "actually it's the one in Vancouver" and run `familydb enrich --idea N`.
- **Suggestions say "web discovery off" or "hours unknown".** Web tools are off (`WEB_TOOLS_ENABLED`), or the idea has not been looked up yet; the enrichment job runs only in the long-running `familydb run` process.
- **The digest never arrives.** `familydb digest` shows the schedule and chat; the log says why a run was skipped (no chat id, nothing to send with, no admin). The bot must be in the group and see its messages (section 4, step 3).
- **"the web page is not serving" in the log.** Either the settings forbid it (a page off the loopback with no `WEB_PASSWORD`) or the port is taken. The log line says which. The bot keeps running either way.
- **The web page asks for the password again and again.** The login cookie could not be stored or its signing key keeps changing. Check that `data/` is writable, or set `WEB_SECRET_KEY`. Over HTTPS, `WEB_TRUST_PROXY` must be true or the `Secure` cookie is never set. Changing `WEB_PASSWORD` also ends every session opened with the old one, on purpose, so everybody signs in once after that.
- **The web page is unreachable from another device.** `WEB_HOST` is probably still `127.0.0.1`, or the compose `ports` line still starts with `127.0.0.1:`. Both have to change, and a password has to be set.
- **A setting in `.env` does nothing.** Something on the settings page is set for it, and that wins. `familydb config` marks every value with where it came from; empty that box on the page and `.env` applies again.
- **"stored settings are not usable" in the log.** A value in the database no longer validates, usually because an upgrade narrowed what a setting will take. The bot keeps running on what `.env` says and names the setting in the same line; fix or empty that box on the settings page.
- **A changed digest hour or lookup interval did not take effect.** Those move within five minutes of the change, not instantly; `journalctl` shows a "settings changed" line when they do. Anything that has not moved after that is worth reporting.
