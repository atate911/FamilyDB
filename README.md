# FamilyDB

A private family assistant that lives in our chat app. It remembers the things we say we'd like to do, puts confirmed plans on the shared Google Calendar, and suggests what to do this weekend based on the calendar, the weather and the ideas we've collected.

**Status:** usable by the family. The Telegram channel, the Google Calendar integration (plans created, moved and cancelled from chat, free time read live), the weather forecast and automatic retries are in, on top of the store, the tools, the model loop with prompt caching and the console chat. Next: looking up each idea's place details, checking hours and travel time, web discovery and the staged suggestion engine. The design and roadmap are in [docs/DESIGN.md](docs/DESIGN.md); home-server setup is in [RUNBOOK.md](RUNBOOK.md).

## How it works

- Someone messages the bot "we should try that ramen place sometime" or "idea for one day, the Hopscotch thing in Portland with the girls" and it is logged as an idea, tagged with what it can infer. A background lookup will later fill in the address, hours, tickets and travel time.
- "We're going to the symphony next Saturday" becomes an event on the family calendar, with the resolved date echoed back.
- "What should we do this weekend?" checks each stored idea against the free time, the forecast, opening hours, booking needs and travel time, searches the web for things happening that weekend, and returns a short list with the reasoning, plus an offer to schedule.
- The day after a plan, the bot asks how it went so it can suggest repeats or avoid duds.

One Python process does all of it. A chat adapter hands each message to a pipeline that saves it first, builds a prompt from the family context, the full ideas list and the recent conversation, and lets Claude decide which tools to call. The tools are ordinary functions over a SQLite file, and every model call and tool call is logged.

## Quick start

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
| `familydb debug validate-tools` | Have the API validate the tool schemas (needs a key) |
| `familydb google auth --client-secrets FILE` / `calendars` / `events` | One-time Google sign-in; find the calendar id; connection test |
| `familydb run` | The long-running service: migrates, starts the retry scheduler, then polls Telegram (or waits when no token is set) |
| `familydb config` | Resolved settings with secrets masked |

## Layout

```
src/familydb/
  cli.py          commands            pipeline.py     one message end to end
  config.py       settings (.env)     app.py          wiring: settings, clock, db, client
  clock.py        time abstraction    dates.py        parsing in the family timezone
  agent/          prompt builder, history, the tool loop, prompts/system.md
  tools/          registry, strict schemas, ideas/outcomes/now tools, calendar/weather/place stubs
  store/          SQLite connection, migrations/, one repository per table
  channels/       message shapes, the console channel and the Telegram channel
  integrations/   Google Calendar and Open-Meteo clients
  jobs/           the scheduler and the retry job
tests/            pytest suite with a scripted fake of the Anthropic API
deploy/           systemd unit; Dockerfile and docker-compose.yml at the root
```

## Development

```bash
uv run pytest -q                                   # unit tests, no network
uv run ruff check . && uv run ruff format --check .
FAMILYDB_LIVE=1 uv run pytest -m live              # two real turns; checks prompt-cache hits
```
