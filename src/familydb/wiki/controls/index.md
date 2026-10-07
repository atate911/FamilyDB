# How you control it

Everything FamilyDB can do can be done in three places: the web page, Telegram,
and the command line on the server. This page is the map of all three, and of who
sees what.

## The web page

Each person signs in as themselves. What a page shows depends on the person's role,
and the page asks about what they may do, never about their role by name.

| Page | What it is for | Who |
|---|---|---|
| **Home** | The box to ask Vera something, with what is coming up, what is left to do and what was added lately around it | everyone |
| **Chat** | The conversation itself (every message is paid for) | anyone who may chat |
| **Ideas** | Search and filter the ideas, open one for its hours, travel time and booking link; a tab for the restaurants; add or fix an idea | everyone reads; parents and admins change |
| **Plans** | The family calendar as a list or a month, read from Google, with what was on lately | everyone reads; parents and admins change |
| **To do** | Things to do and their reminders; a tick marks one done. A kid sees only her own | everyone |
| **Kids' lists** / **My list** | The wish lists: a kid keeps her own, a parent answers them | kids keep; parents answer |
| **What Vera knows** | What she remembers about the family, with a way to forget any of it | parents and admins |
| **Status** | What is connected, what the models have cost, what changed in models and prices, recent activity | parents and admins |
| **Guide** | This guide | parents and admins |
| **Settings** | Every setting that can change from the page | admins |
| **Family** | Who the bot talks to and who signs in, and each person's password | admins |
| **Setup** | A new install, one step at a time | admins |
| **Look** and **Your password** | How the page looks for you, and your own password | everyone signed in |

The [Settings pages](/wiki/controls/settings) are a card for each part:

- **General**: where home is, the time zone, the page's title, dictation
- **AI model**: which company answers, with which model, and its key
- **Spending**: the daily limit, and what one message may use
- **Messages**: what is sent without being asked, and when
- **Lookups**: filling ideas in from the web
- **Personality and family**: who Vera is, and the family's own words about itself
- **Connections**: Telegram, and Google Calendar
- **Sign-in and security**: passwords, how long a sign-in lasts, seeing a key, signing everyone out
- **What has changed**: every change made on the page, and who made it

A form on the page is not a second way to change things. Each one runs the same
tool the model would run when asked in chat, so the checks are the same code.

## Telegram

Chat is the main thing: say what you want, in your own words. Four commands answer
at once from the calendar, the task list and the ideas, with **no model call**:
`/today`, `/week`, `/tasks` and `/now`. `/lookup` asks for the ideas waiting to be
looked up now rather than in the evening. Only the family may ask.

Under a reminder are buttons for Done, In an hour and Tomorrow, and under a
follow-up Yes again, Not again and Didn't go. A tap does it at once, as the person
who tapped, with no model call.

## The command line

On the server, `familydb --help` lists every command. The ones an admin reaches for:

| Command | What it does |
|---|---|
| `familydb doctor [--online] [--fix]` | Checks the whole install, says what is wrong and how to fix it |
| `familydb config` | Every setting and where it came from, with secrets masked |
| `familydb password [NAME]` | Makes a new starting password for the page, shown once (the first admin unless named) |
| `familydb db status` / `backup DEST` | Row counts and recent model calls; an online backup |
| `familydb debug cost` | What each message pays for before anyone types, and the last month's cost per purpose and model |
| `familydb debug prompt TEXT` | The exact request that would be sent, without sending it |

`scripts/maintain.sh` wraps the things done to the server itself (backups, upgrades,
logs); [Running it over time](/wiki/operations) lists its commands.

## In this section

**Still to come:** a page for each screen in the table, Telegram's commands and buttons
in full, and the command line.
