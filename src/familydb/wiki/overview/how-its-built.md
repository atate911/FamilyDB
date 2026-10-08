# How it is built

FamilyDB is one program on one machine with one database file. A restart is safe because nothing a message needs lives only in memory. [What it is and is not](/wiki/overview/what-it-is) covers the product, and [From message to reply](/wiki/behavior/message-to-reply) follows one message through the parts named here.

## The layers

```
 Telegram   Web chat   Console                 Timer          Browser
     \         |         /                       |                |
      v        v        v                        v                v
 +-------- channels --------+                   jobs         the web page
 | take messages in and out |              (reminders,     (its chat box is
 +------------+-------------+              lookups, ...)    a channel above)
               v                                |                |
          pipeline <--- weekend ideas, retries -+                |
 (dedupe, family check, store,                  |                |
  lease, build the turn, reply)                 |                |
               v                                |                |
          gateway  <--- lookups ----------------+                |
               v                                |                |
          agent loop --> model company          |                |
               v                                |                |
          tools (registry, context) <-----------+-- edit forms --+
               v                                                 |
          engines --> Google Calendar, weather, geocoder         |
               v                                                 |
          store (SQLite) <---------------------------- reads ----+
```

A **channel** is an adapter for one way of talking: Telegram, the page's chat, or the console (`familydb chat`). The **pipeline** handles one inbound message from arrival to stored reply. The **gateway** is the one door to a model company, and the **agent loop** runs a [turn](/wiki/reference/glossary#turn): ask the model, run the tools it names, ask again. **Tools** are small checked functions the model may call, and **engines** are the code behind them that weighs an idea against the calendar, forecast and opening hours. The **store** is the database.

Two things sit alongside. The **web page** reads the store; its edits go through tools, its chat box goes through the pipeline, and family and settings changes have their own door. The **jobs** run on the timer, mostly without a model call. The weekend ideas job and the retry job go through the pipeline, and lookups go through the gateway as separate [worker turns](/wiki/reference/glossary#worker-turn).

## The rules every layer follows

- A message is stored before the assistant works on it, and a reply is stored before it is sent, so a crash loses nothing. The price is that a reply can arrive twice.
- Every model call goes through the [gateway](/wiki/reference/glossary#gateway), so the daily limit is always checked and every call is recorded.
- A change made on the page is a tool call, the same kind the assistant makes, so the page can do nothing the assistant cannot. Changes to the family list and the settings are not tools, so the model can never change who may message it or sign in.
- A page view makes no model call. Only a sent message does.

[Trust and threat model](/wiki/security/model) says what each rule protects.

## One process, several threads

A **thread** is a line of work a program runs alongside others. `familydb run` starts these:

| Part | Runs on | What it does |
|---|---|---|
| The timer (APScheduler) | Its own thread, handing each job to a pool of up to 10 worker threads | Runs the [jobs](/wiki/behavior/jobs). A job still running is not started a second time |
| The web page (waitress, serving Flask) | One thread named `familydb-web`, which hands each request to 4 worker threads | The page and the guide. Runs only when `WEB_ENABLED` is true, which the installer sets |
| The Telegram connection | One thread named `familydb-telegram`, running an event loop | Fetches new messages from Telegram and sends replies. A *supervisor* watches the token setting and reconnects when it changes |
| The web chat | A new thread for each message sent from the page, named `familydb-web-chat-<chat>` | Answers a message typed on the page, so the form post comes straight back |
| The main thread | The process itself | Waits for a stop signal and does nothing else |

Telegram messages are fetched on one thread that never waits on anything slow, and each message is handed to another thread to be answered, so a long answer does not hold up the next one. A job that sends to Telegram hands its text to the Telegram thread. The web chat needs no hand-off, because the page reads the stored message log.

While a message is being answered, FamilyDB keeps a [lease](/wiki/reference/glossary#lease) on it: a claim that runs out if the program stops, so nothing is answered twice. A small extra thread renews the lease every 30 seconds. If the program stops, the lease runs out after 5 minutes and the retry job picks the message up.

## One database, a connection per piece of work

Everything the family told FamilyDB, every setting saved on the page and every record of a model call is in one database file ([SQLite](/wiki/reference/glossary#sqlite), `data/familydb.sqlite3` by default, set by `FAMILYDB_PATH`). SQLite runs inside the program, so there is no database server.

Each piece of work (a page view, a job, a turn) opens its own connection and closes it, and waits up to 5 seconds for a lock. That lets the page, the jobs and a one-off command such as `familydb chat` use the file at once, and it is why `-wal` and `-shm` files appear beside the database. [State and the database](/wiki/model/state-and-database) says what is in it.

## Starting and stopping

`familydb run` reads `.env`, applies any pending [migrations](/wiki/reference/glossary#migration) (numbered changes to the database layout; one that fails stops the start and leaves the database as it was), makes the database, the Google key and the session key owner-only, then starts the timer, the web page and the Telegram supervisor. A setting that will not do stops the start with a sentence naming it. If only the web page cannot start, the process logs why (`could not serve the web page on <address>` for a port in use) and carries on without it.

A stop signal (SIGTERM from systemd or Docker, or Ctrl-C) stops the Telegram connection (waiting up to 30 seconds), closes the web server and shuts the timer down without waiting for running jobs. The systemd service allows 150 seconds before it kills the process. The compose file sets no stop time, so Docker's default of 10 seconds applies.

## What is configured where

`.env` holds where the data lives, the page's address and port, whether the page is on, and the shared password; you change it by editing the file and restarting. Nearly everything else (models, keys, limits, hours, the family's wording) is saved in the database from the Settings page. What was saved on the page wins over `.env`, which wins over the built-in default. [How a setting gets its value](/wiki/controls/settings#how-a-setting-gets-its-value) says when a change applies, and [The .env file](/wiki/operations/configuration) lists the keys only `.env` sets.

## What a restart loses

The timer keeps its schedule in memory, so about 60 seconds after a start a catch-up run does what the restart could have skipped ([After a restart](/wiki/behavior/jobs#after-a-restart)). A message in the middle of a turn is recovered by its lease and the retry job ([What survives a restart](/wiki/behavior/message-to-reply#what-survives-a-restart)). The sign-in lockout counts are kept in memory, so a restart clears them. Messages, replies waiting to be sent and settings are in the database and survive.

## What you see of each part

[Status](/wiki/controls/status) has a row for the assistant and one for Telegram; if you can read Status, the web page is up. A healthy start logs `familydb <version> starting`, `serving the web page at ...` and `telegram: polling as @<name>`; [Logs](/wiki/operations/diagnostics#logs) says how to read the log.

Developer docs: src/familydb/cli.py, src/familydb/app.py, src/familydb/jobs/scheduler.py, src/familydb/channels/telegram.py, src/familydb/channels/web.py, src/familydb/web/server.py, src/familydb/store/db.py, src/familydb/delivery.py; docs/DESIGN.md, "Architecture" and "Deployment on a home server or a VPS"; docs/AI_CALLS.md, "The one idea".
