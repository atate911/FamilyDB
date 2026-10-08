# Model companies

FamilyDB reaches Anthropic (Claude), OpenAI and Google (Gemini) through one small interface, so you can change which model company does a job without changing anything else. The settings are on [AI model](/wiki/controls/settings/ai-model) and the cost is on [Cost](/wiki/operations/cost).

## One interface, three modules

Each company has its own module that translates FamilyDB's request into the company's own library and reads its failures into a few plain troubles. Nothing outside those modules knows which company is in use. Every call goes through the [gateway](/wiki/reference/glossary#gateway), which checks the daily limit first and records the call.

A request times out after 120 seconds per attempt. The Claude and OpenAI libraries retry twice on their own, so a failing call can wait about 6 minutes before the second company is tried. Gemini has the same timeout and no retries. Key checks and model lookups use 10 and 20 seconds.

What each kind of call carries is on [What leaves the house](/wiki/security/what-leaves-the-house). The instructions, family and idea list come first and are the same on every message, so the company can [cache](/wiki/reference/glossary#prompt-cache) them; the date, sender, location and remembered facts go last. FamilyDB asks OpenAI not to store its responses (chat, lookups and photos). A voice note sent to OpenAI's speech service is not covered.

## Which company does which job

Each of eight things the assistant does has a company and a model of its own, chosen on the rows of [AI model](/wiki/controls/settings/ai-model#what-does-what). With nothing chosen a row answers as the older settings say, shown in the table.

| Job (row) | When nothing is chosen | Older setting it falls back to |
|---|---|---|
| Chat, answering again after a failure (**Answering the family**) | The company you chose at setup, OpenAI by default | `provider`, `chat_level` |
| The weekend ideas (**The weekend digest**) | The same model as chat while the strengths agree | `digest_level` |
| Choosing what to suggest (**Choosing suggestions**) | The chat company, at best, while choosing is on | `choosing`, `choose_level` |
| Looking ideas up, checking a disputed price (**Looking things up**) | The lookup company | `worker_provider` (empty means `provider`), `lookup_level` |
| Searching for what is on near home (its row, under the family's own name for it) | The same as looking things up | |
| Voice notes (**Voice notes**) | The chat company if it can hear, else another with a key | `transcribe_provider`, `voice_notes`; Claude cannot hear |
| Photos (**Photos**) | The same as looking things up | `photos` |
| Weighing a change in the models (**Weighing changes**) | Off until a model is chosen | `judgements`, `judgement_level` |

## A second company

A second company answers when the first cannot: the first of Anthropic, OpenAI and Gemini (then any [added company](/wiki/controls/settings/ai-model#other-companies), in the order added), in that order, that is not the one that failed, has a key, is let to answer and may stand in. Each company's **May stand in** is on [AI model](/wiki/controls/settings/ai-model#companies); where a company has not said, `provider_fallback` (on by default) says for the three built in. It answers at the same [level](/wiki/reference/glossary#level) as the model chosen (everyday for one the lineup has no place for), and the spending limit is reserved again at its price. A company over its monthly limit is passed over the same way.

A turn moves only on its first call, before any tool has run. After that a tool may already have saved an idea or written to the calendar, and starting again elsewhere would do it twice, so the turn stays failed for the retry job. It moves when the first company is busy, unreachable, out of credit, refusing the key or missing the model, or has no key. It does not move for a request refused as written, which would fail the same way. A voice note or photo is one request, and the next company able to take it is tried for the same failures. Neither is retried later, since the recording and picture are not kept.

## Levels and the catalog

| Level | OpenAI | Claude | Gemini |
|---|---|---|---|
| Everyday | `gpt-6-luna` | `claude-haiku-4-5` | `gemini-3.1-flash-lite` |
| Better | `gpt-6-sol` | `claude-sonnet-5` | `gemini-3.8-flash` |
| Best | `gpt-6-astra` | `claude-opus-5` | `gemini-3.1-pro-preview` |

Everyday is the model named in your settings, the company's cheapest by default. Better and best are the models you name, or this table's. A higher level never answers with a model cheaper than everyday, and a model with no known price counts as dearer than any listed one. A model the [daily check](/wiki/controls/status/models-and-prices#what-the-daily-check-does) has found gone is replaced by a near one when that costs no more than twice as much.

How a request is shaped for each model (thinking, web search, caching) depends on the model's name and is developer detail. The thinking effort comes from [Spending](/wiki/controls/settings/spending#thinking): `effort` for chat and `worker_effort` for lookups.

## Keys

The AI model page checks a key by looking up the chat model with the company, which costs nothing. A key the company clearly refuses is not saved, but what counts as clear differs: Claude refuses only a 401, so a 403 is saved unchecked, and OpenAI and Gemini differ in detail. A key whose company has no such model is saved, with a note to choose another. A company that cannot be asked leaves the key saved unchecked, and the first message shows whether it works.

## When a company says no

Each module reads a failure into a trouble that only an admin can fix.

| The company said | Trouble | What an admin sees |
|---|---|---|
| Claude: a 400 or 402 mentioning the credit balance. OpenAI: a 429 with `insufficient_quota`. Gemini: a 429 mentioning billing, credit or prepay | credit | `<Company> is out of credit` on Status |
| A 401 or 403, or Gemini's 400 about the key | key | `<Company> refused its key` |
| A 404 naming a model | model | `A model in use is going, or has gone` |
| Any other 4xx except 429 | refused | `<Company> is refusing requests` on Status; the Telegram message waits until it has happened twice with no answer between |
| Another 429, a 5xx or no connection | none | Nothing; the second company or the retry job handles it |

Each row clears when the company next answers. For the first four rows every admin with a Telegram id is also told ([When something needs fixing](/wiki/controls/settings/messages#when-something-needs-fixing)).

When a 400's text names a part of the request that FamilyDB sent (a thinking setting, a newer web tool, the prompt cache key), FamilyDB sends the request again without that part, once per part, and keeps it out for that model until FamilyDB restarts. The answer is used, and admins are told once under `A company stopped taking part of a request`. A 400 naming none of these is a refused trouble.

## Voice notes and photos

OpenAI hears with `gpt-4o-mini-transcribe` unless you choose another model on the **Voice notes** row (or set `openai_transcribe_model`). Gemini hears with `gemini_transcribe_model`, else its lookup model. Claude hears nothing. All three look at a photo with the model chosen on the **Photos** row, by default their lookup model. The limits on size and length are on [AI model](/wiki/controls/settings/ai-model#voice-notes-and-photos).

## The daily check

Each day at 05:17 FamilyDB asks every company with a key which models the key may use, and reads two public price lists. Neither request carries anything of the family. [Models and prices](/wiki/controls/status/models-and-prices#what-the-daily-check-does) says what the check does with them, and [Weather, maps and price lists](/wiki/boundaries/weather-and-maps#the-price-lists) says where the lists come from.

A company beyond these three, such as OpenRouter, is added on the AI model page ([Other companies](/wiki/controls/settings/ai-model#other-companies)) and spoken to by one adapter for the OpenAI chat protocol. It cannot search the web, hear or look at photos.

Developer docs: src/familydb/agent/providers/, src/familydb/agent/gateway.py, src/familydb/agent/loop.py, src/familydb/model_watch.py, src/familydb/alerts.py; docs/AI_CALLS.md; docs/DESIGN.md, "Decisions"; CLAUDE.md, "Layout".
