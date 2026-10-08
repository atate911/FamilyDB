# Shared location

Shared location lets the assistant answer "near here" and "open now" from where your phone is. It is off until you tick a box on the web page or send a location in Telegram, and nothing else ever sends one. To use it, see [Share where I am](/wiki/controls/home-and-chat#share-where-i-am) and [Telegram](/wiki/controls/telegram).

## How a position arrives

- **On the web page:** tick **Share where I am with this message** under the box on Home or Chat. The tick appears only where the browser can give a position. The browser asks your permission, and its position goes with that one message.
- **In Telegram:** attach a location (the paperclip, then Location), once or live. A live location keeps the position current while it runs.

FamilyDB names the place once, as in "Old Town, Portland". On Telegram it replies once to say it has the location; later updates of a live location are silent.

## What is kept and for how long

FamilyDB keeps one position for each person, and each new share replaces it. The assistant uses it for 3 hours after the share. The forget-locations job (`forget_locations`, every 10 minutes) deletes it when it is a day old, and so does the next share by anybody. Backups keep the coordinates until they are pruned ([Backup and restore](/wiki/operations/backup-and-restore)).

## Who sees it

Only you and the assistant, and only on your own messages. No page shows it, and no other person's message carries it. The assistant's reply can name the place, so in a group chat, or in a kid's chat that a parent reads, the readers see that name. Admins reading [Recent activity](/wiki/controls/status/activity) can see the place name in the confirmation and the "travel from" line.

## What each company gets

The family decided that the coordinates may go to the [model company](/wiki/reference/glossary#model-company). If the second company answers in its place, it gets the same text.

| Who | Gets | When |
|---|---|---|
| Model company, for chat | Place name and coordinates to 4 decimals (about 10 metres), with your message | Each message while the position is under 3 hours old |
| Model company, for the web search of what is on | Place name and coordinates to 3 decimals (about 100 metres) | When a suggestion starts from your position |
| OpenStreetMap (Nominatim) | The coordinates, to name the place | Once per share, and not again while you stay within 200 metres |

Telegram sees a shared location as it sees any message. The full list of what leaves the house is on [What leaves the house](/wiki/security/what-leaves-the-house).

## How to stop

Do not tick the box, or do not send a location. Unticking the box before you send stops that message carrying one. In Telegram, stop a live location in Telegram's own screen.

A position already shared stays until it ages out: the assistant stops using it after 3 hours and the job deletes it within a day. Nothing deletes it sooner except [taking you off the list for good](/wiki/controls/family#switch-off-or-take-off-for-good). With no fresh position, travel is counted from home.

## What outlives the coordinates

## The place name goes with the position

When a position is forgotten, by the job, by the next share or because the person is taken off for good, FamilyDB takes its place name out of what held it:

- The "Got it" reply loses the name in parentheses.
- The model texts, tool calls and suggestions kept for [Recent activity](/wiki/controls/status/activity) show "[place forgotten]" in its place. Only rows made after the name was given are changed, and a name shorter than 3 characters is left.

Two things are not scrubbed. Coordinates inside kept model texts go only with those texts, after their own days. Words of the assistant or the family that name the place, such as "I am at the park", stay in the messages.

Developer docs: src/familydb/whereabouts.py and suggest/origin.py; docs/DESIGN.md, "Suggestion engine: answering "what should we do?"".
