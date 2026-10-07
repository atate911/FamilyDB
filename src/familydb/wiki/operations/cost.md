# Cost

FamilyDB costs what the model companies charge for the calls it makes, and nothing else: an idle FamilyDB asks no model. Companies charge by the [token](/wiki/reference/glossary#token), the small piece of text a model reads or writes, about three quarters of a word. Every money figure in FamilyDB is an estimate from its own price table, not the bill.

To see what a message pays for on your install, run `familydb debug cost`. It prints the size of the fixed start of each request without asking a model. Run it as in [The command line](/wiki/operations/command-line#how-to-run-it).

## What a message pays for

Every chat message starts with the same front part: the character, the instructions, the family context, the idea list and the definitions of the assistant's tools. Your family's text and up to 150 idea lines (`prompt_idea_limit`) add to it. The uncached part comes on top: recent conversation, the date, memories and the message itself. A tool step is another call that carries the turn's earlier steps again, so a message that uses three tools pays for four calls.

Answers and thinking are extra. Only lookups, discovery and price checks search the web, at about US$0.01 a search on OpenAI and Claude and US$0.014 on Gemini. The chat model never searches.

## What the cache does

The [prompt cache](/wiki/reference/glossary#prompt-cache) is the company reading a request that starts the same way as the last one at a fraction of the input price: a tenth for most models in the built-in table. For that reason nothing that changes sits in the front part. Dates, the sender, a shared location and memories go in the current turn, after it.

Editing the family's words or the character, or changing any idea, makes the next message pay full price again for that part. On Claude the cache lasts an hour by default (`anthropic_cache_ttl`), and the first message after it goes cold also pays to write it: twice the input price with the 1-hour setting, 1.25 times with `5m`. OpenAI and Gemini cache on their own, and not every repeat hits.

## The daily limit

The [spending limit](/wiki/reference/glossary#spending-limit) is US$2.00 a day by default, and 0 turns it off. Before every call FamilyDB adds up what the day's calls were estimated to cost and stops asking a model once the total reaches the limit. [Spending](/wiki/controls/settings/spending#the-daily-limit) has the settings, including each kid's share and message count.

- The limit is not the bill. The price table can be out of date, so also set a limit in the model company's console.
- It can stop slightly early. Each call in flight reserves the most it could cost (all input fresh, the whole output allowance used), and a call does not count its own reserve, so one call can still cross the limit. `max_output_tokens` mostly sizes that reserve, so lowering it does little to typical spend.
- It stops everything that asks a model. Lookups wait for tomorrow, and admins with a Telegram id are told if **Tell admins on Telegram** is on. Reminders, commands and buttons ask no model and carry on.

A model that neither the built-in table nor the daily check lists is counted at US$15 in and US$75 out per million tokens, dearer than any listed model, so the limit stops early rather than late. Status marks such a model with an asterisk. Where prices come from is on [Models and prices](/wiki/controls/status/models-and-prices#what-the-daily-check-does).

## What each kind of call is

Status and `familydb debug cost` name each kind of call by what it was for. Nothing else asks a model: reminders, follow-ups, the evening-before check, nudges, commands, buttons, alerts and the daily check answer in code, and remembering something rides on the chat call.

| What for | When it runs | On by default |
|---|---|---|
| Answering the family | Every message that reaches a model | Yes |
| The weekend ideas message | Weekly, Thursday 18:00 by default | After an install, which sets the web chat; the program's own default is no chat |
| Answering a message again after a failure | The retry job, every 5 minutes by default, up to 3 retries by default | Only after a failure |
| Looking ideas up | One turn per idea, up to 3 searches; by default together at 21:00, up to 40 a night | After an install; the program's own default is off |
| Searching for what is on | Inside a suggestion that asks what is on, up to 4 searches; kept 12 hours per window | With lookups |
| Weighing a change in the models | Evenings when a change needs weighing (a refusal at once), on `judgement_level` (`best` by default), within `judgement_budget` (US$1 a month by default) | No |
| Checking a disputed price | With the weighing, up to 2 questions per run (every 15 minutes), 3 searches each, same budget | No |
| Listening to voice notes | Each voice note, up to 5 minutes by default, before its chat call | Yes, with an OpenAI or Gemini key |
| Reading photos | Each photo, up to four of an album, on the lookup model, before its chat call | Yes |

A voice note or a photo pays twice: once to be written down, then as a chat message. A voice note is counted in tokens, so FamilyDB has no per-minute price for it.

## What you can turn down

| Lever | Setting | Default |
|---|---|---|
| Model strength for chat, weekend ideas, lookups and photos | [`chat_level`, `digest_level`, `lookup_level`](/wiki/controls/settings/ai-model#how-strong-a-model-answers) | everyday, the cheapest |
| Thinking, history, ideas and steps | [`effort`, `worker_effort`, `history_limit`, `history_hours`, `prompt_idea_limit`, `agent_max_iterations`](/wiki/controls/settings/spending#thinking) | medium, low, 20, 6 hours, 150, 8 |
| Web lookups and discovery | [`web_tools_enabled`](/wiki/controls/settings/lookups#looking-ideas-up) | on after an install |
| Voice notes and photos | [`voice_notes`, `photos`](/wiki/controls/settings/ai-model#voice-notes-and-photos) | on |
| Weekend ideas | [`digest_chat_id`](/wiki/controls/settings/messages#weekend-ideas) (empty sends none) | the web chat after an install; otherwise empty |

Effort does nothing for a model that does not think, such as Claude Haiku 4.5.

## If costs are higher than expected

1. Open [Status](/wiki/controls/status). Today's spend against the limit and, under **Where the money went**, the calls and dollars for each kind of call are there, with no model call.
2. Find the kind that grew. `familydb debug cost --days 30` prints the same by model, and [Recent activity](/wiki/controls/status/activity) opens one message's calls.
3. If the cache share stays at zero, something in the front part changes on every message. The usual cause is editing the family's words or the ideas often.
4. Turn down the lever in the table above that matches the kind.

A kind of call that starts costing much more raises a row on Status: see [Models and prices](/wiki/controls/status/models-and-prices#needs-a-look-rows-about-models).

## The company's own limit

Because the daily limit is an estimate, the model company's own limit is the backstop: set a monthly limit or alert in its console. If the account runs out of credit, a row appears under **Needs a look**. With a second company's key saved and **Ask another company when the first cannot** on (the default), the call can go to that company, but only before the turn has changed anything. A rate limit is retried, not failed for good.
