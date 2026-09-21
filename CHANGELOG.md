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

`scripts/install.sh` asks a handful of questions, writes `.env`, installs for
Docker or a virtualenv, migrates, adds the first family member, creates the
service user and installs the systemd unit. Clone into `/opt/familydb`: a home
directory is closed to other users, so a service running as its own user cannot
start from one, and the installer will tell you so rather than leave a unit that
never starts. `RUNBOOK.md` covers a VPS end to end: firewall, backups and
restores, upgrades, rotating a leaked key, and what to do when something is
wrong.

### What has been checked

Every push runs the test suite on Python 3.11 and 3.12, lints, shellchecks the
installer, installs from an untouched checkout and runs the bot as the service
user it created, and builds the Docker image, migrates inside the container,
serves the page and stops it with a signal. What no test covers is a real
conversation with a real model: that needs a key, and it is what this alpha is
for.

### Known limits

- The suggestion engine has been exercised against fixtures and by hand, not yet
  across a real season of weekends.
- Travel time is a straight-line estimate times a road factor, not real routing.
- Ideas and plans can only be changed by messaging the bot; the web page reads.
- One process at a time writes the database. Run one `familydb run`.
- The page's site-wide lockout, which stops distributed password guessing, also
  means a determined stranger can keep the family off the page for fifteen
  minutes at a time. On a public server, that is the trade being made.
- There is no LICENSE file: all rights reserved by default.
