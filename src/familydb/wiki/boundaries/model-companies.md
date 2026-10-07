# Model companies

FamilyDB reaches Anthropic (Claude), OpenAI and Google (Gemini) through one small interface, so you can change which company does a job without changing anything else. This page says how each is reached, which company does which job, what a request looks like for each, and what happens when one says no. The settings are on [AI model settings](/wiki/controls/settings/ai-model), and what the calls cost is on [Cost](/wiki/operations/cost).

## One interface, three modules

Each company has one module in `src/familydb/agent/providers/`. `base.py` defines what a module must do, and `anthropic.py`, `openai.py` and `gemini.py` translate between that and the company's own library. A module can send a request, say whether a model name exists, list the models a key may use, check a key, and look at a picture. The OpenAI and Gemini modules can also hear a recording.

Nothing outside that folder knows which company is in use. Every call goes through `agent/gateway.py`, which checks the daily limit first and records the call under its kind. Each request times out after 120 seconds, and the Claude and OpenAI libraries retry twice on their own before FamilyDB sees a failure.

What each kind of call carries is in [What leaves the house](/wiki/security/data-and-privacy#what-leaves-the-house). The request is built in labelled parts: the instructions, the family and the idea list come first and are the same on every message, so the company can [cache](/wiki/reference/glossary#prompt-cache) them. The date, the sender, a shared location and remembered facts go last. FamilyDB sets `store` to false on every OpenAI request, which asks OpenAI not to store the response.

## Which company does which job

| Job | Company | Setting |
|---|---|---|
| Chat, answering again after a failure, the weekend digest | The one you chose | `provider` (OpenAI by default) |
| Looking ideas up, searching for what is on, weighing a change | The lookup company | `worker_provider`; empty means `provider` |
| Voice notes | The one you chose, else the chat company if it can hear | `transcribe_provider`; Claude cannot hear, so another company with a key is asked |
| Photos | The lookup company, with its lookup model | none |

### A second company

With `provider_fallback` on (the default), a company with a key answers when the first cannot. The spare is the first of Anthropic, OpenAI and Gemini, in that order, that is not the one that failed and has a key. It answers at the same [level](/wiki/reference/glossary#level), and the spending limit is held again at its price.

A turn moves only on its first call, before any tool has run. After that a tool may already have saved an idea or written to the calendar, and starting again elsewhere would do it twice, so the turn stays failed and the retry job asks again later (every 5 minutes, 3 times, by default). It moves for a company that is busy, unreachable, out of credit, refusing the key, missing the model or has no key. It does not move for a request the company refused as written, because that would fail the same way. If the spare also fails, the first company's failure stands.

A voice note or photo is one request, and the next company able to take it is tried for the same failures. The recording and the picture are not kept, so neither is retried later.

## Levels and the catalog

Each company's models are known by [level](/wiki/reference/glossary#level), in `catalog.py`.

| Level | OpenAI | Claude | Gemini |
|---|---|---|---|
| Everyday | `gpt-6-luna` | `claude-haiku-4-5` | `gemini-3.1-flash-lite` |
| Better | `gpt-6-sol` | `claude-sonnet-5` | `gemini-3.8-flash` |
| Best | `gpt-6-astra` | `claude-opus-5` | `gemini-3.1-pro-preview` |

Everyday is the model named in your settings, the company's cheapest by default. Better and best are the models you name for that company, or this table's. A higher level never answers with a model cheaper than everyday. A model with no known price counts as dearer than any listed, so it is not chosen as the cheaper one. A model the [daily check](/wiki/controls/status/models-and-prices) has found gone is replaced by a near one when that costs no more than twice as much.

## What each model is sent

| | Claude | OpenAI | Gemini |
|---|---|---|---|
| Interface | Messages | Responses | `generate_content` |
| Thinking | Adaptive thinking and an effort, except on the models in `OLDER_MODELS`, which includes Haiku 4.5 | A reasoning effort. All five effort names on GPT-6, capped at high on `gpt-5` and the o-series, none on `gpt-3`, `gpt-4` and `chatgpt-` models | A thinking level (low for low effort, else high) on Gemini 3 and later; a token budget on Gemini 1 and 2 |
| Our tools | Strict schemas | Strict schemas, with optional parameters made nullable | Function declarations |
| Web search (lookups only) | `web_search` and `web_fetch`; older models get the basic versions | One hosted `web_search` | `google_search`; Gemini 1 and 2 are refused before sending, since they cannot combine it with our tools |
| Caching | Marked on the unchanging parts; an hour by default (`anthropic_cache_ttl`, `1h` or `5m`) | Automatic on a long prefix; FamilyDB sends a `prompt_cache_key`, a hash of the unchanging text | Automatic; nothing is sent |
| Refusal fallback | On the strongest models, unless `ANTHROPIC_FALLBACKS` is false in `.env` | none | none |

Effort comes from the [Spending](/wiki/controls/settings/spending#thinking) page: `effort` for chat and `worker_effort` for lookups. Each module names the older models rather than the current ones, so a model released later is sent the current shape.

## Keys

The AI model page checks a key before keeping it by looking up the chat model with the company, which costs nothing.

| Answer | What happens |
|---|---|
| Works | Saved, and that company answers |
| Refused | Not saved. Google answers a bad key with a 400 or 401, and FamilyDB reads the words |
| No such model | Saved, with a note to choose another model |
| Could not be asked | Saved unchecked; the first message shows whether it works |

A model name typed into "Another model" is checked the same way, and refused only on a definite "no such model".

## When a company says no

Each module reads a failure into a trouble that only an admin can fix.

| The company said | Trouble | What an admin sees |
|---|---|---|
| Claude: a 400 or 402 mentioning the credit balance. OpenAI: a 429 with `insufficient_quota`. Gemini: a 429 mentioning billing, credit or prepay | credit | "<Company> is out of credit" on Status, and a Telegram message |
| A 401 or 403, or Gemini's 400 about the key | key | "<Company> refused its key" |
| A 404 naming a model | model | "A model in use is going, or has gone" |
| Any other 4xx except 429 | refused | "<Company> is refusing requests", once it has happened twice with no answer between |
| A 429 that is not about credit, a 5xx, or no connection | none | Nothing; the spare or the retry job handles it |

Each row clears when the company next answers. Every admin with a Telegram id is told, and again at most every 12 hours while it lasts, unless `admin_alerts` is off. With judgements on, a refusal nobody can read is put to a stronger model at once.

### A 400 that names part of the request

A 400 is not billed. When its text names a part the request carried, FamilyDB sends the request again without that part, once per part, and keeps it out for that model until FamilyDB restarts.

| Company | Parts that can be left out |
|---|---|
| Claude | The refusal fallback, the newer web tools, thinking and effort |
| OpenAI | The top effort levels (tried first), reasoning settings, the prompt cache key, the cap on tool calls |
| Gemini | Switching thinking off, the thinking level, search beside our own tools |

The answer is used, and admins are told once under "A company stopped taking part of a request" that the rest works without it. A 400 naming none of these is a refused trouble.

## Voice and photos

| | Claude | OpenAI | Gemini |
|---|---|---|---|
| Hears a voice note | No | `gpt-4o-mini-transcribe` unless changed, through the speech-to-text endpoint | `gemini_transcribe_model`, else its lookup model, sent the recording |
| Looks at a photo | Yes | Yes | Yes |

A voice note over `voice_max_minutes` (5 by default) or 20 MB is not heard. A photo over 3.9 MB is not looked at, and of an album the first four are. See [Voice notes and photos](/wiki/controls/settings/ai-model#voice-notes-and-photos).

## The daily check

At 05:17 each company with a key is asked which models the key may use, and two public price lists are read: LiteLLM's file on GitHub and OpenRouter's model list. Neither request carries anything of the family. A price is taken when the two agree within 5% or only one has it, and held when it jumps more than fivefold. [Weather and maps](/wiki/boundaries/weather-and-maps#the-price-lists) says more, and [Models and prices](/wiki/controls/status/models-and-prices) shows the result.

## Adding a company

Write one module in `src/familydb/agent/providers/` that does what `base.py` asks, and add its name to `NAMES` in `__init__.py`. Give it a lineup in `catalog.py` and prices in `prices.py`, which a test holds to what the modules send, and list its `PARTS`. Map its failures to `AgentError.trouble`. Its key and model settings go in `config.py` and on the AI model page.

Developer docs: `src/familydb/agent/providers/` (module notes, `parts.py`), `src/familydb/agent/gateway.py`, `src/familydb/agent/loop.py` (`worth_switching`), `src/familydb/model_watch.py`, `src/familydb/alerts.py`, `docs/AI_CALLS.md`, and `docs/DESIGN.md`, "Decisions" (Model vendor, Keeping up with models and prices).
