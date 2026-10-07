# Cost and keeping it down

FamilyDB costs what the model company charges for each call it makes. Every figure here is an estimate from FamilyDB's own price table, not your bill.

## What a message pays for

Every chat message starts with the same front part: character, instructions, family context, idea list and 23 tool definitions. `familydb debug cost` prints its size without asking a model:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb debug cost
```

On Docker:

```bash
sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb debug cost
```

On a fresh install it estimated about 6,300 tokens for the prompt and family context with Vera as shipped (about 3,500 with no persona) and about 5,600 for the tools: roughly 11,900 before anything is typed, at four characters to a token. Your family's text and up to 150 idea lines (`prompt_idea_limit`) add to it, and the uncached part (recent conversation, date, memories, the message) comes on top. A tool step is another call that carries the turn's earlier steps again.

At the built-in prices the front part alone costs, per message:

| Everyday model | Read fresh | Read from the cache |
|---|---|---|
| GPT-6 Luna (OpenAI, the default) | about $0.0012 | about $0.00012 |
| Claude Haiku 4.5 (Anthropic) | about $0.012 | about $0.0012 |
| Gemini 3.1 Flash-Lite (Google) | about $0.003 | about $0.0003 |

On Claude, the first message after the cache goes cold also pays to write it: twice the input price with the default hour setting, 1.25 times with 5m (about $0.024 for Haiku 4.5). Answers, thinking and tool steps are extra. Only lookups, discovery and price checks search the web, at about a cent a search on OpenAI and Claude and 1.4 cents on Gemini; the chat model never does.

## What the cache does

The company reads a request that starts the same way as the last one at a fraction of the input price: a tenth for most models in the built-in table. So nothing volatile is in the front part: dates, the sender, a shared location and memories go in the current turn, after it. Editing the family's words or the character, or changing any idea, makes the next message pay full price again for that part. On Claude the cache lasts an hour by default (`anthropic_cache_ttl`); OpenAI and Gemini cache on their own, and not every repeat hits. If Status shows the cache share stuck at zero, see [Troubleshooting](/wiki/operations/troubleshooting#costs-are-higher-than-expected).

## The daily limit

The [spending limit](/wiki/reference/glossary#spending-limit) is $2.00 a day by default, and 0 turns it off. Before every call FamilyDB adds up what the day's calls were estimated to cost and stops asking a model once the total reaches the limit. [Spending](/wiki/controls/settings/spending#the-daily-limit) has the settings, including each kid's share and message count.

- **It is not the bill.** The price table can be out of date. Set a limit with the model company too.
- **It can stop slightly early.** Each call in flight holds the most it could cost (all input fresh, the whole output allowance used), and a call does not count its own hold, so one call can still cross the limit. `max_output_tokens` mostly sizes that hold: lowering it does little to typical spend.
- **It stops everything that asks a model.** Lookups wait for tomorrow, and admins with a Telegram id are told if "Tell admins on Telegram" is on. Reminders, commands and buttons ask no model and carry on.

## How prices are known

FamilyDB starts from a table built into this version, and a daily check lays newer prices over it ([Models and prices](/wiki/controls/status/models-and-prices)). A model neither knows is counted at $15 in and $75 out per million tokens and 3.5 cents a search: dearer per token than any model in the built-in table, so the limit stops early rather than late. Status marks such a model with an asterisk.

## What each kind of call is

Status and `debug cost` name each kind by what it was for. Nothing else asks a model: reminders, follow-ups, the evening plan check, nudges, commands, buttons, alerts and the daily check answer in code, and remembering something rides on the chat call.

| What for (kind) | When it runs | On by default |
|---|---|---|
| Answering the family (`chat`) | Every message that reaches a model | Yes |
| The weekend digest (`digest`) | Weekly, Thursday 18:00 by default | After an install, which sets the page's chat; the program's own default is no chat |
| Answering a message again after a failure (`retry`) | The retry job, every 5 minutes by default, 3 tries by default | Only after a failure |
| Looking ideas up (`enrich`) | One turn per idea, up to 3 searches; by default together at 21:00, up to 40 a night | After an install; the program's own default is off |
| Searching for what is on (`discover`) | Inside a suggestion that asks what is on, up to 4 searches; kept 12 hours per window, until a restart or settings change | With lookups |
| Weighing a change in the models (`judge`) | Evenings when a change needs weighing (a refusal at once), on `judgement_level` (best by default), about a cent or three a question, capped by `judgement_budget` ($1 a month by default) | No |
| Checking a disputed price (`price_check`) | With the judging, up to 2 questions per run (every 15 minutes), 3 searches each, same budget | No |
| Listening to voice notes (`transcribe`) | Each voice note, up to 5 minutes by default, before its chat call | Yes, with an OpenAI or Gemini key |
| Reading photos (`look`) | Each photo, up to four of an album, on the lookup model, before its chat call | Yes |

A voice note or a photo pays twice: once to be written down, then as a chat message. A voice note is counted in tokens, so FamilyDB has no per-minute price; about a third of a cent a minute is OpenAI's published rate for the default speech model, and the limit holds up to about 0.7 cents a minute until the real use is known. A photo is about a tenth of a cent on GPT-6 Luna.

## What you can turn down

| Lever | Setting | Default |
|---|---|---|
| Model strength for chat, the digest, lookups and photos | [`chat_level`, `digest_level`, `lookup_level`](/wiki/controls/settings/ai-model#how-strong-a-model-answers) | everyday, the cheapest |
| Thinking, history, ideas and steps | [`effort`, `worker_effort`, `history_limit`, `history_hours`, `prompt_idea_limit`, `agent_max_iterations`](/wiki/controls/settings/spending#thinking) | medium, low, 20, 6 hours, 150, 8 |
| Web lookups and discovery | [`web_tools_enabled`](/wiki/controls/settings/lookups#looking-ideas-up) | on after an install |
| Voice notes and photos | [`voice_notes`, `photos`](/wiki/controls/settings/ai-model#voice-notes-and-photos) | on |
| The weekend digest | [`digest_chat_id`](/wiki/controls/settings/messages#weekend-ideas) (empty sends none) | the page's chat after an install; otherwise empty |

Effort does nothing for a model that does not think, such as Claude Haiku 4.5.

## Reading the last 30 days

[Status](/wiki/controls/status) shows today's spend against the limit and, under "Where the money went", the calls and dollars for each kind and the cache share, with no model call. `familydb debug cost --days N` prints the same by model, and [Recent activity](/wiki/controls/status/activity) opens one message's calls. A kind of call that starts costing much more raises a row: see [Models and prices](/wiki/controls/status/models-and-prices#needs-a-look-rows-about-models).

## The company's own limit

Because the daily limit is an estimate, the model company's own limit is the backstop: set a monthly limit or alert in its console. If the account runs out of credit, a row appears under Needs a look. With a second company's key saved and the fallback on (the default), the call can go to that company, but only before the turn has changed anything. A rate limit is retried, not failed for good.

Developer docs: `docs/DESIGN.md`, "Cost"; `docs/AI_CALLS.md`, "The calls today" and "Choosing models"; `familydb/agent/spending.py` and `familydb/agent/providers/prices.py` (module notes).
