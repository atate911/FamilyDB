# Telegram as a service

Telegram carries the family's chats with FamilyDB. The service has limits a bot cannot get around, sees everything said in the chat, and can be down. Telegram is optional, because the web chat works without it. [Telegram: the message loop](/wiki/behavior/telegram-loop) covers how a message is handled once it arrives, [Telegram: commands and buttons](/wiki/controls/telegram) covers what the family types and taps, and [Connections](/wiki/controls/settings/connections#telegram) covers setting it up.

## How the bot is reached

The bot is made in Telegram with BotFather, which hands out a token. FamilyDB asks Telegram for new updates by long polling: it asks, waits, and asks again. Nothing comes in from outside, so the server needs no public address and no open port for Telegram.

## What a Telegram bot cannot do

| What a bot cannot do | What FamilyDB does |
|---|---|
| Write to someone who has not written to it | In a group, what is only for one person goes to their own chat once they have written there, or pressed Start on a link an admin made. Until then it stays in the group |
| See every message in a group when Telegram's privacy setting is on | The bot sees only mentions and replies. FamilyDB asks Telegram which applies after each connect and every 5 minutes, and Connections shows it. `telegram_require_mention` narrows it further |
| Send a long message | Longer replies are split into messages of at most 4,096 characters, at a line break or a space where one is near |
| Have voice notes and photos pushed to it | FamilyDB fetches them, and only after the sender is known to be on the family list. See below the table |
| Open stickers, files and videos | The caption is answered as a message, marked as with something not seen; with no caption FamilyDB says it cannot read that kind |
| Send as fast as it likes | FamilyDB waits out Telegram's "retry after" only when it sets the bot's name and description. A reply Telegram will not take stays stored and is tried again by the retry job |
| React in every chat, or accept every format | A plain "saved" in a group is a 👌 reaction; where Telegram refuses it, a silent ✓ reply goes instead. Replies go as Telegram's HTML; if Telegram refuses it, the plain words go instead |

A voice note or photo is fetched with 60 seconds allowed. A voice note over 20 MB, which FamilyDB treats as Telegram's limit for a bot, is not heard. A photo is fetched at the largest size not above 1,600 pixels on its long side, or the smallest if none is that small, and JPEG, PNG and WebP files sent as documents count too. In a group, a photo is looked at only when it is sent to the bot.

## Setting it up

Make a bot with BotFather and copy its token. Paste the token into the Telegram step of [Setup](/wiki/controls/setup#telegram) or onto [Connections](/wiki/controls/settings/connections#telegram), then link each person ([Link a Telegram](/wiki/controls/family#link-a-telegram)). For a family group, turn off the bot's privacy setting in BotFather unless you want mentions only, then add the bot.

## What leaves the house

Telegram sees every message in a chat with the bot, in both directions, including voice notes, photos, shared positions and button taps, as it would for any bot, and it gets the bot's name, description and command menu. [What leaves the house](/wiki/security/what-leaves-the-house) lists the rest, and what Telegram keeps is governed by its own terms.

## If Telegram changes or is down

| What happened | Where you see it | What the family sees |
|---|---|---|
| Telegram cannot be reached | Status and Connections: `cannot reach Telegram; trying again`. Log: `telegram: cannot reach Telegram (...); trying again shortly` | Nothing arrives on Telegram until FamilyDB reconnects, which it tries every 30 seconds. The web chat still works |
| Telegram refuses the token | Status and Connections: `the token was refused by Telegram`. Log: `telegram: Telegram refused the bot token; replace it on the settings page` | Nothing arrives on Telegram, and nothing retries until the token changes. The web chat still works |
| A reply cannot be sent | Log: `delivery pending for message N` | The reply was stored first, so it arrives on a later delivery run |
| The name or description is refused | Log: `telegram: Telegram refused her name or introduction (...)` | Nothing changes. FamilyDB does not try again until the name or line changes or the bot reconnects |
| The formatting is refused | Log: `telegram: the formatting was refused, so it went as plain words (...)` | The reply arrives without formatting |
| A reaction is refused | Log: `telegram: no reaction here (...), so the ✓ goes quietly` | A silent ✓ |
| A tap cannot be marked on its message | Log: `could not add who did it to a message` or `could not take the buttons off a message` | The tap still ran, and the buttons stay |

Telegram trouble is not among what admins are told on Telegram. It shows in the Telegram row on [Status](/wiki/controls/status) and on Connections, and [Troubleshooting](/wiki/operations/troubleshooting) covers the symptoms.

## Security of the link

> **Anyone who holds the token can run the family's bot.** The token is write-only: you paste it, it is stored in the database (so it is in every [backup](/wiki/operations/backup-and-restore)), and the page never shows it again except through **See a key**, which asks for your password first.

The change log records that the token changed, never the value. Telegram's own requests carry the token in their address, so FamilyDB replaces it with `bot<token>` in every log line.

Who may talk to the bot is the family list: a Telegram id on it. A message from anyone else gets a short line with their id and a record that they knocked, never the words ([Who may message the bot](/wiki/model/family-and-roles#who-may-message-the-bot)). A link an admin makes for one person works for whoever holds it, so send it to that person alone.

Developer docs: `src/familydb/channels/telegram.py`, `src/familydb/routing.py`, `src/familydb/pipeline.py`, `src/familydb/delivery.py`, `src/familydb/app.py`; `docs/DESIGN.md`, "Integrations" and "Decisions".
