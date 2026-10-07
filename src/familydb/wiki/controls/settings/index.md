# Settings

Settings is where an admin changes how FamilyDB behaves without editing a file on the
server. It is one card per part of the app, and every setting on it takes effect without a
restart. Only admins can open it. A parent who follows a link to it is told it is for an admin.

| Page | What it holds |
|---|---|
| [General](/wiki/controls/settings/general) | Where home is, the time zone and units, the page's name, dictation, the log level |
| [AI model](/wiki/controls/settings/ai-model) | Which company answers, its key, how strong a model each job uses, voice notes and photos |
| [Spending](/wiki/controls/settings/spending) | The daily limit, each kid's limits, the wish-list limits, thinking and size limits |
| [Messages](/wiki/controls/settings/messages) | What is sent without being asked, and when |
| [Lookups](/wiki/controls/settings/lookups) | Filling ideas in from the web |
| [Personality and family](/wiki/controls/settings/personality) | Who the assistant is, and the family's own words about itself |
| [Connections](/wiki/controls/settings/connections) | Telegram and Google Calendar |
| [Sign-in and security](/wiki/controls/settings/sign-in) | How long a sign-in lasts, seeing a key, signing everyone out |
| What has changed | Every change made on these pages, below |

## How a setting gets its value

A setting has up to three values, and the most specific one wins:

1. **The built-in default.**
2. **The server's `.env` file**, which the installer wrote and which is how the machine was set up. In `.env` a setting is its key in capitals (`DAILY_SPEND_LIMIT`), with three exceptions: the time zone is `FAMILYDB_TZ`, and the thinking and answer-size settings also answer to `ANTHROPIC_EFFORT` and `ANTHROPIC_MAX_TOKENS`.
3. **What was saved on these pages**, which sits on top.

Emptying a box, or choosing the first choice of a list ("Default (…)"), removes the saved
value, so the setting falls back to `.env`, or to the default. A box set on the page shows a
"changed" mark. `familydb config` on the server prints every setting and where each value
came from, with secrets masked.

Changes are picked up at once by the page and by messages. Scheduled jobs follow within
five minutes, since the scheduler looks for changes at that interval. A new Telegram token
reaches the bot within a few seconds.

## What is not here

How the page is reached (its port, its domain, whether it is behind Caddy) is shown on the
General page but changed on the server, never from a form, so that nobody who is signed in
can move the page or open it wider. Keys and tokens can be saved here but are write-only; see
[AI model](/wiki/controls/settings/ai-model#keys) and [Connections](/wiki/controls/settings/connections).

## What has changed

The last page of Settings lists every change made on any of these pages, newest first, with
what it was, what it became, when, who changed it and from where (the page, or the command
line). A key or a password is never shown, only that it was replaced, and a long text only
that it was rewritten. Use it to answer "who changed that, and when?". It is kept in the
database, so it is in the [backups](/wiki/operations/backup-and-restore).

Developer docs: `docs/DESIGN.md`, "Where settings live".
