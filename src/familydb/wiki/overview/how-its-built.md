# How it is built

FamilyDB is one program, started with `familydb run`, that holds every part of the assistant at once: the web page, the Telegram connection, the timer that runs the jobs, and the code that talks to a model company. This page names those parts, says how they share the work, and says what you see of each when you run the server. [What it is and isn't](/wiki/overview/what-it-is) covers the product; [Layers and flow](/wiki/overview/layers-and-flow) follows a message through the code.

## One process, several threads

A **thread** is a line of work a program runs alongside others. The process starts these when it comes up:

| Part | Runs on | What it does |
|---|---|---|
| The timer (APScheduler) | Its own thread, handing each job to a pool of up to 10 worker threads | Runs the [jobs](/wiki/behavior/jobs): reminders, retries, lookups, the weekend digest and the rest. A job that is still running is not started a second time |
| The web page (waitress, serving Flask) | One thread named `familydb-web`, which hands each request to 4 worker threads | The page and the guide. Started only when `WEB_ENABLED` is true, which the installer sets |
| The Telegram connection | One thread named `familydb-telegram`, running an event loop | Fetches new messages from Telegram and sends replies. A *supervisor* watches the token setting and reconnects when it changes |
| The web chat | A new thread for each turn sent from the page, named `familydb-web-chat-<chat>` | Answers a message typed on the page, so the form post can come straight back |
| The main thread | The process itself | Waits for a stop signal and does nothing else |

The Telegram side waits on the network without blocking, but the rest of FamilyDB is ordinary synchronous code. Each Telegram handler therefore calls the core through `asyncio.to_thread`, which runs it on a worker thread and leaves the event loop free to keep fetching messages. A job that needs to send to Telegram hands the text to that loop through a thread-safe sender; the web chat needs none, because the page reads the stored message log. A message under way also holds a claim on itself, a [lease](/wiki/reference/glossary#lease), which a small extra thread renews every 30 seconds while the turn runs.

## One database, a connection per piece of work

Everything the family told it, every setting saved on the page and every record of a model call is in one SQLite file (`data/familydb.sqlite3` by default, set by `FAMILYDB_PATH`). SQLite is a database that lives in a single file inside the program's own process, so there is no database server to run.

A SQLite connection must not be shared between threads, so each piece of work opens its own, uses it and closes it: a page view, a job, a turn. Each connection uses write-ahead logging (which is why `-wal` and `-shm` files appear beside the database), waits up to five seconds for a lock, and writes inside transactions. That is what lets the page, the jobs and a one-off command such as `familydb chat` use the file at once. [State and database](/wiki/model/state-and-database) says what is in it.

## Starting and stopping

`familydb run` does these in order:

1. Reads `.env` and the environment. A setting that will not do stops the start with a sentence naming it.
2. Applies any pending **migrations**: numbered changes to the database's layout, each in its own transaction. One that fails stops the start and leaves the database as it was before that migration.
3. Tightens the permissions of the database, the Google key and the session key to owner-only.
4. Reads the settings saved on the page and logs one line saying which model answers chat.
5. Starts the timer, then the web page, then the Telegram supervisor.
6. Waits.

If the web page cannot start (a port in use, or a setting that forbids it), the process logs why and carries on without it.

A stop signal (SIGTERM from systemd or Docker, or Ctrl-C) is noted by a handler that is installed only once everything above has started. The main thread notices within a second, logs `received signal`, asks the Telegram connection to stop (waiting up to 30 seconds), closes the web server, tells the timer to shut down without waiting for running jobs, and logs `stopped`. The systemd unit allows 150 seconds before it kills the process, because a lookup in the middle of a model call can be slow to notice the stop. [The server](/wiki/operations/host) covers the unit.

## What is configured where

| Place | Holds | Changed by |
|---|---|---|
| The environment and `.env` | Where the data lives, the page's address and port, whether the page is on, the first password | Editing the file, then restarting |
| The database (the Settings page) | Nearly everything else: models, keys, limits, hours, the family's wording | The page, taking effect without a restart |
| The database (everything else) | Ideas, plans, things to do, messages, the log of model calls, memory | The assistant, the page's forms and the jobs |

What was saved on the page wins over `.env`, which wins over the built-in default. The running process re-reads the saved settings at each entry point (a message, a job, a page view), and the timer moves a changed schedule within five minutes. [The .env file](/wiki/operations/configuration) lists the keys only `.env` sets.

## What a restart loses

The timer keeps its schedule in memory, not in the database. About a minute after start, a *catch-up* job runs what a restart could have skipped: follow-ups, the evening check of tomorrow's plans, the weekend digest if today is its day and hour has passed, and the daily check of models and prices if a day has gone by. Each is safe to run twice.

Also gone after a restart:

- **A turn in progress.** Its message keeps its lease until it lapses (five minutes), then the retry job answers it.
- **Wrong-password counts.** The sign-in lockout is held in memory, so a restart clears it.
- **Two small caches.** Discovery results and the once-only tokens that stop a double click are kept in memory. Nothing stored is lost with them.

Messages, replies waiting to be sent, and settings are in the database and survive. [The server](/wiki/operations/host#updates-and-reboots) lists what comes back by itself.

## What you see of each part

| Part | On the Status page | In the log |
|---|---|---|
| Startup | No row of its own; the assistant's row says whether it can answer | `familydb <version> starting: ...`, `applied migrations [...]` |
| Timer | No row of its own; Waiting and Messages that did not go through show retries | `settings changed; <job> on`, `retrying N failed message(s)`, `catch-up on start: ...` |
| Web page | None: if you can read Status, the page is up | `serving the web page at ...`, or `the web page is not serving: ...` |
| Telegram | The Telegram row and Connected to | `telegram: polling as @<name>`, `telegram: Telegram refused the bot token ...`, `telegram: cannot reach Telegram ...` |
| Web chat | The "Writing back" pill | An error line only if the turn could not run at all |
| Model calls | Spending, Where the money went, and [Recent activity](/wiki/controls/status/activity) | Agent errors by message id |

The log is the journal under systemd and the container's log on Docker; [the server](/wiki/operations/host#logs) shows how to read it, and [Status](/wiki/controls/status) explains each row.

Developer docs: `src/familydb/cli.py` (`run`, `_wait_for_stop`), `app.py` (`App.refresh`, `connect`), `jobs/scheduler.py` (`build_scheduler`, `job_specs`), `channels/telegram.py` (`TelegramSupervisor`), `channels/web.py` (`WebChat`), `web/server.py` (`serve_in_thread`), `store/db.py` (`connect`, `migrate`), `delivery.py` (`lease`); `docs/DESIGN.md`, "Architecture" and "Deployment on a home server or a VPS".
