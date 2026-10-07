# Connections settings

Telegram, and Google Calendar. Both are optional. Without Telegram the family uses the chat on the
page, and without a calendar plans are kept in FamilyDB but never put on one.

## Telegram

The card says whether the bot is connected (and as which bot), whether Telegram refused the saved
token, or that none is set.

| Setting | Default | What it does |
|---|---|---|
| Bot token | none | The long line BotFather sent when the bot was made. Paste it to connect or replace it, tick "Remove it" to disconnect. A new one reaches the bot within a few seconds, with no restart. "Remove it" shows only for a token saved on the page; one from the server's `.env` file is marked as such and has to be removed there |

The token is write-only: it is saved in the database (so it is in every
[backup](/wiki/operations/backup-and-restore)) and never shown again in a form. The change log records
that it changed, never its value. To see it, use [See a key](/wiki/controls/settings/sign-in#see-a-key). If Telegram refuses it,
copy it again from BotFather (send `/mybots`, choose the bot, then API Token). Making the bot, linking
a phone to it and adding the family's group are in the Telegram step of the setup, which goes through
them one at a time.

### Answering on Telegram

| Setting | Default | What it does |
|---|---|---|
| Seconds to wait for more before answering (`gather_seconds`) | 4 | Several messages from the same person in the same chat, sent one after another, are answered together, in one reply and one model call, when each comes within this long of the last (each new message restarts the wait). Every family member's message on Telegram waits this long first; the page's chat is unaffected. 0 answers each at once. Between 0 and 30 |

### In a Telegram group

| Setting | Default | What it does |
|---|---|---|
| Answer only when mentioned (`telegram_require_mention`) | off | On: only a message that @mentions the bot or replies to it is answered, which suits a busy group the family uses for other things too. Off suits a group kept for planning, where everything said is for the assistant |
| Send what's for one person to their own chat (`private_when_personal`) | on | A reminder for somebody's own thing to do, a note on an idea they added, how their plan went: sent to their own chat with the bot, once they have written to it there, and not to the whole group. What is for everyone stays in the group. Either way a plain "saved" in the group is a 👌 on the message, which buzzes nobody (a silent ✓ reply where reactions are off) |

The card also says whether the bot can read every message in a group. If Telegram's privacy setting
for bots is on, it sees only messages that mention it or reply to it. To let it read the family group,
send BotFather `/setprivacy`, choose the bot, then Disable; then remove the bot from the group and add it
again, which is when Telegram applies the change.

## Google Calendar

The card says whether a calendar is connected, which calendar, and the address the bot reaches it as.
That address is a **service account**, a robot Google account of its own, so the bot holds nobody's
sign-in. The calendar must stay shared with it, allowing "Make changes to events".

Connecting is done once, in Google Cloud: make a project, turn on the Google Calendar API, make a service
account and a JSON key for it, and share the family calendar with the account's address. Then paste the key
file's contents and the calendar's id into the page's form, which checks the access before saving anything
by adding and removing a test event called "FamilyDB connection check" (it may show briefly in calendar
notifications). The setup's Google Calendar step walks through it. The key does not expire, but stops
working if it is deleted in Google Cloud.

| Setting | Default | What it does |
|---|---|---|
| Google calendar id (`google_calendar_id`) | set when you connect | To use another calendar, share it with the service account first, then paste its id from Google Calendar's Settings and sharing, under Integrate calendar. Changing only the id is not checked, so share the calendar before you save it |

The key itself is saved as a file on the server (`data/google_key.json`), not in the database, so a
[backup](/wiki/operations/backup-and-restore) holds the calendar's id but not its key.
