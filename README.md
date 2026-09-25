# FamilyDB

A private family assistant, Vera, who lives in our chat app. She remembers the things we say we'd like to do and the things we have to do, puts confirmed plans on the shared Google Calendar, reminds us when we ask her to, and suggests what to do right now, tonight or this weekend, based on the calendar, the weather, where we are and the ideas we've collected.

**Status:** usable by the family. Capture, the Telegram channel, Google Calendar (plans created, moved and cancelled from chat, free time read live), the weather forecast and automatic retries are in, and so are the checked suggestions: a background lookup fills in each idea's place details (address, hours, booking, travel time), a staged engine checks every idea against the free time, the forecast and those details, web discovery finds what is on that weekend, a Thursday digest posts the weekend's options to the family chat, and the bot asks how a plan went the day after. Voice notes sent on Telegram are heard and answered like typed messages. Things to do and reminders are in too, and suggestions can be for right now, tonight or part of a day, measured from where the family is when a phone shares its location. It speaks as Vera, a personality the family can rewrite on the settings page along with a description of the family itself, and everything it says unasked (reminders, follow-ups, notices) goes through one voice layer in her words, folded into the conversation when the family is already talking. It runs on OpenAI's GPT-6 Luna by default, and on Claude or Gemini when chosen per surface, with another as a spare when the first is busy, and it stops asking any of them once the day's spending limit is used up. A web page, where each person signs in as themselves, does the lot in a browser: chat with the bot, browse and search the ideas list, the restaurants and the plans, add and change an idea, record how something went, put a plan on the calendar or cancel it, see what is connected and what the models have cost, and set the bot up — keys, models, Telegram, Google Calendar, where home is — without editing a file or restarting anything. Next: richer data (Google Places, real routing, link previews). An alpha review in September found and fixed a set of faults that only showed on a real install — lookups and discovery never ran on the default models, nobody could sign in to the page from a real browser, a restart could strand a message — and what still needs checking against live Google, Telegram and model accounts is listed in [docs/ALPHA_READINESS.md](docs/ALPHA_READINESS.md). The design and roadmap are in [docs/DESIGN.md](docs/DESIGN.md); installing it on a home server or a VPS is in [RUNBOOK.md](RUNBOOK.md).

## How it works

- Someone messages the bot "we should try that ramen place sometime" or "idea for one day, the Hopscotch thing in Portland with the girls" and it is logged as an idea, tagged with what it can infer. A background lookup fills in the address, hours, tickets and travel time a couple of minutes later.
- "We're going to the symphony next Saturday" becomes an event on the family calendar, with the resolved date echoed back.
- "Remind me on Tuesday that we need paper towels" becomes a task with a reminder; "one of these Saturday mornings I need to get my knives sharpened" becomes a task with no invented date.
- "I'm bored, what can we do right now?" and "anything for tonight?" are answered for that stretch of time, with when each option could actually start, and from where the family is when a phone has shared its location.
- "What should we do this weekend?" checks each stored idea against the free time, the forecast, opening hours, booking needs and travel time, searches the web for things happening that weekend, and returns a short list with the reasoning, plus an offer to schedule.
- The day after a plan, the bot asks how it went so it can suggest repeats or avoid duds.
- A web page does the same things in a browser, for anyone who would rather not open Telegram. It opens on what is coming up and what was added lately. Ask it something on the chat page and the answer arrives there, from the same pipeline and with the same checks. Search and filter the ideas, open one to see its hours, travel time and booking link, browse the restaurants, and see the family calendar as a list or a month, read live from Google so an event somebody added on their phone is there too. The Family page adds people and their Telegram ids, so nobody needs a terminal to let a new family member talk to the bot.
- Adding an idea, fixing its details, dropping it, recording how it went and putting a plan on the calendar all work from the page too. Each form runs the same tool the bot runs when you ask it in chat, so the duplicate check, the rating bounds and the calendar round-trip are the same code, not a second copy of it.
- What the page also changes is the bot itself — which model answers, how hard it thinks, what it may spend a day, where home is, when it speaks first, the API keys, the Telegram bot and the Google Calendar connection — on a settings page, with a status page saying what is connected, what is waiting and what today and the last month cost. Until everything is set, the home page lists what is left, each linked to where it is done.

One Python process does all of it. A chat adapter hands each message to a pipeline that saves it first, builds a prompt from the family context, the full ideas list and the recent conversation, and lets the model decide which tools to call. The tools are ordinary functions over a SQLite file, and every model call and tool call is logged.

## Quick start

**On a server, follow [docs/INSTALL.md](docs/INSTALL.md):** three steps, about twenty minutes,
and no Linux knowledge needed. Paste one block into the server's terminal; it walks you through
letting the server read this private repository, then installs everything, puts the page on
HTTPS at the server's address, and prints a link and a password. Open the link, and the page
walks you through the rest: yourself, your own password, an AI key, where home is, Telegram and
Google Calendar.

Afterwards: `familydb doctor` says whether the install is right and what to do about anything
that is not, `scripts/maintain.sh` does backups, restores, upgrades, logs and a forgotten
password, and `scripts/uninstall.sh` removes it (`--from-zero` puts the server back as it was
before FamilyDB, to try the install again).

On your own machine, to try it out:

```bash
uv sync
uv run familydb db migrate
uv run familydb members add Sam --role admin
uv run familydb members add "the girls" --role kid
uv run familydb tool add_idea --json '{"title": "Ramen place on Main St", "kind": "restaurant"}'
uv run familydb ideas list

export OPENAI_API_KEY=...         # or ANTHROPIC_API_KEY or GEMINI_API_KEY with PROVIDER set
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
| `familydb debug prompt TEXT [--as NAME] [--chat ID] [--kind KIND] [--idea N]` | The exact API request that would be sent (a chat message, or `--kind enrich --idea N` for a lookup), without sending it |
| `familydb debug cost [--days N]` | What each message pays for before anyone types, and what the last month cost per purpose (chat, digest, lookups, ...) and per model |
| `familydb debug validate-tools` | Have the API validate the tool schemas (needs an Anthropic or Gemini key) |
| `familydb google auth --client-secrets FILE` / `calendars` / `events [--days N]` | Google sign-in on a machine with a browser (the settings page does it without one); find the calendar id; connection test |
| `familydb enrich [--idea N] [--limit N]` | Look pending ideas up on the web now; `--idea` redoes one (needs `WEB_TOOLS_ENABLED=true`) |
| `familydb suggest [--window now\|today\|this-weekend\|next-weekend\|someday\|START..END] [--discover] [--json]` | Run the suggestion engine and print its verdicts; `--discover` also searches the web |
| `familydb digest [--now]` | Show the weekend digest schedule, or post it to the family chat now |
| `familydb follow-ups [--now]` | Ask how recent plans went, in the chat each plan was made in |
| `familydb web [--host H] [--port N]` | Serve the web page in the foreground |
| `familydb run` | The long-running service: migrates, starts the scheduler (retries, lookups, the digest, follow-ups, reminders), the web page when it is enabled, and Telegram whenever a token is set, taking up a new one without a restart |
| `familydb config` | Resolved settings with secrets masked, saying where each one came from |
| `familydb doctor [--online] [--fix] [--json]` | Check the whole install and say what is wrong and how to fix it; `--fix` puts right what it safely can |

## Layout

```
src/familydb/
  cli.py          commands            pipeline.py     one message end to end
  config.py       settings (.env)     app.py          wiring: settings, clock, db, client
  clock.py        time abstraction    dates.py        parsing in the family timezone
  delivery.py     message leases and at-least-once delivery of stored replies
  calendar_sync.py  plans brought in line with their Google events
  family.py       the rules for adding and changing family members (not a tool)
  task_service.py tasks and their reminders, changed in one place
  whereabouts.py  where a phone last said a member was, for a few hours
  voice.py        the words for everything said unasked, and folding it into a conversation
  personas/       who the assistant is: a name, a character and her lines, a folder each (default/)
  doctor.py       the install check   privacy.py      owner-only files and umask
  agent/          prompt builder, history, the tool loop, worker turns, the daily spending
                  limit, prompts/{system,enrich,discover}.md
  agent/providers/ one module per model vendor behind a small protocol, and the price table
  tools/          registry, strict schemas, one module per tool group (ideas, outcomes, calendar,
                  weather, places, suggest, tasks, now)
  suggest/        the suggestion engine: context, shortlist, evaluate, discover, compose, log
  store/          SQLite connection, migrations/, one repository per table
  channels/       message shapes, the console, Telegram (with the supervisor that follows its
                  token) and web channels
  web/            the page: app factory, password gate, home, chat, the reading views, the edit
                  forms, Family, the agenda read from Google, status, settings (with Google
                  connection and signing everyone out), once-only forms, templates
  integrations/   Google Calendar, Open-Meteo and the keyless geocoder
  jobs/           the scheduler; retries, enrichment, the weekend digest, follow-ups, reminders,
                  catch-up
tests/            pytest suite with scripted fakes of each provider's SDK, Google and the weather
evals/            the family's own requests run against a real model, graded by code
scripts/          bootstrap (bare server to running bot), install, maintain, uninstall,
                  and lib/common.sh: the shared logging, error reporting and retries
deploy/           systemd unit, a Caddyfile and an nginx site for HTTPS; Dockerfile and
                  docker-compose.yml at the root
docs/             DESIGN.md, INSTALL.md for a server from zero, ALPHA_READINESS.md (what the
                  September review found and what still needs a live check), MEMORY.md (the
                  household-memory design, not yet built), AI_CALLS.md (how model calls
                  are decided, fed and trusted: the framework, mostly not yet built)
```

## Development

```bash
uv run pytest -q                                   # unit tests, no network
uv run ruff check . && uv run ruff format --check .
FAMILYDB_LIVE=1 uv run pytest -m live              # two real turns; checks prompt-cache hits
uv run python -m evals --repeat 3                  # behaviour on a real model, a few cents
```
