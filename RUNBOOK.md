# Runbook: running FamilyDB on the home server

Two supported ways to run it: Docker Compose, or a Python virtualenv managed by systemd. Both use the same `.env` file and the same `data/` folder for the database and tokens. Pick one.

## Requirements

- Linux with either Docker (with the compose plugin) or Python 3.11+ and [uv](https://docs.astral.sh/uv/).
- Outbound HTTPS only. No ports need to be opened; no domain or reverse proxy.
- An Anthropic API key.

## 1. Get the code and the config

```bash
sudo mkdir -p /opt/familydb && sudo chown "$USER" /opt/familydb
git clone <this repo> /opt/familydb && cd /opt/familydb
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
sudo useradd --system --home /opt/familydb --shell /usr/sbin/nologin familydb
sudo chown -R familydb:familydb /opt/familydb/data /opt/familydb/.env
sudo cp deploy/familydb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now familydb
journalctl -u familydb -f
```

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

The database is one file. Nightly:

```
# crontab -e (as the user that owns data/)
15 3 * * * /opt/familydb/.venv/bin/familydb db backup /opt/familydb/backups/familydb-$(date +\%F).sqlite3
```

or with Docker: `docker compose exec bot familydb db backup /data/backups/familydb-$(date +%F).sqlite3`. The backup uses SQLite's online backup API and is safe while the bot runs. Keep a copy off the server. Calendar events are also in Google.

## 8. Upgrades

```bash
cd /opt/familydb && git pull
docker compose up -d --build               # Docker
# or
uv sync --frozen --no-dev && sudo systemctl restart familydb
```

Migrations run automatically on start. Never edit an applied migration; add a new numbered file.

## 9. Lookups, the weekend digest and follow-ups

**Looking ideas up.** Set `WEB_TOOLS_ENABLED=true` and restart. Every `ENRICH_INTERVAL_MINUTES` the bot takes up to `ENRICH_BATCH` new ideas and, in a separate small model call with web search, finds the place, its address, hours, booking link and price notes, geocodes it (OpenStreetMap's Nominatim, no key) and estimates the drive from `HOME_LAT`/`HOME_LON`. It then posts one line to the chat where the idea was captured ("Filled in #57 Hopscotch Portland: open Sat 10:00-20:00 · about 45 min away (estimate)"); set `ENRICHMENT_NOTES=false` to keep quiet. Ideas that are not one place ("a picnic somewhere") are skipped, and ideas the worker cannot identify are marked failed and left alone; `familydb enrich --idea 57` redoes one by hand, `familydb ideas list` shows the `details:` state, and `familydb tool describe_idea --json '{"id": 57}'` shows what was saved. Details older than `PLACE_STALE_DAYS` are refreshed the next time the idea comes up in a suggestion. With web tools off, nothing is looked up and suggestions say "hours unknown".

**Suggestions.** "What should we do this weekend?" runs the engine once: free time from the calendar, the forecast, every idea against the looked-up details, and, with web tools on, a search for time-bound things near `HOME_AREA` (cached for twelve hours per weekend). Each verdict is logged in `suggestions`. `familydb suggest --window this-weekend --discover` runs the same engine from the shell.

**Weekend digest.** Set `DIGEST_CHAT_ID` to the family group's Telegram chat id. Group ids are negative numbers; find it once someone has written in the group with `sqlite3 data/familydb.sqlite3 "select distinct chat_id from messages where channel = 'telegram'"` (or `docker compose exec bot sqlite3 /data/familydb.sqlite3 ...`), or ask the bot in the group and read the id from the log line. `DIGEST_DAY` and `DIGEST_HOUR` (default Thursday 18:00 in `FAMILYDB_TZ`) set the schedule; `familydb digest` prints it and `familydb digest --now` posts a digest immediately. The digest is asked as the first admin and stored like any message, so it goes out at most once a day; if the model call fails it is retried like a failed message, and if the bot was off at the scheduled hour it sends the digest a minute after it next starts on the same day.

**Follow-ups.** The morning after a plan (`FOLLOW_UP_HOUR`, default 10:00), the bot asks "How was #57 Hopscotch Portland on Saturday? Worth doing again?" in the chat the plan was made in, once per plan, unless someone already said how it went. The answer is recorded as feedback and feeds future suggestions. `familydb follow-ups --now` asks by hand.

**Cost.** Enrichment is at most three searches and three page reads per idea; discovery at most four searches per weekend per twelve hours. Both use the same model as chat.

## 10. Troubleshooting

- **`cache_read` stays 0 in `db status`.** Something volatile is in the cached prefix. `familydb debug prompt "hi"` prints the request: the two `system` blocks and the `tools` list must be byte-identical between two runs. Also, the cache expires after five minutes of quiet; set `ANTHROPIC_CACHE_TTL=1h` if usage is bursty.
- **`database is locked`.** Two processes writing at once. Run one bot process; the CLI can be used alongside it (short transactions, busy timeout), but not a second `familydb run`.
- **"Saved your message, but I couldn't process it right now."** The model call failed. `journalctl` or `docker compose logs` has the error. The running bot retries the message every `RETRY_INTERVAL_MINUTES` up to `RETRY_MAX_ATTEMPTS` times and delivers the answer when it succeeds; `familydb db retry-failed` does it by hand, and `--reset` re-arms messages that gave up after a configuration problem you have since fixed.
- **"Google credentials are expired or revoked."** Run `familydb google auth` again on a laptop and copy the new token over. If this happens weekly, the OAuth consent screen is still in Testing (section 5, step 2).
- **"no family members yet".** Add an admin with `familydb members add NAME --role admin`.
- **"Sorry, I only talk to the family."** The sender is not in `members` for that channel; the reply includes the id to add.
- **A refusal.** Rare. `llm_calls.stop_reason` is `refusal`; server-side fallbacks are on by default (`ANTHROPIC_FALLBACKS`), so it means every model declined.
- **"details: failed" on an idea.** The lookup worker could not identify the place; `ideas list --json` shows the note. Fix the title or location with "actually it's the one in Vancouver" and run `familydb enrich --idea N`.
- **Suggestions say "web discovery off" or "hours unknown".** Web tools are off (`WEB_TOOLS_ENABLED`), or the idea has not been looked up yet; the enrichment job runs only in the long-running `familydb run` process.
- **The digest never arrives.** `familydb digest` shows the schedule and chat; the log says why a run was skipped (no chat id, nothing to send with, no admin). The bot must be in the group and see its messages (section 4, step 3).
