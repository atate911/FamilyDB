# Model companies

FamilyDB reaches Anthropic (Claude), OpenAI and Google (Gemini) through one small interface, so you can change which company does a job without changing anything else. This page says how each is reached, which does which job, how a request differs between them and what happens when one says no. The settings are on [AI model settings](/wiki/controls/settings/ai-model) and the cost is on [Cost](/wiki/operations/cost).

## One interface, three modules

Each company has one module in `src/familydb/agent/providers/`. `base.py` says what a module must do, and `anthropic.py`, `openai.py` and `gemini.py` translate to the company's own library: send a request, say whether a model exists, list the models a key may use, check a key, look at a picture and, for OpenAI and Gemini, hear a recording. Nothing outside that folder knows which company is in use. Every call goes through `agent/gateway.py`, which checks the daily limit first and records the call. A request times out after 120 seconds per attempt. The Claude and OpenAI libraries retry twice on their own, so a failing call can wait about six minutes before the spare is tried. Gemini has the same timeout and no retries set. Key checks and model lookups use 10 and 20 seconds.

What each kind of call carries is in [What leaves the house](/wiki/security/data-and-privacy#what-leaves-the-house). The instructions, family and idea list come first and are the same on every message, so the company can [cache](/wiki/reference/glossary#prompt-cache) them; the date, sender, location and remembered facts go last. FamilyDB sets `store` to false on every OpenAI Responses request (chat, lookups, photos), which asks OpenAI not to store the response. A voice note sent to OpenAI's speech endpoint is not covered.

## Which company does which job

| Job | Company | Setting |
|---|---|---|
| Chat, answering again after a failure, the weekend digest | The one you chose | `provider` (OpenAI by default) |
| Looking ideas up, searching for what is on, checking a disputed price | The lookup company | `worker_provider`; empty means `provider` |
| Weighing a change in the models (off unless `judgements` is on) | The lookup company, at `judgement_level` (best by default) | `worker_provider` |
| Voice notes | The one you chose, else the chat company if it can hear | `transcribe_provider`; Claude cannot hear, so another company with a key is asked |
| Photos | The lookup company, with its lookup model | none |

### A second company

With `provider_fallback` on (the default), another company with a key answers when the first cannot. The spare is the first of Anthropic, OpenAI and Gemini, in that order, that did not fail and has a key. It answers at the same [level](/wiki/reference/glossary#level), and the spending limit is held again at its price.

A turn moves only on its first call, before any tool has run. After that a tool may already have saved an idea or written to the calendar, and starting again elsewhere would do it twice, so the turn stays failed for the retry job (every 5 minutes, 3 times, by default). It moves when the company is busy, unreachable, out of credit, refusing the key, missing the model or has no key. It does not move for a request refused as written, which would fail the same way. A voice note or photo is one request, and the next company able to take it is tried for the same failures; neither is retried later, since the recording and picture are not kept.

## Levels and the catalog

| Level | OpenAI | Claude | Gemini |
|---|---|---|---|
| Everyday | `gpt-6-luna` | `claude-haiku-4-5` | `gemini-3.1-flash-lite` |
| Better | `gpt-6-sol` | `claude-sonnet-5` | `gemini-3.8-flash` |
| Best | `gpt-6-astra` | `claude-opus-5` | `gemini-3.1-pro-preview` |

Everyday is the model named in your settings, the company's cheapest by default. Better and best are the models you name, or this table's. A higher level never answers with a model cheaper than everyday, and a model with no known price counts as dearer than any listed one. A model the [daily check](/wiki/controls/status/models-and-prices) has found gone is replaced by a near one when that costs no more than twice as much.

## What each model is sent

| | Claude | OpenAI | Gemini |
|---|---|---|---|
| Interface | Messages (beta) | Responses | `generate_content` |
| Thinking | Adaptive thinking and an effort, except the models in `OLDER_MODELS`, Haiku 4.5 among them | A reasoning effort: all five names on GPT-6, capped at high on `gpt-5` and the o-series, none on `gpt-3`, `gpt-4` and `chatgpt-` | A thinking level (low for low effort, else high) from Gemini 3; a token budget on Gemini 1 and 2 |
| Web search (lookups only) | `web_search` and `web_fetch`; older models get basic versions | One hosted `web_search` | `google_search`; refused before sending on Gemini 1 and 2, which cannot combine it with our tools |
| Caching | Marked on the unchanging parts; an hour by default (`anthropic_cache_ttl`, `1h` or `5m`) | Automatic on a long prefix; FamilyDB sends a `prompt_cache_key`, a hash of the unchanging text | Automatic; nothing is sent |
| Refusal fallback | On the Claude models that have it (not Haiku or Sonnet), unless `ANTHROPIC_FALLBACKS` is false in `.env` | none | none |

Effort comes from [Spending](/wiki/controls/settings/spending#thinking): `effort` for chat and `worker_effort` for lookups.

## Keys

The AI model page checks a key by looking up the chat model with the company, which costs nothing. A key the company clearly refuses is not saved, but what counts as clear differs: Claude refuses only a 401, so a 403 is saved unchecked, and OpenAI and Gemini differ in detail. A key whose company has no such model is saved, with a note to choose another. A company that cannot be asked leaves the key saved unchecked, and the first message shows whether it works.

## When a company says no

Each module reads a failure into a trouble that only an admin can fix.

| The company said | Trouble | What an admin sees |
|---|---|---|
| Claude: a 400 or 402 mentioning the credit balance. OpenAI: a 429 with `insufficient_quota`. Gemini: a 429 mentioning billing, credit or prepay | credit | "<Company> is out of credit" on Status |
| A 401 or 403, or Gemini's 400 about the key | key | "<Company> refused its key" |
| A 404 naming a model | model | "A model in use is going, or has gone" |
| Any other 4xx except 429 | refused | "<Company> is refusing requests" on Status; the Telegram message waits until it has happened twice with no answer between |
| Another 429, a 5xx or no connection | none | Nothing; the spare or the retry job handles it |

Each row clears when the company next answers. For the first four rows every admin with a Telegram id is also told, again at most every 12 hours while it lasts, unless `admin_alerts` is off.

### A 400 that names part of the request

When a 400's text names a part the request carried, FamilyDB sends it again without that part, once per part, and keeps it out for that model until FamilyDB restarts.

| Company | Parts that can be left out |
|---|---|
| Claude | The refusal fallback, the newer web tools, thinking and effort |
| OpenAI | The top effort levels (tried first), reasoning settings, the prompt cache key, the cap on tool calls |
| Gemini | Switching thinking off, the thinking level, search beside our own tools |

The answer is used, and admins are told once, under "A company stopped taking part of a request". A 400 naming none of these is a refused trouble.

## Voice and photos

OpenAI hears with `gpt-4o-mini-transcribe` unless changed. Gemini hears with `gemini_transcribe_model`, else its lookup model, sent the recording. Claude hears nothing. All three look at a photo with their lookup model. Limits on size and length are on the settings page. See [Voice notes and photos](/wiki/controls/settings/ai-model#voice-notes-and-photos).

## The daily check

At 05:17 each company with a key is asked which models the key may use, and LiteLLM's and OpenRouter's public price lists are read. Neither request carries anything of the family. [Weather and maps](/wiki/boundaries/weather-and-maps#the-price-lists) says how a price is taken, and [Models and prices](/wiki/controls/status/models-and-prices) shows the result.

## Adding a company

Write one module in `src/familydb/agent/providers/` that does what `base.py` asks, add its name to `NAMES` in `__init__.py`, and give it a lineup in `catalog.py` and prices in `prices.py`, which a test holds to what the modules send. List its `PARTS`, map its failures to `AgentError.trouble`, and add its key and model settings to `config.py`.

Developer docs: `src/familydb/agent/providers/` (module notes, `parts.py`), `src/familydb/agent/gateway.py`, `src/familydb/agent/loop.py` (`worth_switching`), `src/familydb/model_watch.py`, `src/familydb/alerts.py`, `docs/AI_CALLS.md`, and `docs/DESIGN.md`, "Decisions" (Model vendor, Keeping up with models and prices).
