# FamilyDB

A private family assistant available in the browser and our chat app. It remembers the things we say we'd like to do, puts confirmed plans on the shared Google Calendar, and suggests what to do this weekend based on the calendar, the weather and the ideas we've collected.

**Status:** alpha build; live installation checks are still required. Capture, the Telegram channel, Google Calendar (plans created, moved and cancelled from chat, free time read live), the weather forecast and automatic retries are in, and so are the checked suggestions: a background lookup fills in each idea's place details (address, hours, booking, travel time), a staged engine checks every idea against the free time, the forecast and those details, web discovery finds what is on that weekend, a Thursday digest posts the weekend's options to the family chat, and the bot asks how a plan went the day after. It runs on Claude, OpenAI or Gemini, chosen per surface, with another as a spare when the first is busy. A responsive web app behind a shared family password provides a dashboard, idea and restaurant editing, calendar forms, month and agenda views, and a persistent AI conversation. Status and settings pages remain available; Telegram token changes require a restart. Next: richer data (Google Places, real routing, link previews). The design and roadmap are in [docs/DESIGN.md](docs/DESIGN.md); installing it on a home server or a VPS is in [RUNBOOK.md](RUNBOOK.md).

## How it works

- Someone messages the bot "we should try that ramen place sometime" or "idea for one day, the Hopscotch thing in Portland with the girls" and it is logged as an idea, tagged with what it can infer. A background lookup fills in the address, hours, tickets and travel time a couple of minutes later.
- "We're going to the symphony next Saturday" becomes an event on the family calendar, with the resolved date echoed back.
- "What should we do this weekend?" checks each stored idea against the free time, the forecast, opening hours, booking needs and travel time, searches the web for things happening that weekend, and returns a short list with the reasoning, plus an offer to schedule.
- The day after a plan, the bot asks how it went so it can suggest repeats or avoid duds.
- The web app lets the family save and edit ideas and restaurants, manage Google Calendar plans, and ask the AI directly. The dashboard brings recent ideas and upcoming plans together. See [docs/WEB_APP.md](docs/WEB_APP.md) for workflows, setup, and alpha limits.

One Python process does all of it. A chat adapter hands each message to a pipeline that saves it first, builds a prompt from the family context, the full ideas list and the recent conversation, and lets the model decide which tools to call. The tools are ordinary functions over a SQLite file, and every model call and tool call is logged.

## Quick start

**On a bare server, start at [docs/INSTALL.md](docs/INSTALL.md)**, which goes from a fresh VPS to
a running bot: preparing the machine, getting the code onto it (the repository is private, so
that is its own step), and then one command:

```bash
sudo bash scripts/bootstrap.sh
```

It says what it will change on the machine and why before it changes anything: the packages, the
`familydb` user it creates, the directory it writes to, and the systemd unit. Then it installs,
starts the service and checks the result. `scripts/install.sh` is the configuration half on its
own, for a machine that is already prepared.

Afterwards: `familydb doctor` says whether the install is right and what to do about anything
that is not, `scripts/maintain.sh` does backups, restores, upgrades and logs, and
`scripts/uninstall.sh` removes it, with or without the data.

On your own machine, to try it out:

```bash
uv sync
uv run familydb db migrate
uv run familydb members add Sam --role admin
uv run familydb members add "the girls" --role kid
uv run familydb tool add_idea --json '{"title": "Ramen place on Main St", "kind": "restaurant"}'
uv run familydb ideas list

export ANTHROPIC_API_KEY=...      # or OPENAI_API_KEY, or GEMINI_API_KEY, or put it in .env
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
| `familydb members list [--all]`, `familydb ideas list [--all] [--json]` | Inspect; the ideas lines are exactly what the model sees |
| `familydb tool NAME --json '{...}' [--stdin] [--as NAME]`, `--list`, `--schema` | Run any tool without the model |
| `familydb chat TEXT [--as NAME] [--fresh]` | One message, one reply |
| `familydb repl [--as NAME]` | Interactive chat (`/as NAME`, `/ideas`, `/quit`) |
| `familydb debug prompt TEXT [--as NAME] [--chat ID]` | The exact API request that would be sent, without sending it |
| `familydb debug cost [--days N]` | What each message pays for before anyone types, and what the last month actually used |
| `familydb debug validate-tools` | Have the API validate the tool schemas (needs an Anthropic or Gemini key) |
| `familydb google auth --client-secrets FILE` / `calendars` / `events [--days N]` | One-time Google sign-in; find the calendar id; connection test |
| `familydb enrich [--idea N] [--limit N]` | Look pending ideas up on the web now; `--idea` redoes one (needs `WEB_TOOLS_ENABLED=true`) |
| `familydb suggest [--window this-weekend\|next-weekend\|someday\|START..END] [--discover] [--json]` | Run the suggestion engine and print its verdicts; `--discover` also searches the web |
| `familydb digest [--now]` | Show the weekend digest schedule, or post it to the family chat now |
| `familydb follow-ups [--now]` | Ask how recent plans went, in the chat each plan was made in |
| `familydb web [--host H] [--port N]` | Serve the web page in the foreground |
| `familydb run` | The long-running service: migrates, starts the scheduler (retries, lookups, the digest, follow-ups) and the web page when it is enabled, then polls Telegram (or waits when no token is set) |
| `familydb config` | Resolved settings with secrets masked, saying where each one came from |
| `familydb doctor [--online] [--fix] [--json]` | Check the whole install and say what is wrong and how to fix it; `--fix` puts right what it safely can |

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
  web/            the page: app factory, password gate, the reading views, status, settings, templates
  integrations/   Google Calendar, Open-Meteo and the keyless geocoder
  jobs/           the scheduler; retries, enrichment, the weekend digest, follow-ups, catch-up
tests/            pytest suite with a scripted fake of the Anthropic API
scripts/          bootstrap (bare server to running bot), install, maintain, uninstall,
                  and lib/common.sh: the shared logging, error reporting and retries
deploy/           systemd unit; Dockerfile and docker-compose.yml at the root
docs/             DESIGN.md, and INSTALL.md for a server from zero
```

## Development

```bash
uv run pytest -q                                   # unit tests, no network
uv run ruff check . && uv run ruff format --check .
FAMILYDB_LIVE=1 uv run pytest -m live              # two real turns; checks prompt-cache hits
```
