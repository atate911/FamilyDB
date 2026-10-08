# Connections

The Connections card connects Telegram and Google Calendar, and is the one place this guide says how. Both are optional. Without Telegram the family uses the chat on the web page, and without a calendar plans are kept in FamilyDB but never put on one. [Setup](/wiki/controls/setup) walks through the same steps one page at a time, with the same forms.

## Telegram

Telegram lets everyone message the assistant from their phone, and carries reminders and the weekend ideas. The card says whether the Telegram bot is connected (and as which bot), whether Telegram refused the saved token, or that none is set.

To make the Telegram bot and connect it:

1. On your phone, install Telegram if you do not have it, and open it.
2. Search for **BotFather**, Telegram's own tool for making bots, and choose the one with the blue tick.
3. Send it `/newbot`.
4. Give it a name, which the family will see. Once the bot is connected, its name in Telegram follows what the assistant is called.
5. Give it a username: one word ending in `bot`. If it is taken, try another.
6. BotFather replies with a token, a long line like `7123456789:AAH4k…`. Copy all of it and paste it into **Bot token** below.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Bot token (`telegram_bot_token`) | none | Connects the bot when pasted, and replaces it when pasted again. A new one is picked up within 5 seconds. Tick **Remove it** to disconnect; it shows only for a token saved here, and one from the server's `.env` has to be removed there. | The line BotFather sent |

The token is write-only. It is saved in the database, so it is in every [backup](/wiki/operations/backup-and-restore), and it is never shown again in a form. The change log records that it changed, never its value. To see it, use [See a key](/wiki/controls/settings/sign-in#see-a-key). If Telegram refuses it, copy it again from BotFather: send `/mybots`, choose the bot, then **API Token**.

Connecting the Telegram bot does not tell it who anyone is. Each person has to be linked to a Telegram account on [Family](/wiki/controls/family#link-a-telegram), and the first admin should be linked so that a trouble needing a look reaches them on Telegram; Setup does the first admin's link with **That's me**. Status words a refusal as "Telegram refused the bot token"; the log line adds "replace it on the settings page".

### Answering on Telegram

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Seconds to wait for more before answering (`gather_seconds`) | 4 | Answers several messages from one person in one chat together, in one reply and one model call, when each comes within this long of the last. Every family member's message on Telegram waits this long first; the web chat is unaffected. | 0 to 30 (0 answers each at once) |

### In a Telegram group

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Answer only when mentioned (`telegram_require_mention`) | off | On: only a message that @mentions the bot or replies to it is answered, which suits a busy group used for other things too. Off suits a group kept for planning. | on or off |
| Send what's for one person to them (`private_when_personal`) | on | Sends a reminder for somebody's own thing to do, a note on their idea, or how their plan went to their own chat with the bot on Telegram once they have written to it there, and otherwise to their own conversation on the web page. What is for everyone stays in the group. | on or off |
| The family's chat (`family_chat_id`) | where the weekend ideas go | Where a reminder for everyone goes when it was asked for on the web page or in somebody's own chat; one asked for in a group stays in that group. The morning message's plans for the day go there too. Choose the web page's chat or a Telegram chat FamilyDB has seen, or choose **Another Telegram chat** and give its id. With none set and no weekend ideas chat, it goes where it was asked for. | A chat from the list, or a Telegram chat id |

A plain "saved" in the group is a 👌 on the message, which buzzes nobody (a silent ✓ reply where reactions are off).

The card also says whether the Telegram bot can read every message in a group. If Telegram's privacy setting for bots is on, it sees only messages that mention it or reply to it. To let it read the family group:

1. Send BotFather `/setprivacy`.
2. Choose the Telegram bot, then **Disable**.
3. Remove the Telegram bot from the group and add it again, which is when Telegram applies the change.

What the service is, and what it does when Telegram is down, is on [Telegram as a service](/wiki/boundaries/telegram).

## Google Calendar

The card says whether a calendar is connected, which calendar, and the address FamilyDB reaches it as. That address belongs to a [service account](/wiki/reference/glossary#service-account), a robot Google account of its own, so FamilyDB holds nobody's sign-in. It is free, never asks anybody to sign in, and its key does not expire, but stops working if it is deleted in Google Cloud. Keep the calendar shared with it, allowing **Make changes to events**.

You do this once, in Google Cloud and Google Calendar:

1. In Google Cloud, make a project, named FamilyDB, and wait for it to finish.
2. Turn on the Google Calendar API for it.
3. Make a service account, named FamilyDB. It needs no role.
4. Open the account, then **Keys**, **Add key**, **Create new key**, **JSON**. A file is saved; copy everything in it.
5. In Google Calendar's settings, choose the family calendar under **Settings for my calendars**. Under **Share with specific people**, add the service account's address (the `client_email` line in the file, ending `iam.gserviceaccount.com`) with permission **Make changes to events**.
6. Further down, under **Integrate calendar**, copy the **Calendar ID**.
7. Paste the file's contents into **The key file** and the id into **The calendar's id**, and press **Connect**.

FamilyDB tries the calendar before keeping anything: it adds and removes a test event called "FamilyDB connection check", which may show briefly in calendar notifications. If that fails it says what is wrong.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Google calendar id (`google_calendar_id`) | set when you connect | The calendar plans go on. To use another, share it with the service account first, then paste its id. Changing only the id is not checked. | A calendar id |

The key itself is saved as a file on the server (`data/google_key.json`), not in the database, so a backup holds the calendar's id but not its key.

> **Deleting the old key first shuts FamilyDB out of the calendar until you connect again.** To replace a key, make the new one, paste it here, then delete the old one in Google Cloud.

If Google refuses the key or none is saved, or no longer shows the calendar, admins with a Telegram id are told ([Messages](/wiki/controls/settings/messages#when-something-needs-fixing)). For a refused key, connect again here with a new key. For a calendar that is gone, check that it is still shared with the service account and not deleted, then share it again or connect another. What FamilyDB reads and writes on the calendar is on [Google Calendar](/wiki/boundaries/google-calendar).

### Disconnect Google Calendar

An admin sees a closed **Disconnect Google Calendar** fold under the form once a key or a calendar id is saved. Open it, read what goes, and press **Yes, disconnect**. FamilyDB deletes the saved key and forgets the calendar's id, and any Needs a look row about the calendar goes with them. Plans stay saved here and nothing is taken off Google. Connect again at any time; the plans still to come are then copied to Google, up to 20 a run. To end Google's side as well, stop sharing the calendar and delete the key in Google Cloud.
