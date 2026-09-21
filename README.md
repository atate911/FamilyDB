# FamilyDB

A private family assistant that lives in our chat app. It remembers the things we say we'd like to do, puts confirmed plans on the shared Google Calendar, and suggests what to do this weekend based on the calendar, the weather and the ideas we've collected.

**Status:** usable by the family. Capture, the Telegram channel, Google Calendar (plans created, moved and cancelled from chat, free time read live), the weather forecast and automatic retries are in, and so are the checked suggestions: a background lookup fills in each idea's place details (address, hours, booking, travel time), a staged engine checks every idea against the free time, the forecast and those details, web discovery finds what is on that weekend, a Thursday digest posts the weekend's options to the family chat, and the bot asks how a plan went the day after. It runs on Claude or on OpenAI, per surface, with the other one as a spare when the first is busy. There is also a read-only web page for browsing the ideas list, the restaurants and the plans, with a shared family password. Next: richer data (Google Places, real routing, link previews). The design and roadmap are in [docs/DESIGN.md](docs/DESIGN.md); home-server setup is in [RUNBOOK.md](RUNBOOK.md).

## How it works

- Someone messages the bot "we should try that ramen place sometime" or "idea for one day, the Hopscotch thing in Portland with the girls" and it is logged as an idea, tagged with what it can infer. A background lookup fills in the address, hours, tickets and travel time a couple of minutes later.
- "We're going to the symphony next Saturday" becomes an event on the family calendar, with the resolved date echoed back.
- "What should we do this weekend?" checks each stored idea against the free time, the forecast, opening hours, booking needs and travel time, searches the web for things happening that weekend, and returns a short list with the reasoning, plus an offer to schedule.
- The day after a plan, the bot asks how it went so it can suggest repeats or avoid duds.
- A small web page shows the same list in a browser: search and filter the ideas, open one to see its hours, travel time and booking link, browse the restaurants, and see what is on the calendar. It only reads; everything is still changed by messaging the bot.

One Python process does all of it. A chat adapter hands each message to a pipeline that saves it first, builds a prompt from the family context, the full ideas list and the recent conversation, and lets Claude decide which tools to call. The tools are ordinary functions over a SQLite file, and every model call and tool call is logged.

## Quick start

On a server, `scripts/install.sh` does all of this and the rest of the setup: it asks a few
questions, writes `.env`, installs everything, creates the database and adds you as an admin.
`--help` lists the options, including a non-interactive mode for a scripted build. By hand:

```bash
uv sync
uv run familydb db migrate
uv run familydb members add Sam --role admin
uv run familydb members add "the girls" --role kid
uv run familydb tool add_idea --json '{"title": "Ramen place on Main St", "kind": "restaurant"}'
uv run familydb ideas list

export ANTHROPIC_API_KEY=...      # or put it in .env (see .env.example)
uv run familydb chat "we should try that new ramen place on Main St sometime"
uv run familydb chat "tell me about #1"
uv run familydb repl
uv run familydb db status         # row counts and the last model calls, with cache hits
```

## Commands

| Command | What it does |
|---|---|
| `familydb db migrate` / `status` / `backup DEST` / `retry-failed [--reset]` | Create or upgrade the schema; show counts and recent model calls; online backup; retry failed messages now |
| `familydb members add NAME --role admin\|member\|kid [--channel --channel-user-id]` | Add a person; kids need no channel |
| `familydb members list`, `familydb ideas list [--all] [--json]` | Inspect; the ideas lines are exactly what the model sees |
| `familydb tool NAME --json '{...}'`, `--list`, `--schema` | Run any tool without the model |
| `familydb chat TEXT [--as NAME] [--fresh]` | One message, one reply |
| `familydb repl [--as NAME]` | Interactive chat (`/as NAME`, `/ideas`, `/quit`) |
| `familydb debug prompt TEXT` | The exact API request that would be sent, without sending it |
| `familydb debug cost [--days N]` | What each message pays for before anyone types, and what the last month actually used |
| `familydb debug validate-tools` | Have the API validate the tool schemas (needs an Anthropic key) |
| `familydb google auth --client-secrets FILE` / `calendars` / `events` | One-time Google sign-in; find the calendar id; connection test |
| `familydb enrich [--idea N] [--limit N]` | Look pending ideas up on the web now; `--idea` redoes one (needs `WEB_TOOLS_ENABLED=true`) |
| `familydb suggest [--window this-weekend\|next-weekend\|someday\|START..END] [--discover] [--json]` | Run the suggestion engine and print its verdicts; `--discover` also searches the web |
| `familydb digest [--now]` | Show the weekend digest schedule, or post it to the family chat now |
| `familydb follow-ups [--now]` | Ask how recent plans went, in the chat each plan was made in |
| `familydb web [--host H] [--port N]` | Serve the read-only web page in the foreground |
| `familydb run` | The long-running service: migrates, starts the scheduler (retries, lookups, the digest, follow-ups) and the web page when it is enabled, then polls Telegram (or waits when no token is set) |
| `familydb config` | Resolved settings with secrets masked |

## Layout

```
src/familydb/
  cli.py          commands            pipeline.py     one message end to end
  config.py       settings (.env)     app.py          wiring: settings, clock, db, client
  clock.py        time abstraction    dates.py        parsing in the family timezone
  agent/          prompt builder, history, the tool loop, worker turns, prompts/{system,enrich,discover}.md
  agent/providers/ one module per model vendor behind a small protocol
  tools/          registry, strict schemas, one module per tool group (ideas, outcomes, calendar,
                  weather, places, suggest, now)
  suggest/        the suggestion engine: context, shortlist, evaluate, discover, compose, log
  store/          SQLite connection, migrations/, one repository per table
  channels/       message shapes, the console channel and the Telegram channel
  web/            the read-only page: app factory, password gate, views, templates, stylesheet
  integrations/   Google Calendar, Open-Meteo and the keyless geocoder
  jobs/           the scheduler; retries, enrichment, the weekend digest, follow-ups
tests/            pytest suite with a scripted fake of the Anthropic API
deploy/           systemd unit; Dockerfile and docker-compose.yml at the root
```

## Development

```bash
uv run pytest -q                                   # unit tests, no network
uv run ruff check . && uv run ruff format --check .
FAMILYDB_LIVE=1 uv run pytest -m live              # two real turns; checks prompt-cache hits
```
