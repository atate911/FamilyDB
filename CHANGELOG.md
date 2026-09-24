# Changelog

## v0.1.0 — in progress

The first version meant to be installed on a real machine and used by a family.
Everything below has been running against the tests and a scripted install; none
of it has yet been lived with for a month, which is what this alpha is for.

Still being built. While this heading says "in progress", an install follows the
default branch rather than a release tag, and an upgrade never moves to anything
older than what is installed. It gets a date when it is released.

### What it does

- **Captures ideas from chat.** "We should try that ramen place sometime" becomes
  a stored idea, tagged with what the model can infer, through Telegram, the web
  page's chat or the console.
- **Fills them in.** A background worker turn looks each new idea up on the web:
  address, opening hours, booking link, price notes, a geocoded travel estimate.
- **Keeps the calendar.** Confirmed plans are created, moved and cancelled on the
  shared Google Calendar from chat, and free time is read back live.
- **Keeps the things to do.** "Remind me on Tuesday that we need paper towels"
  is a task with a reminder, sent in the chat it was asked in; "one of these
  Saturday mornings" is a task with no invented date. A page lists them, and
  a reminder sent late after the bot was off says when it was due.
- **Answers "what should we do?" for the time asked about:** right now, tonight,
  Saturday morning or this weekend. A staged engine checks every idea against
  the free time in minutes, the forecast, the opening hours and the travel
  time, says when each option could actually start, searches for what is on,
  and logs every verdict.
- **Knows where the family is when a phone says so.** A location shared on
  Telegram, or the position the web page's chat sends with a message (only
  while "Send where I am" is ticked), is used for three hours: travel is measured from there
  and discovery searches near it.
- **Speaks as Vera.** A personality, and a description of the family, both
  editable on the settings page. Everything said unasked (reminders, "how was
  it?", notices) is written in her words by code, and is carried by her reply
  instead when the family is already talking to her.
- **Speaks first.** A Thursday digest of the weekend's options, and a "how was
  it?" the morning after a plan.
- **Runs on OpenAI's GPT-6 Luna by default,** the cheapest capable model of the
  three companies, for chat and lookups alike. Claude and Gemini can be chosen
  per surface on the settings page, with another as a spare when the first is
  rate limited or down, and a mistyped model name is refused when it is saved.
- **Stops at a daily spending limit.** Every model call records an estimated
  cost; once the day's limit ($2 unless changed) is used up, nothing more is
  asked of a model until midnight, and the chat says why.
- **The whole bot in a browser,** behind one shared family password: a home page
  saying what is coming up and what is left to set up, the chat, the ideas and
  restaurants, the plans as a list or a month read live from Google, forms that
  add and change ideas, record how things went and put plans on the calendar
  (through the same tools the bot uses), the Family page, a status page with
  what is connected and what it has cost, and a settings page.
- **A look of its own.** A modern dark page with an old green screen in its heart:
  pixel headlines that glow like phosphor, a colour for each part of the site and
  each kind of idea, pixel icons and pictures, a tab bar under the thumb on a
  phone, plans as tear-off dates, and a month that prints as green-bar paper.
  `docs/STYLE.md` says what each choice is for.
- **Set up from that page.** The keys, the models, Telegram (taken up within
  seconds, no restart), Google Calendar (connected from the page, with no laptop
  needed), where home is (found on the map), the timezone and the spending
  limit. The page can also sign everyone out on every device. Somebody new who
  messages the bot on Telegram is listed on the Family page with a button to
  add them, and the digest chat is chosen from the chats the bot has seen, so
  nobody copies an id by hand.

### Installing it

Start at [docs/INSTALL.md](docs/INSTALL.md), which goes from a fresh VPS to a
running bot. On the server:

```bash
sudo bash scripts/bootstrap.sh
```

That is the only script that assumes nothing. It installs the system packages,
puts the code in `/opt/familydb`, creates the service account, hands over to
`scripts/install.sh`, starts the service and checks the result. Before it
touches anything it prints what it will change on the machine and why, and what
it will not touch, and asks.

The installer asks one thing: the domain name the page will be reached at, if
any. With a domain it puts the page behind HTTPS (Caddy, in Docker or on the
machine), which is also what lets a phone's browser share its location. It
keeps the data folder readable by the bot alone and schedules a nightly backup.
Everything else is set on the page, whose home lists what is left to do,
starting with adding yourself on the Family page.

Getting the code onto a bare server is a step of its own, because the
repository is private: a deploy key, a token in the environment, or a copy you
put there yourself. All three are in the install guide.

Clone into `/opt/familydb` and not a home directory. A home directory is closed
to other users, so a service running as its own account cannot start from one.
The installer checks this and refuses rather than leaving a unit that will
never start.

### Looking after it

- `familydb doctor` checks the whole install and says what is wrong and what to
  do about it. `--online` also tests the keys against the APIs, `--json` is for
  scripts, and `--fix` puts right the few things that can be put right without a
  decision.
- `scripts/maintain.sh` does status, check, backup, restore, upgrade, logs,
  restart and nightly backups. A restore backs up the database it is about to
  replace, so it can itself be undone.
- `scripts/uninstall.sh` removes the service and the installed files but keeps
  `.env`, `data/` and the backups, which is what a reinstall wants. `--purge`
  removes those too, after taking a backup and asking you to type a
  confirmation.

Every one of these explains a failure rather than printing one: which step, the
command, its exit code, what it said, what that usually means, and what to try.
`RUNBOOK.md` covers running it day to day; `docs/INSTALL.md` has a section on
each failure.

### What has been checked

Every push runs the test suite on Python 3.11 and 3.12, lints and shellchecks
every script, and then, on a real machine: a bootstrap install into `/opt`, the
bot running as the service account it created, `doctor` and its `--fix`, a
backup, a restore over the database, an uninstall that keeps the data followed
by a reinstall that picks it back up, and a purge that backs up first and leaves
nothing. It also starts the service under its systemd sandboxing and fetches
the page, refuses an install from a home directory, and builds the Docker image,
migrates inside the container, serves the page and stops it with a signal.

Signing in through Caddy and through nginx over HTTPS was checked in a real
browser: an earlier build could not sign anyone in behind a proxy, because the
web server discarded the proxy's headers before the page saw them.

What no test covers is a real conversation with a real model, a real Telegram
bot or a real Google account: those need keys, and they are what this alpha is
for. `uv run python -m evals` runs the family's own requests against a real
model and grades what it did, for a few cents; it has not yet been run. Connecting Google from the page in particular is new and has not yet been
tried against Google itself; `familydb google auth` on a laptop is the fallback.

### Known limits

- The suggestion engine has been exercised against fixtures and by hand, not yet
  across a real season of weekends.
- Travel time is a straight-line estimate times a road factor, not real routing,
  and the forecast is per day, not per hour.
- The location a phone shares is named with OpenStreetMap's free reverse lookup,
  which has not yet been reached from a real install.
- One process at a time writes the database. Run one `familydb run`.
- The daily spending limit is an estimate from a price table, not the bill. Set a
  limit on the API key with the company as well.
- The page's site-wide lockout stops distributed password guessing. A browser
  that has signed in before is spared it; a new phone may have to wait fifteen
  minutes while someone is guessing.
- Household memory is designed (`docs/MEMORY.md`) but not built.
- Upgrading on a private repository needs the credential the install used. With
  a deploy key the bootstrap wires it up; with a token there is nothing stored,
  and `maintain.sh upgrade` says so and what to do.
- There is no LICENSE file: all rights reserved by default.
