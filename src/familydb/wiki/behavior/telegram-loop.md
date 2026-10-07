# The Telegram loop

This page explains how the bot talks to Telegram: it asks Telegram for new updates, hands each to the same pipeline the page's chat uses, and sends the answers back. The commands and buttons are on [Telegram: commands and buttons](/wiki/controls/telegram), and the settings are on [Connections](/wiki/controls/settings/connections).

## How it connects

The bot uses long polling: it opens the connection to Telegram and asks for updates, and nothing connects in. You need no domain, open port or webhook for it. Telegram sends only four kinds of update: messages, edited messages (read only for a live location), button taps, and changes to the bot's place in a chat.

A supervisor thread inside `familydb run` re-reads the settings every 5 seconds and follows the token. `familydb web` alone never connects. A new token reconnects within seconds, with no restart, and removing it disconnects.

| State (Status and Connections) | Means | What the supervisor does |
|---|---|---|
| connected as @name | Polling | Checks the token setting every 5 seconds |
| the token was refused by Telegram | The token is wrong or revoked | Waits until the token changes |
| cannot reach Telegram; trying again | The connection failed | Tries again every 30 seconds |

## What it does when it connects

1. It registers itself as the sender for replies, with and without buttons. Until then nothing can be sent, and replies wait.
2. It asks Telegram who it is and logs "telegram: polling as @name".
3. It sets the command menu (the five commands) when it differs from Telegram's. If that fails, the log warns "the command menu could not be set", and the commands still work, only unlisted.
4. It sets the bot's name to the persona's name (FamilyDB's with no persona) and its description to the `/start` line, each only when it differs, cut to Telegram's length limits. It checks again when either changes. If Telegram asks for a wait, it waits that long. If Telegram is unreachable, it tries again in 30 seconds. If Telegram refuses, it logs a warning and stops until the name or line changes or the bot reconnects. No model is asked.
5. It asks Telegram every 5 minutes whether the bot can read every message in a group, because a change in BotFather reaches the bot in no update. The Connections card shows the answer.

## The updates it handles

"Addressed" means the message @mentions the bot or replies to one of its messages. The mention is removed from the text before it is stored.

| What arrives | What happens | In a group |
|---|---|---|
| Text | Answered by the pipeline, after the gather pause | Ignored only when "answer only when mentioned" is on and it is not addressed |
| A command | Answered by code, no model | `/today@BotName` works |
| `/start` | The introduction, or links a phone to a family member | |
| A voice note or audio file | Heard, then answered ([Lifecycles](/wiki/behavior/lifecycles#a-voice-note)) | Same rule as text |
| A photo, or a JPEG, PNG or WebP file, or an album | Looked at ([Lifecycles](/wiki/behavior/lifecycles#a-photo)) | Only when addressed, whatever the setting |
| A sticker, GIF, video, video note, other file, contact, poll or dice | With no words, "I can't open that kind of message". With a caption, the caption is answered, marked "(with a sticker, not seen)" | Only when addressed |
| A shared location, live or not | Kept for use for 3 hours and deleted within a day. The first share is acknowledged, and later updates of a live location are kept silently | |
| A button tap | Done by code, no model | |
| The bot added to a group | An introduction, only when someone on the family list added it | |

Someone not on the family list is recorded as a knock and gets one line, but in a group a message not addressed to the bot gets no reply.

## The gather pause

Text on Telegram is kept the moment it arrives and answered after `gather_seconds` (4 by default, 0 to 30), so several messages in a row get one reply. The message is held from the retry job for the pause plus 5 minutes, which is why a stopped process loses nothing. While the bot waits and works, "typing…" is resent every 4.5 seconds, for at most 3 minutes. Voice notes, photos, commands, taps and the page's chat are not paused. The steps are in [Lifecycles](/wiki/behavior/lifecycles#a-message-from-arrival-to-reply).

## Quiet replies in groups

A reply that only says something was saved is a 👌 reaction on the message, which buzzes nobody. Where Telegram refuses reactions, it is a ✓ reply sent without a sound. A ✓ sent later, by the delivery job, goes the same way, without a sound. Everything else is sent with a notification. A reminder or note for one person goes to that person's own chat once they have written to the bot there, when "send what's for one person to their own chat" is on ([Telegram: where each message goes](/wiki/controls/telegram#where-each-message-goes)).

## Sending

- **Formatting.** Models write light Markdown. Code turns bold, italics, strikethrough, inline code, code blocks and links (http and https only) into Telegram's HTML, headings into bold and bullets into •. Everything else is escaped, so a message can never become markup of its own. If marks cross, the message goes with its marks as written. If Telegram still refuses ("parse entities"), the plain words go, and the log says "the formatting was refused". Stored text and the page's text stay as written.
- **Length.** A part is at most 4,096 characters, split at a line break where possible, else a space. Buttons go under the last part. A command's answer has its first line in bold.
- **Where it lands.** The answer to a person's update replies to their message. A reminder, a digest or a note from a job is a new message to the chat. A job's part waits at most 30 seconds, and an answer to an update 120 seconds.

## Delivery

A reply is stored before it is sent and marked delivered only after the send succeeds, so delivery is at least once. A send Telegram accepted whose answer was lost can arrive twice, and so can the earlier parts of a long reply whose later part failed. Neither runs the model or touches the calendar again.

While Telegram is not connected, replies for it stay stored and go on the next delivery run after it connects. The retry job (every 5 minutes by default) tries every unsent reply each time it runs, and does not count attempts. The weekend digest and follow-ups run the same delivery first. See [Jobs](/wiki/behavior/jobs).

## When Telegram or the token fails

| What happened | Where you see it | What the family sees |
|---|---|---|
| The token is refused | Status and Connections: "the token was refused by Telegram". Log: "telegram: Telegram refused the bot token; replace it on the settings page" | Nothing arrives on Telegram, and the page's chat still works |
| Telegram cannot be reached | "cannot reach Telegram; trying again". Log: "telegram: cannot reach Telegram (...); trying again shortly" | Nothing arrives until it connects |
| A send fails | Log: "delivery pending for message N" | The reply arrives on a later delivery run |
| The formatting is refused | Log warning "the formatting was refused, so it went as plain words" | The reply arrives without formatting |
| A reaction is refused | Log: "no reaction here (...), so the ✓ goes quietly" | A silent ✓ |
| A tap cannot be marked on its message | Log: "could not add who did it to a message", or "could not take the buttons off a message" | The tap still ran, and the buttons stay |

Telegram trouble is not among what admins are told on Telegram. It shows in the Telegram row on [Status](/wiki/controls/status) and on Connections. Fixes are in [Troubleshooting](/wiki/operations/troubleshooting).

## Limits that matter

| Limit | Value |
|---|---|
| A voice note | `voice_max_minutes` (5 by default, 1 to 30) and 20 MB, Telegram's download limit for a bot |
| A photo | 3.9 MB each, the first four of an album, fetched within 1,600 pixels on the long side |
| An album | Collected for 1.5 seconds |
| Fetching a file | 60 seconds |
| A text part | 4,096 characters |
| Gather pause | `gather_seconds`, 4 by default |
| Retry job | Every 5 minutes, 3 attempts by default |
| The bot's name | Telegram rate-limits renames, and the bot waits as asked |

Developer docs: `src/familydb/channels/telegram.py` (`TelegramChannel`, `TelegramSupervisor`), `channels/markup.py`, `delivery.py`, `routing.py`, and `docs/DESIGN.md` ("Message pipeline", "Group vs DM").
