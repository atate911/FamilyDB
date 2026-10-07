# Data and privacy

This page lists what FamilyDB stores, for how long and who can see it, and what leaves the house, to whom and whether you can turn it off. It is the one list of what leaves. Everything the family says is kept in one SQLite file on your server, and a few keys sit in plain files beside it. [What it touches](/wiki/boundaries) describes each service.

## What is stored

| What | Where it is kept | How long | Who can see it |
|---|---|---|---|
| Messages, both ways, with a voice note's words and a photo's description marked as such, and the commands and button taps | `messages` in the database | No setting, job or command removes them | The Family conversation on the page: parents and admins. A kid's own page conversation: that kid, every parent and every admin. Telegram chats: whoever is in them. Admins can open any message in full on the Activity page |
| Each tool call, with its input and result | `tool_calls` | Same | Admins on the Activity page; parents and admins see only the tools' names under an answer |
| Each model call: model, token counts, estimated cost, what it was for. Not the prompt or the reply | `llm_calls` | Same | Parents and admins see totals on Status; admins see each call |
| Ideas, places, plans, outcomes, things to do, reminders | Their own tables | Kept; an idea is dropped, not deleted | Signed-in people by role. A kid sees only their own things to do |
| Wish lists | `wishes` | Kept | The kid who wrote them, parents and admins, not another kid |
| What the bot remembers, with a quote of the message it came from | `memories` | A forgotten or replaced one keeps its words. [Memory](/wiki/controls/memory) has the rest | Parents and admins on the page. The model is sent every "Must" with each message, and other memories up to about 1,600 characters |
| The family: name, role, Telegram id, birthday, male or female for a kid, page look | `members` | Until the person is taken off | Admins on the Family page. Names and roles go to the model with every message |
| Password hashes (scrypt) | `member_logins`; the shared one in settings | Until changed, taken away or the person is taken off | Nobody through the page. A starting password is shown once to the admin who made it |
| Settings, and model and Telegram keys as plain text | `app_settings` | Until changed or removed | Admins. A key is shown only after you retype your password, if the page has one |
| The installer's first password, the Google key, the session signing key | `.env` (and its `.env.*.bak` copies), `data/google_key.json`, `data/web_secret`: plain text, owner-only | Until you change or delete them | Whoever can read the server. None is in a backup |
| The change log: who, from where, old and new values, except keys and the shared password | `settings_log` | No removal | Admins on the Settings page |
| Where somebody is: coordinates and a place name | `member_locations`, one row each | Used for 3 hours; deleted at 24 hours by a job that runs every 10 minutes, or replaced by the next share | No page shows the row. The place name can survive elsewhere: the bot's confirmation is a message, and the `suggest` tool's "travel from" line is in the tool log. Admins can read both on Activity. Coordinates stay in backups until those are pruned |
| Strangers who wrote to the bot: name, id, chat, count, never the words | `knocks` | 30 days and 200 rows, pruned when the next stranger writes, so a quiet bot keeps the last ones | Admins on the Family page |
| A Telegram link | A hash of its code | Works for 24 hours; the row goes when somebody makes or uses a link | Nobody |
| Troubles for admins | `alerts` | Until the trouble clears; rows unseen for 7 days go when the next is noted | Parents and admins on Status |
| Questions asked of a stronger model | `judgements` | 60 days, pruned only when the judgement job runs with `judgements` on; with it off (the default) a filed refusal question stays | Parents and admins on Status |
| A voice recording or a photo | Not stored. Held in memory while it is sent, then dropped; the words stay as a message | None | Not applicable |
| Safety backups and nightly backups | The backups folder (`/opt/familydb/backups` on an install) | 14 days if the nightly schedule is on; otherwise until you delete them | Root and the owner. The database and everything in it |

The service log records page sign-ins and changes with the visitor's address, password and link changes (never the password), and errors. At `log_level` DEBUG it also records traffic to Telegram and the model companies. FamilyDB sets no retention for it; the host keeps it.

## A kid's data

A kid's messages go to the model company like anybody's. The model is told every person's name and role, and in a kid's own turn their age and whether they are a girl or a boy, never the birthday. A kid's wish topics are sent only where nobody else reads the reply.

A kid's conversation on the page is read by that kid and the grown-ups; the conversation list shows a parent only when the last message was sent, never its words. A kid's Telegram chat is not on that page, and only admins can open it, through Activity. Wish lists are not shown to another kid.

A present is kept from every kid and from the grown-up it is for, and a grown-up may add others. It is left out of the pages those people see and of the bot's idea search when they ask, and out of the idea list the model carries for everyone. The hiding is of the pages and the chat, not of the data: the Activity page, the database and a backup do not hide it, and a present with a place or link is still sent to the lookup company with who it is for.

## What leaves the house

Where a row says "the company", a spare company with a key (`provider_fallback`, on by default) can receive the same content when the first is busy, out of credit or refusing.

| What leaves | To whom | When | Can you turn it off? |
|---|---|---|---|
| Your message, by default up to 20 earlier ones from the last 6 hours (each cut to 1,500 characters), names and roles, home area, time zone, the family's own words and the persona, the idea list without presents, remembered facts, and what a tool returns, such as calendar entries: titles, times, places, and the descriptions of all-day ones | The company that answers (`provider`) | Every message it answers | Not without stopping the bot. [Choose the company](/wiki/controls/settings/ai-model#who-answers); [shorten the history](/wiki/controls/settings/spending#what-one-message-may-use); [turn the spare off](/wiki/controls/settings/ai-model#a-second-company) |
| The weekend digest's question and the same context | The chat company, at the digest level | Once a week | Empty [`digest_chat_id`](/wiki/controls/settings/messages#weekend-ideas) |
| An idea's title, kind, place, description, link, who it is for, the home area, and details saved before. Its searches go to the company's hosted web search, which is given the home city, region and time zone as the search location where it takes one | The lookup company (`worker_provider`) | When an idea is looked up (by default each evening) | [`web_tools_enabled`](/wiki/controls/settings/lookups#looking-ideas-up), on after an install |
| A search for what is on: dates, a topic, the home area, who it is for and, when the question is near a place or near where someone is, that place to about 100 metres | The same company | When a suggestion asks for it | The same setting |
| A voice recording, with the family's names and home area as hints | The company that hears (OpenAI or Gemini), or the spare | Each family voice note | [`voice_notes`](/wiki/controls/settings/ai-model#voice-notes-and-photos) |
| A photo, with the same hints | The lookup company, or the spare | Each family photo | [`photos`](/wiki/controls/settings/ai-model#voice-notes-and-photos) |
| A shared location: coordinates (to about 10 metres) and place name in the turn | The chat company; the lookup company when a search starts from it (coordinates to about 100 metres) | Only after someone shares a position, or ticks "Send where I am", and only while it is under 3 hours old | Nobody has to share; there is no setting |
| The same coordinates, to about a metre, to be named | OpenStreetMap's Nominatim | When a share is not within 200 metres of the last named place | Same |
| Model names, prices and a refusal's error text, not the family's messages. A disputed price is checked on the web at the lookup level | The lookup company, at the level `judgement_level` names, or the spare | Rarely, when a change needs weighing | [`judgements`](/wiki/controls/settings/ai-model#asking-a-stronger-model-to-weigh-a-change), off unless you turn it on |
| A list-models request with each key, and requests for LiteLLM's and OpenRouter's price lists that carry nothing of the family | Each company, GitHub, OpenRouter | Daily at 05:17 | [`model_watch`](/wiki/controls/settings/ai-model#keeping-up-with-the-companies) |
| Every chat on that channel, voice notes and photos, shared positions and taps | Telegram | As the family uses it | [Remove the bot token](/wiki/controls/settings/connections#telegram) |
| Plan titles, times, places and notes; the calendar is read for what is on | Google | When a plan is made, changed or looked up | No button: delete `data/google_key.json` on the server and unshare the calendar in Google |
| Home area, idea locations, place addresses and places named in a question, to find coordinates, and an operator's `GEOCODER_CONTACT` in the request header if one is set | Nominatim, then Open-Meteo's geocoder for a short name | When one is typed or saved | No setting |
| Home coordinates and dates | Open-Meteo | When a forecast is needed | No setting; with no home position there is no forecast |
| The sound of dictation | The browser's maker (Apple for Safari, Google for Chrome; other browsers vary, and Firefox has no mic), never through FamilyDB | When someone presses the mic | [`web_dictation`](/wiki/controls/settings/general#this-page) |

What each company does with what it receives is governed by its own terms, not by FamilyDB. The page itself loads nothing from other sites: its policy allows scripts, styles and fonts only from itself.

## Taking somebody off the family list

Switching a person off deletes nothing. Taking them off for good deletes what was theirs alone (name, password, Telegram link, last place, what the bot remembers about them, a kid's wish lists) and leaves what they said and did with nobody's name on it. The words stay as written, so a name inside any text stays: a message, an idea's "for", a plan, a memory. A private Telegram chat's id, which is the person's Telegram id, stays on that chat's messages, and earlier backups still hold the person. [Family](/wiki/controls/family#switch-off-or-take-off-for-good) has the full list and the steps.

## Deleting everything

There is no setting, job or command that removes messages one at a time or by age. What you can do is take a person off, or remove the database. `uninstall.sh --purge` removes the install, the database and the nightly backups, but first writes one backup of everything to `/var/backups/familydb` (or the folder you give with `--backup-to`). Delete that yourself, or pass `--no-backup`. `--from-zero` also removes what the installer put around it and keeps no backup unless you give `--backup-to`. See [Taking it off again](/wiki/operations/install#taking-it-off-again).

**Things outside the server stay.** That `--purge` backup, which nothing prunes, stays too, along with Telegram's copy of every chat, the events written to the Google calendar, whatever each model company keeps, and the keys, which work until you revoke them.

Developer docs: `src/familydb/store/members.py` (`POINTING_AT`), `src/familydb/whereabouts.py`, `src/familydb/store/knocks.py`, `src/familydb/store/alerts.py`, `src/familydb/pipeline.py` (`_hints`), `src/familydb/agent/gateway.py` (`ask`, `listen`, `look`), `docs/DESIGN.md`, "Taking somebody off" and "Decisions", and `docs/AI_CALLS.md`.
