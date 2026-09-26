# FamilyDB

A private family assistant, Vera, who lives in our chat app. She remembers the things we say we'd like to do and the things we have to do, puts confirmed plans on the shared Google Calendar, reminds us when we ask her to, and suggests what to do right now, tonight or this weekend, based on the calendar, the weather, where we are and the ideas we've collected.

**Status:** usable by the family, ahead of its first release. [CHANGELOG.md](CHANGELOG.md) says what v0.1.0 does and its known limits, [docs/DESIGN.md](docs/DESIGN.md) is the design and what comes next, [docs/INSTALL.md](docs/INSTALL.md) installs it on a server, and [RUNBOOK.md](RUNBOOK.md) runs it, including the checks still to make against live Google, Telegram and model accounts.

## How it works

- Someone messages the bot "we should try that ramen place sometime" or "idea for one day, the Hopscotch thing in Portland with the girls" and it is logged as an idea, tagged with what it can infer. A background lookup fills in the address, hours, tickets and travel time a couple of minutes later.
- "We're going to the symphony next Saturday" becomes an event on the family calendar, with the resolved date echoed back.
- "Remind me on Tuesday that we need paper towels" becomes a task with a reminder, and "remind me to put the bins out every Sunday at 7pm" one that comes round every week (or six months after each time it's done, for the dentist); a birthday's reminder comes every year with the gift ideas saved for them ("Grandma would love a gardening apron"); "one of these Saturday mornings I need to get my knives sharpened" becomes a task with no invented date, brought up on a Saturday morning when the calendar is free.
- "The girls are vegetarian now" or "no long drives until my back is better" is remembered, about the person it concerns, and weighed whenever it bears on a question. A page lists what she remembers and forgets anything for good.
- "I'm bored, what can we do right now?" and "anything for tonight?" are answered for that stretch of time, with when each option could actually start, and from where the family is when a phone has shared its location.
- "What should we do this weekend?" checks each stored idea against the free time, the forecast, opening hours, booking needs and travel time, searches the web for things happening that weekend, and returns a short list with the reasoning, plus an offer to schedule. On Thursday evenings the weekend's options are posted to the family chat unasked.
- The evening before a plan, the bot checks the forecast and the place's hours again, and speaks up only if something is off ("80% chance of rain for the falls hike"), with another idea for the same time.
- The day after a plan, the bot asks how it went so it can suggest repeats or avoid duds. On Telegram the question comes with buttons (Yes, again / Not again / Didn't go), and a reminder with ✓ Done, In an hour and Tomorrow: a tap does it at once, with no model call.
- Voice notes sent on Telegram are heard by a speech model and answered as if typed; the words are kept, the recording is not. /today, /week, /tasks and /now answer at once from the calendar, the task list and the ideas, with no model call.
- She speaks as Vera, a personality the family can rename, add to or rewrite on the settings page, or swap for a shorter Vera or for none at all. Everything said unasked (reminders, follow-ups, notices) is worded by code from her lines, and folded into the conversation when the family is already talking.
- A web page, where each person signs in as themselves, does the same things in a browser. It opens on the box to ask Vera something, with what is coming up, what is left to do and what was added lately around it. Search and filter the ideas, see on a radar where the places among them lie from home, open one to see its hours, travel time and booking link, browse the restaurants, and see the family calendar as a list or a month, read live from Google. Adding an idea, fixing its details, recording how it went, putting a plan on the calendar and ticking off a task all work from the page, and each form runs the same tool the bot runs when you ask it in chat, so the checks are the same code, not a second copy of it. Kept on a phone's home screen, the page opens full-screen as an app of its own.
- An admin also sets the bot up from the page: which company's model answers and how strong, what it may spend a day, where home is, when it speaks first, the API keys, the Telegram bot, the Google Calendar connection and who is in the family, with a status page saying what is connected and what the models have cost. Until everything is set, the home page lists what is left, each linked to where it is done.
- It runs on OpenAI's GPT-6 Luna by default, or on Claude or Gemini, chosen per surface: each company's cheapest model unless the family chooses a stronger one for the chat, the weekend digest or the lookups, with another company as a spare when the first is busy. Once the day's spending limit is used up, nothing more is asked of any model until midnight.

One Python process does all of it. A chat adapter hands each message to a pipeline that saves it first, builds a prompt from the family context, the ideas list and the recent conversation, and lets the model decide which tools to call. The tools are ordinary functions over a SQLite file, and every model call and tool call is logged.

## Quick start

**On a server, follow [docs/INSTALL.md](docs/INSTALL.md):** three steps, about twenty minutes,
and no Linux knowledge needed. Paste one block into the server's terminal; it walks you through
letting the server read this private repository, then installs everything, puts the page on
HTTPS at the server's address, and prints a link and a password. Open the link, and the page
walks you through the rest: yourself, your own password, an AI key, where home is, Telegram, the
rest of the family and Google Calendar.

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
| `familydb members add NAME [--role admin\|parent\|kid] [--channel C --channel-user-id ID]` | Add a person (a parent unless the role says otherwise); kids need no channel |
| `familydb members list [--all]`, `familydb ideas list [--all] [--json]` | Inspect; the ideas lines are exactly what the model sees |
| `familydb password [NAME]` | A new password for the web page, printed once: a starting password for the first admin, or for NAME; while the family still shares one password, a new shared one |
| `familydb tool NAME --json '{...}' [--stdin] [--as NAME]`, `--list`, `--schema` | Run any tool without the model |
| `familydb chat TEXT [--as NAME] [--fresh]` | One message, one reply |
| `familydb repl [--as NAME] [--fresh]` | Interactive chat (`/as NAME`, `/ideas`, `/quit`) |
| `familydb debug prompt TEXT [--as NAME] [--chat ID] [--kind KIND] [--idea N]` | The exact API request that would be sent (a chat message, or `--kind enrich --idea N` for a lookup), without sending it |
| `familydb debug cost [--days N]` | What each message pays for before anyone types, and what the last month cost per purpose (chat, digest, lookups, ...) and per model |
| `familydb debug validate-tools` | Have the API validate the tool schemas (needs an Anthropic or Gemini key) |
| `familydb google auth --client-secrets FILE` / `calendars` / `events [--days N]` | Google sign-in on a machine with a browser (the settings page does it without one); find the calendar id; connection test |
| `familydb enrich [--idea N] [--limit N]` | Look pending ideas up on the web now; `--idea` redoes one (needs `WEB_TOOLS_ENABLED=true`) |
| `familydb suggest [--window now\|today\|this-weekend\|next-weekend\|someday\|START..END] [--discover] [--json]` | Run the suggestion engine and print its verdicts; `--discover` also searches the web |
| `familydb digest [--now]` | Show the weekend digest schedule, or post it to the family chat now |
| `familydb follow-ups [--now]` | Ask how recent plans went, in the chat each plan was made in |
| `familydb web [--host H] [--port N]` | Serve the web page in the foreground |
| `familydb run` | The long-running service: migrates, starts the scheduler (retries, lookups, the digest, follow-ups, the evening-before check, reminders, nudges), the web page when it is enabled, and Telegram whenever a token is set, taking up a new one without a restart |
| `familydb config` | Resolved settings with secrets masked, saying where each one came from |
| `familydb doctor [--online] [--fix] [--json]` | Check the whole install and say what is wrong and how to fix it; `--fix` puts right what it safely can |

## Layout

```
src/familydb/
  cli.py          commands            pipeline.py     one message end to end
  config.py       settings (.env)     app.py          wiring: settings, clock, connections
  clock.py        time abstraction    dates.py        parsing in the family timezone
  delivery.py     message leases and at-least-once delivery of stored replies
  calendar_sync.py  plans brought in line with their Google events
  agenda.py       what is on, from Google or else the saved plans
  family.py       the rules for adding and changing family members (not a tool)
  roles.py        the three roles, admin, parent and kid, and what each may do
  task_service.py tasks, their reminders and repeats, changed in one place
  windows.py      a task's preferred window ("some Saturday morning"), read by code
  commands.py     Telegram's /today, /week, /tasks and /now, answered by code
  buttons.py      the buttons under a reminder or a follow-up, and what a tap does
  memory.py       which of the family's memories each message is sent
  whereabouts.py  where a phone last said a member was, for a few hours
  voice.py        the words for everything said unasked, and folding it into a conversation
  personas/       who the assistant is: a name, a character and her lines, a folder each
                  (default/, Vera as first written, and brief/, a shorter Vera)
  doctor.py       the install check   privacy.py      owner-only files and umask
  agent/          the gateway (the one door to a model), the request and prompt builders,
                  history, the tool loop, worker turns, the daily spending limit,
                  prompts/{system,enrich,discover}.md
  agent/providers/ one module per model vendor behind a small protocol, the price table and
                  each company's models by level
  tools/          registry, strict schemas, one module per tool group (ideas, outcomes,
                  calendar, weather, places, suggest, tasks, memory, now)
  suggest/        the suggestion engine: context, shortlist, evaluate, discover, compose, log
  store/          SQLite connection, migrations/, one repository per table
  channels/       message shapes, the console, Telegram (with the supervisor that follows its
                  token) and the web chat
  web/            the page: app factory, sign-in and roles, home, chat, the reading views, the
                  edit forms, Family, status, settings and setup, once-only forms, templates
  integrations/   Google Calendar, Open-Meteo and the keyless geocoder
  jobs/           the scheduler and its jobs: retries, lookups, the weekend digest, follow-ups,
                  the evening-before check, reminders, nudges, forgetting shared locations,
                  catch-up after a restart, and following settings changed on the page
tests/            pytest suite with scripted fakes of each provider's SDK, Google and the weather
evals/            the family's own requests run against a real model, graded by code
scripts/          bootstrap (bare server to running bot), install, maintain, uninstall; lib/ for
                  the shared logging, error reporting, retries and HTTPS; icons.py builds the
                  page's icon sprite
deploy/           systemd unit, a Caddyfile and an nginx site for HTTPS; Dockerfile and
                  docker-compose.yml at the root
docs/             DESIGN.md (the design and its decisions), INSTALL.md (a server from zero),
                  AI_CALLS.md (how each model call is decided, fed and trusted), MEMORY.md (what
                  the bot remembers of the family), PERSONAS.md (who the family talks to),
                  STYLE.md (how the page looks, and why), PRODUCT_EXAMPLES.md (the owner's own
                  scenarios)
```

## Development

```bash
uv run pytest -q                                   # unit tests, no network
uv run ruff check . && uv run ruff format --check .
FAMILYDB_LIVE=1 uv run pytest -m live              # two real turns; checks prompt-cache hits
uv run python -m evals --repeat 3                  # behaviour on a real model, a few cents
```
