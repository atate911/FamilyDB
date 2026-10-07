# Telegram: the message loop

FamilyDB asks Telegram for new updates, hands each to the same pipeline the web chat uses, and sends the answers back. This page is the mechanics. [Telegram: commands and buttons](/wiki/controls/telegram) covers what the family types and taps, [Telegram as a service](/wiki/boundaries/telegram) covers the service and what to do when it fails, and [Connections](/wiki/controls/settings/connections#telegram) covers setting it up.

## How it connects

FamilyDB uses long polling: it opens the connection to Telegram and asks for updates, and nothing connects in. You need no domain, open port or webhook for it. Telegram sends only four kinds of update: messages, edited messages (read only for a live location), button taps, and changes to the bot's place in a chat.

A supervisor thread inside `familydb run` re-reads the settings every 5 seconds and follows the token. `familydb web` alone never connects. A new token reconnects within seconds, and removing it disconnects. Status and Connections show one of four states: `off` (no token), `connected as @name` (polling), `the token was refused by Telegram` (the supervisor waits until the token changes) and `cannot reach Telegram; trying again` (every 30 seconds). Causes and fixes are on [If Telegram changes or is down](/wiki/boundaries/telegram#if-telegram-changes-or-is-down).

## What it does when it connects

1. It registers itself as the sender for replies, with and without buttons. Until then nothing can be sent, and replies wait.
2. It asks Telegram who it is and logs `telegram: polling as @name`.
3. It sets the command menu (the five commands) when it differs from Telegram's. If that fails, the log warns `the command menu could not be set`, and the commands still work, only unlisted.
4. It sets the bot's name to the persona's name (FamilyDB's with no persona) and its description to the `/start` line, each only when it differs. If Telegram asks for a wait, it waits that long; if Telegram refuses, it stops trying until the name or line changes or the bot reconnects. No model is asked.
5. It asks Telegram every 5 minutes whether the bot can read every message in a group, because a change in BotFather reaches the bot in no update. The Connections card shows the answer.

## The updates it handles

"Addressed" means the message @mentions the bot or replies to one of its messages. The mention is removed from the text before it is stored.

| What arrives | What happens | In a group |
|---|---|---|
| Text | Answered by the pipeline, after the gather pause | Ignored only when **Answer only when mentioned** is on and it is not addressed |
| A command | Answered by code, no model | `/today@BotName` works |
| `/start` | The introduction, or links a phone to a family member | |
| A voice note or audio file | Heard, then answered ([Voice notes and photos](/wiki/behavior/message-to-reply#voice-notes-and-photos)) | Same rule as text |
| A photo, or a JPEG, PNG or WebP file, or an album | Looked at | Only when addressed, whatever the setting |
| A sticker, GIF, video, video note, other file, contact, poll or dice | With no words, a reply that it cannot open that kind of message. With a caption, the caption is answered, marked as with something not seen | One with no words only when addressed. One with a caption follows the text rule |
| A shared location, live or not | Kept for use ([Shared location](/wiki/model/location)). The first share is acknowledged, and later updates of a live location are kept silently | |
| A button tap | Done by code, no model | |
| The bot added to a group | An introduction, only when someone on the family list added it | |

A voice note follows the text rule, so with **Answer only when mentioned** off, every voice note in a group is heard, and each one heard is paid for. A photo is looked at only when addressed, whatever the setting, because each one looked at is paid for.

Someone not on the family list is recorded as a knock and gets one line, but in a group a message not addressed to the bot gets no reply.

## The gather pause

Text on Telegram is kept the moment it arrives and answered after `gather_seconds` (4 by default, 0 to 30), so several messages in a row get one reply. The retry job leaves the message alone for the pause plus 5 minutes, which is why a stopped process loses nothing. While FamilyDB waits and works, "typing…" is resent every 4.5 seconds, for at most 3 minutes. Voice notes, photos, commands, taps and the web chat are not paused. The steps are in [From message to reply](/wiki/behavior/message-to-reply#a-message-from-arrival-to-reply).

## Quiet replies in groups

A reply that only says something was saved is a 👌 reaction on the message, which buzzes nobody. Where Telegram refuses reactions, it is a ✓ reply sent without a sound. Everything else is sent with a notification. A reminder or note for one person goes to that person's own chat once they have written to the bot there, when **Send what's for one person to their own chat** is on ([Telegram: where each message goes](/wiki/controls/telegram#where-each-message-goes)).

## Sending

- **Formatting.** Models write light Markdown. Code turns bold, italics, strikethrough, inline code, code blocks and links (http and https only) into Telegram's HTML, headings into bold and bullets into •. Everything else is escaped, so a message can never become markup of its own. If Telegram refuses the result, the plain words go ([If Telegram changes or is down](/wiki/boundaries/telegram#if-telegram-changes-or-is-down)). Stored text and the page's text stay as written.
- **Length.** A part is at most 4,096 characters, split at a line break where possible, else a space. Buttons go under the last part. A command's answer has its first line in bold.
- **Where it lands.** The answer to a person's update replies to their message. A reminder, weekend ideas or a note from a job is a new message to the chat.
- **Time-outs.** FamilyDB waits 30 seconds for Telegram to take a part sent by a job and 120 seconds for the answer to an update. A send that times out counts as failed, and the stored reply goes out on a later delivery run.

## Delivery

A reply is stored before it is sent and marked delivered only after the send succeeds. Telegram cannot tell FamilyDB whether a send arrived, so a reply is sometimes sent twice, and so are the earlier parts of a long reply whose later part failed. Neither runs the model or touches the calendar again.

A reply for Telegram waits stored while the channel has no sender, and goes on the first delivery run after it connects. The retry job tries each unsent reply each time it runs, and does not count attempts.

## Limits

| Limit | Value |
|---|---|
| A voice note | `voice_max_minutes` (5 by default, 1 to 30) and 20 MB, Telegram's download limit for a bot |
| A photo | 3.9 MB each, the first 4 of an album, collected for 1.5 seconds |
| Retry job | Every 5 minutes by default; a message is retried 3 times ([Jobs](/wiki/behavior/jobs)) |
| A send | 30 seconds for a job's part, 120 seconds for an answer to an update |
| The bot's name | Telegram rate-limits renames, and FamilyDB waits as asked |

Developer docs: `src/familydb/channels/telegram.py`, `src/familydb/channels/markup.py`, `src/familydb/delivery.py`, `src/familydb/routing.py`; `docs/DESIGN.md`, "Message pipeline" and "Decisions".
