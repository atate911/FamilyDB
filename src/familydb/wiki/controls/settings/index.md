# Settings

Settings is where an admin changes how FamilyDB behaves, one card at a time, with no file to edit. This page says which card holds what, and how a value saved here beats the one in `.env`. Only admins can open it; a parent who follows a link to it is told it is for an admin.

| Card | What it holds |
|---|---|
| [General](/wiki/controls/settings/general) | Where home is, the time zone and units, the web page's name, dictation, the log level |
| [AI model](/wiki/controls/settings/ai-model) | Which model company answers, its key, how strong a model each job uses, voice notes and photos |
| [Spending](/wiki/controls/settings/spending) | The daily limit, each kid's limits, the wish-list limits, thinking and size limits |
| [Messages](/wiki/controls/settings/messages) | What is sent without being asked, and when |
| [Lookups](/wiki/controls/settings/lookups) | Filling ideas in from the web |
| [Personality and family](/wiki/controls/settings/personality) | Who the assistant is, and the family's own words about itself |
| [Connections](/wiki/controls/settings/connections) | Telegram and Google Calendar |
| [Sign-in and security](/wiki/controls/settings/sign-in) | How long a sign-in lasts, seeing a key, signing everyone out |
| [What has changed](#what-has-changed) | Every change made on these cards (described below) |

## How a setting gets its value

A setting has up to three values, and the most specific one wins:

1. **The built-in default.**
2. **The server's `.env` file**, which the installer wrote. Edit it and restart FamilyDB to apply a change; a real environment variable beats the file. In `.env` a setting is its key in capitals (`DAILY_SPEND_LIMIT`), with three exceptions: the time zone is `FAMILYDB_TZ`, and the thinking and answer-size settings also answer to `ANTHROPIC_EFFORT` and `ANTHROPIC_MAX_TOKENS`.
3. **What was saved on these cards**, which sits on top.

Emptying a box, or choosing the first choice of a list ("Default (…)"), removes the saved value, so the setting falls back to `.env`, or to the default. A box set on the page shows a "changed" mark. `familydb config` prints every setting with its source, secrets masked; run it as in [The command line](/wiki/operations/command-line#how-to-run-it).

Settings apply on the next message or page view; job schedules within five minutes, because FamilyDB's settings watch looks for changes at that interval. A new Telegram token is picked up within 5 seconds.

## What is not here

How the web page is reached (its port, its domain, whether it is behind Caddy) is shown on General but changed on the server, never from a form, so that nobody who is signed in can move the page or open it wider. Keys and tokens can be saved here but are write-only; see [Keys](/wiki/controls/settings/ai-model#keys) and [Connections](/wiki/controls/settings/connections).

## What has changed

The last card, What has changed, lists every change made on any card, newest first: what it was, what it became, when, who changed it and from where (the web page, the command line, or a stronger model's judgment). A key or a password is never shown, only that it was replaced, and a long text only that it was rewritten. It answers "who changed that, and when?". It is kept in the database, so it is in the [backups](/wiki/operations/backup-and-restore).
