# Telegram as an outside service

Telegram carries the family's chats with the bot, and this page covers the service itself: what a Telegram bot can and cannot do, what you set up, what leaves the house through it and what happens when it is down. Telegram is optional, because the page's own chat works without it. [The Telegram loop](/wiki/behavior/telegram-loop) describes how a message is handled once it arrives, and [Telegram: commands and buttons](/wiki/controls/telegram) covers what the family types and taps.

## How the bot is reached

The bot is made in Telegram with BotFather, which hands out a token. FamilyDB uses that token with the `python-telegram-bot` library and asks Telegram for new updates by long polling: it asks, waits, and asks again. Nothing comes in from outside, so the server needs no public address and no open port for Telegram.

It asks for four kinds of update: messages, edits (only so a live location can keep moving), button taps, and the bot being added to or removed from a chat. A message someone edits is not answered again.

## Edges that matter

| Edge | What FamilyDB does |
|---|---|
| A bot cannot write to someone who has not written to it | In a group, what is only for one person goes to their own chat once they have written there, or pressed Start on a link an admin made. Until then it stays in the group |
| In a group, Telegram's privacy setting decides what the bot sees | With it on, the bot sees only mentions and replies. FamilyDB asks Telegram which applies after each connect and every five minutes, and the Connections page shows it. `telegram_require_mention` narrows it further |
| A message has a size limit | Longer replies are split into several messages of at most 4,096 characters, at a line break or a space where one is near |
| Voice notes and photos are downloaded, not pushed | They are fetched only after the sender is known to be on the family list, with a minute allowed. A voice note over 20 MB, which the code treats as Telegram's limit for a bot, is not heard. A photo is fetched at the largest size not above 1,600 pixels on its long side, or the smallest if none is that small; JPEG, PNG and WebP files sent as documents count too. In a group, a photo is looked at only when it is sent to the bot |
| Stickers, files and videos are not opened | The caption is answered as a message, marked as with something not seen; with no caption the bot says it cannot read that kind |
| Telegram asks a bot to slow down | FamilyDB waits out Telegram's "retry after" only when it sets the bot's name and description. It has no other rate limiting: a reply Telegram will not take stays stored and is tried again by the delivery job |
| Reactions may be off in a chat | A plain "saved" in a group is a 👌 reaction. Where Telegram refuses it, a silent ✓ reply goes instead |
| Formatting can be refused | Replies go as Telegram's HTML, drawn from the light Markdown a model writes. If Telegram refuses it, the plain words go instead |

While a turn runs, "typing…" is sent every few seconds, for at most three minutes.

## Setting it up

1. In Telegram, open BotFather, make a bot and copy its token.
2. Paste the token into the Telegram step of [Setup](/wiki/controls/setup#telegram), or on [Connections](/wiki/controls/settings/connections#telegram). A new token takes effect within seconds, with no restart.
3. Link each person: [Family](/wiki/controls/family#link-a-telegram) and [Setup](/wiki/controls/setup#three-ways-to-link-a-persons-telegram) cover the three ways.
4. For a family group, turn off the bot's privacy setting in BotFather unless you want mentions only, then add the bot. The Connections page says what to do.

After a connect, FamilyDB sets the bot's name and description in Telegram to the name it goes by and its `/start` line, and the "/" command menu, each only when it differs from what Telegram has. No model is asked.

## What leaves the house

Telegram sees every message in a chat with the bot, in both directions, including voice notes, photos, shared positions and button taps, as it would for any bot. It also gets the bot's name, description and command menu. [What leaves the house](/wiki/security/data-and-privacy#what-leaves-the-house) lists the rest, and what Telegram keeps is governed by its own terms.

A voice note or photo is downloaded from Telegram and then sent to a model company; only its words are kept.

## If Telegram changes or is down

| What happens | What FamilyDB does |
|---|---|
| Telegram cannot be reached | The channel shows "cannot reach Telegram; trying again" and tries every 30 seconds. The page's chat is unaffected |
| Telegram refuses the token | The channel shows "the token was refused by Telegram" and waits until the token changes. Nothing retries it |
| A reply cannot be sent | It was stored before sending, so it stays and goes out when Telegram answers again |
| A refused name or description | Logged, and not tried again until the name or line changes or the bot reconnects |
| The library or Telegram's rules change | The `python-telegram-bot` floor and ceiling are pinned in `pyproject.toml`, and a monthly dependency update is tested and reviewed like any change. A change the library does not follow would show as errors in the server's log |

The Status page shows whether Telegram is connected, and [Troubleshooting](/wiki/operations/troubleshooting) covers the symptoms.

## Security of the link

**Anyone who holds the token can run the family's bot.** The token is write-only: you paste it, it is stored in the database (so it is in every [backup](/wiki/operations/backup-and-restore)), and the page never shows it again except through See a key, which asks for your password first. The change log records that it changed, never the value. Telegram's own requests carry the token in their address, so FamilyDB replaces it with `bot<token>` in every log line.

Who may talk to the bot is the family list: a Telegram id on it. A message from anyone else gets a short line with their id and a record that they knocked, never the words. No model is asked, and a stranger's voice note is not even downloaded. A link an admin makes for one person is a bearer token, so send it to that person alone.

Developer docs: `src/familydb/channels/telegram.py` (module notes, `TelegramSupervisor`), `src/familydb/routing.py`, `src/familydb/pipeline.py` (`_hear`, `_look`), `src/familydb/delivery.py`, `src/familydb/app.py` (`RedactSecrets`), and `docs/DESIGN.md`, "Integrations" (Telegram) and "Decisions" (Group vs DM, Linking Telegram).
