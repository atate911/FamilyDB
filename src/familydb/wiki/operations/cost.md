# Cost and keeping it down

FamilyDB's running cost is what the model company charges for each call it makes. This page says what a message pays for before anyone types, what the daily limit is and is not, what each kind of call is, and what turns the cost down. Every figure here is an estimate, not your bill.

## What a message pays for

Every chat message starts with the same front part: the assistant's character, the instructions, the family's own words about themselves, the idea list and the 23 tool definitions. `familydb debug cost` prints its size without asking a model:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb debug cost
```

On Docker:

```bash
sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb debug cost
```

On a fresh install, with an empty family and idea list, it estimated about 6,300 tokens for the prompt and family context with Vera as shipped (about 4,250 with the "in brief" persona, about 3,500 with none) and about 5,600 for the tools: roughly 11,900 before anything is typed. The count is four characters to a token. Your family's text and up to 150 idea lines add to it, and the uncached part of each message (recent conversation, the date, the memories chosen for it, the message) comes on top. A step that uses a tool is another call, and it carries the earlier steps of the same turn again.

At the built-in prices the front part alone costs, per message:

| Everyday model | Read fresh | Read from the cache |
|---|---|---|
| GPT-6 Luna (OpenAI, the default) | about $0.0012 | about $0.00012 |
| Claude Haiku 4.5 (Anthropic) | about $0.012 | about $0.0012 |
| Gemini 3.1 Flash-Lite (Google) | about $0.003 | about $0.0003 |

Answers, thinking and tool steps are extra, and each web search is billed on top of tokens: about a cent on OpenAI and Claude, 1.4 cents on Gemini.

## What the cache does

The company reads a request that starts the same way as the last one at a fraction of the normal input price: a tenth for most models in the built-in table. So the front part holds only what changes rarely, and nothing volatile is in it. Dates, the sender, a shared location and memories go in the current turn, after the cached part.

Editing the family's words or the assistant's character, or changing any idea (a new one, a recorded outcome), means the next message pays the full input price again for that part of the front. On Claude the cache lasts an hour by default (`anthropic_cache_ttl`), because a family writes in bursts. OpenAI and Gemini cache a repeated start on their own, and not every repeat is a hit. Status shows the share of input that came from the cache; if it stays at zero, see [Troubleshooting](/wiki/operations/troubleshooting#costs-higher-than-expected).

## The daily limit

The [spending limit](/wiki/reference/glossary#spending-limit) is $2.00 a day unless you change it, and 0 turns it off. Before every call (a chat step, a lookup, a voice note, a photo) FamilyDB adds up what the day's recorded calls were estimated to cost, and stops asking a model once the total reaches the limit. The day ends at midnight in the family's time zone.

- **It is not the bill.** The price table can be out of date. Set a limit with the model company too.
- **It can stop slightly early.** Each call holds the most it could cost, with every input token fresh and the whole output allowance used. Holds count against other calls, not their own, so one call can still cross the limit.
- **It stops everything that asks a model.** Chat says so, lookups wait for tomorrow, and admins with a Telegram id are told. Reminders, commands and buttons ask no model and carry on.

Each kid also has a share of $0.25 a day, which counts toward the daily limit, and an optional count of messages a day, off by default. Both are checked before a message is answered, and neither tells the kid anything about money. Commands and button taps ask no model, so they cost nothing and are not counted. The settings are on [Spending](/wiki/controls/settings/spending#the-daily-limit).

## How prices are known

FamilyDB starts from a table built into this version. Once a day, at 05:17 in the family's time zone, the daily check asks each company you have a key for which models it offers, reads two public price lists (LiteLLM's and OpenRouter's), and lays what it found over the table. It takes a price when the two lists are within 5% of each other, or when only one has the model. It calls no model and sends nothing about the family. With "Check models and prices daily" off, the built-in table stands.

A model neither knows is counted at $15 in and $75 out per million tokens and 3.5 cents a search: dearer than any model in the built-in table, so the limit stops early rather than late. Status marks such a model with an asterisk. [Models and prices](/wiki/controls/status/models-and-prices) shows what the check read and what moved.

## What each kind of call is

Status and `debug cost` name each kind by what it was for. Nothing else asks a model: reminders, follow-ups, the evening plan check, nudges, commands, buttons, alerts and the daily check answer in code, and remembering something rides on the chat call.

| What for (kind) | When it runs | On by default |
|---|---|---|
| Answering the family (`chat`) | Every message that reaches a model | Yes |
| The weekend digest (`digest`) | Weekly, to the chosen chat | After an install, which sets the page's chat; off with no chat |
| Answering a message again after a failure (`retry`) | The retry job, every 5 minutes, up to 3 tries per message | Only after a failure |
| Looking ideas up (`enrich`) | One turn per idea, up to 3 searches; by default together at 21:00, up to 40 a night, or within minutes when asked for now | After an install; the program's own default is off |
| Searching for what is on (`discover`) | Inside a suggestion that asks what is on, up to 4 searches; kept 12 hours per window and topic, in memory | With lookups |
| Weighing a change in the models (`judge`) | Evenings, when a change needs weighing, within $1 a month | No |
| Checking a disputed price (`price_check`) | With the above, at most 2 a day, up to 3 searches each | No |
| Listening to voice notes (`transcribe`) | Each voice note, up to 5 minutes, before its chat call | Yes, with an OpenAI or Gemini key |
| Reading photos (`look`) | Each photo, up to four of an album, before its chat call | Yes |

A voice note or a photo pays twice: once to be written down, then as a chat message. The first part is small: at most about a tenth of a cent for a photo on GPT-6 Luna.

## What you can turn down

| Lever | Setting | Default |
|---|---|---|
| How strong a model answers chat, the digest and lookups | [`chat_level`, `digest_level`, `lookup_level`](/wiki/controls/settings/ai-model#how-strong-a-model-answers) | everyday, the cheapest |
| How hard chat and lookups think | [`effort`, `worker_effort`](/wiki/controls/settings/spending#thinking) | medium, low |
| Chat history, ideas, steps and answer length sent | [`history_limit`, `history_hours`, `prompt_idea_limit`, `agent_max_iterations`, `max_output_tokens`](/wiki/controls/settings/spending#what-one-message-may-use) | 20, 6 hours, 150, 8, 16000 |
| Web lookups and discovery | [`web_tools_enabled`](/wiki/controls/settings/lookups#looking-ideas-up) | on after an install |
| Voice notes and photos | [`voice_notes`, `photos`](/wiki/controls/settings/ai-model#voice-notes-and-photos) | on |
| The weekend digest | [`digest_chat_id`](/wiki/controls/settings/messages#weekend-ideas) (empty sends none) | the page's chat |
| The daily limit, each kid's share and count | [`daily_spend_limit`, `kid_daily_spend`, `kid_daily_messages`](/wiki/controls/settings/spending#the-daily-limit) | $2.00, $0.25, 0 |

Effort does nothing for a model that does not think, such as Claude Haiku 4.5. A stronger level is never cheaper than everyday.

## Reading the last 30 days

The Status page shows today's spend against the limit, what a usual day costs, and under "Where the money went" the calls and dollars for each kind and the cache share. It asks no model. Recent activity opens one message or lookup with every call and its cost. A row called "What the calls cost or do moved" appears when a kind of call moved by a factor of 1.5 or more against the four weeks before. See [Status](/wiki/controls/status) and [Recent activity](/wiki/controls/status/activity).

`familydb debug cost --days N` prints the same by kind and by model, with the cache share and how the input of each kind was shared out by part.

## The company's own limit

Because the daily limit is an estimate, the model company's own limit is the backstop: set a monthly limit or alert in its console. If the account runs out of credit, a row appears under Needs a look and admins are told. With a second company's key saved and the fallback on, which it is by default, the next call can go to that company, but only before the turn has changed anything. A rate limit is retried by the retry job rather than failing for good.

Developer docs: `docs/DESIGN.md`, "Cost"; `docs/AI_CALLS.md`, "The calls today" and "Choosing models"; `familydb/agent/spending.py` and `familydb/agent/providers/prices.py` (module notes).
