# Changelog

## v0.1.0 — first alpha (2026-09-21)

The first version meant to be installed on a real machine and used by a family.
Everything below has been running against the tests and a scripted install; none
of it has yet been lived with for a month, which is what this alpha is for.

### What it does

- **Captures ideas from chat.** "We should try that ramen place sometime" becomes
  a stored idea, tagged with what the model can infer, through Telegram or the
  console.
- **Fills them in.** A background worker turn looks each new idea up on the web:
  address, opening hours, booking link, price notes, a geocoded travel estimate.
- **Keeps the calendar.** Confirmed plans are created, moved and cancelled on the
  shared Google Calendar from chat, and free time is read back live.
- **Answers "what should we do this weekend?"** A staged engine checks every idea
  against the free time, the forecast, the opening hours and the travel time,
  searches for what is on that weekend, and logs every verdict.
- **Speaks first.** A Thursday digest of the weekend's options, and a "how was
  it?" the morning after a plan.
- **Runs on Claude, OpenAI or Gemini,** chosen per surface, with another as a
  spare when the first is rate limited or down.
- **A web page** behind one shared family password: the ideas, the restaurants,
  the plans, a status page saying what is connected and what the month has cost,
  and a settings page that changes any setting or key without a restart.

### Installing it

Start at [docs/INSTALL.md](docs/INSTALL.md), which goes from a fresh VPS to a
running bot. On the server:

```bash
sudo bash scripts/bootstrap.sh
```

That is the only script that assumes nothing. It installs the system packages,
puts the code in `/opt/familydb`, creates the service account, hands over to
`scripts/install.sh` for the questions, starts the service and checks the
result. Before it touches anything it prints what it will change on the machine
and why, and what it will not touch, and asks.

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
nothing. It also refuses an install from a home directory, and builds the Docker
image, migrates inside the container, serves the page and stops it with a
signal.

What no test covers is a real conversation with a real model: that needs a key,
and it is what this alpha is for.

### Known limits

- The suggestion engine has been exercised against fixtures and by hand, not yet
  across a real season of weekends.
- Travel time is a straight-line estimate times a road factor, not real routing.
- Ideas and plans can only be changed by messaging the bot; the web page reads.
- One process at a time writes the database. Run one `familydb run`.
- The page's site-wide lockout, which stops distributed password guessing, also
  means a determined stranger can keep the family off the page for fifteen
  minutes at a time. On a public server, that is the trade being made.
- Upgrading on a private repository needs the credential the install used. With
  a deploy key the bootstrap wires it up; with a token there is nothing stored,
  and `maintain.sh upgrade` says so and what to do.
- There is no LICENSE file: all rights reserved by default.
