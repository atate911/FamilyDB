# AI model

The AI model card sets which model company answers, with which model, and its key. Everything the family writes goes to the company that answers, and you pay that company for what it uses, so this card is also the main lever on cost.

## Who answers

Three model companies are supported: OpenAI, Anthropic (Claude) and Google (Gemini). The default is OpenAI with `gpt-6-luna`, the cheapest model that is good enough. A company can be chosen only with a key.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Company that answers (`provider`) | OpenAI | Reads each message and writes the answer. Saving a key makes that company the one that answers. | OpenAI, Anthropic or Gemini |

### Keys

Paste the company's key into its form. FamilyDB checks it with the company (a free request) before keeping it, and saving it makes that company the one that answers. A key the company refuses is not saved. If the company cannot be reached, the key is saved unchecked and the first message shows whether it works.

A saved key is never shown again in a form; to see it, use [See a key](/wiki/controls/settings/sign-in#see-a-key). The "Every company's key" fold at the bottom saves or removes a second company's key without switching to it; keys saved there are not checked.

> **A key saved here is stored in the database as plain text, so it is in every [backup](/wiki/operations/backup-and-restore).** A key kept in `.env` is not. The Technical details fold on [Status](/wiki/controls/status) says which key each company uses and where it came from.

## How strong a model answers

There are three strengths, whichever company: **everyday** (the company's own model, its cheapest by default), **better** and **best**. A stronger level is never cheaper than everyday.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Answering the family (`chat_level`) | everyday | The strength for chat. | everyday, better or best |
| The weekend digest (`digest_level`) | everyday | The strength for the weekend ideas. | everyday, better or best |
| Looking things up (`lookup_level`) | everyday | The strength for filling in an idea and finding what is on. | everyday, better or best |

### Which model is everyday

| Label (`key`) | Default |
|---|---|
| OpenAI everyday chat model (`openai_model`) | `gpt-6-luna` |
| OpenAI everyday lookup model (`openai_worker_model`) | `gpt-6-luna` |
| Claude everyday chat model (`anthropic_model`) | `claude-haiku-4-5` |
| Claude everyday lookup model (`worker_model`) | `claude-haiku-4-5` |
| Gemini everyday chat model (`gemini_model`) | `gemini-3.1-flash-lite` |
| Gemini everyday lookup model (`gemini_worker_model`) | `gemini-3.1-flash-lite` |

The card shows the models for the company in use, least expensive first, with the price per million [tokens](/wiki/reference/glossary#token) read and written; the other companies' are under "Other models". "Another model" accepts any name the company offers: FamilyDB refuses a name the company says it does not have, and accepts any name when the company cannot be asked. Prices come from the [daily check](/wiki/controls/status/models-and-prices#what-the-daily-check-does); a model it does not know is counted dearer than any listed.

### Better and best models

Folded away on the card, one box for each company and level (`anthropic_better_model`, `anthropic_best_model`, `openai_better_model`, `openai_best_model`, `gemini_better_model`, `gemini_best_model`). Empty uses the ones this version knows; a judgment (below) may suggest newer ones.

## A second company

With a key for another company as well, FamilyDB can use it for lookups, or let it answer when the first cannot. The **Backup** row on Status is this second company, not your database backup.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Company for lookups (`worker_provider`) | the same company | Looks ideas up on the web. | A company with a key |
| Ask another company when the first cannot (`provider_fallback`) | on | When the first is down, out of credit or busy, a company with a key answers instead, at the same level, and only before anything has been done, so nothing happens twice. | on or off |

## Keeping up with the companies

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Check models and prices daily (`model_watch`) | on | Runs the [daily check](/wiki/controls/status/models-and-prices#what-the-daily-check-does) of which models each company offers and what they cost. Off, the prices built into this version are used and nobody is told when a model goes. | on or off |

## Asking a stronger model to weigh a change

Some changes need judgment and not a rule: which model replaces one that is going, what a refusal nobody can read means, which new models belong at which level, what a disputed price really is. With this on, FamilyDB asks the day's questions together after the evening's lookup time, in one call, plus at most two price checks that search the web; a refusal is asked at once. The call carries model names, prices and error messages, never the family's messages.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Ask a stronger model when a change needs judgment (`judgements`) | off | Asks the questions that come up. A few cents each time; nothing on a day with no question. | on or off |
| How strong a model weighs it (`judgement_level`) | best | The strength for these rare questions. | everyday, better or best |
| What it may do by itself (`judgement_acts`) | within cost | **Put in a model at most about 10% dearer** (`within_cost`) saves a chosen model costing no more than about 10% over the one it replaces, tells admins, and lets you put the old one back. **Only suggest** (`suggest`) puts nothing in. | `within_cost` or `suggest` |
| Most to spend on it in a month (`judgement_budget`) | US$1 | Counted within the daily limit too, over the calendar month in the family's time zone. A budget under about 5 cents, or 0, asks nothing. | 0 to 50 |

A judgment never changes a setting by itself except under "within cost"; a dearer model waits for an admin to press **Put these in** on [Models and prices](/wiki/controls/status/models-and-prices#put-these-in-and-put-back). A judgment must pick one of the options it was given, and a price is accepted only when it matches a price list.

## Voice notes and photos

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Listen to voice notes (`voice_notes`) | on | Writes down voice notes sent on Telegram and answers them as if typed. Off asks the family to type. | on or off |
| Longest voice note heard (`voice_max_minutes`) | 5 | A longer one is not heard at all, since every minute is paid for. | 1 to 30 |
| Who hears them (`transcribe_provider`) | empty | Empty uses the chat company when it can hear, otherwise another company with a key. | OpenAI or Gemini |
| OpenAI hearing model (`openai_transcribe_model`) | `gpt-4o-mini-transcribe` | Writes a voice note down when OpenAI hears it. | A model name |
| Gemini hearing model (`gemini_transcribe_model`) | Gemini's lookup model | The same for Gemini. Empty uses its lookup model. | A model name |
| Look at photos (`photos`) | on | The lookup model reads a photo sent on Telegram (a poster, a menu, a ticket) and writes down what it shows. | on or off |

Claude cannot hear voice notes, so they need an OpenAI or Gemini key. A voice note goes to the company that hears it; a photo goes to the company that looks things up, costs about a tenth of a cent, and is not kept. Of an album, only the first 4 photos are looked at. In a group, a photo is looked at only when it is sent to the bot, by a mention in its caption or a reply. Neither recording is kept; only the words are. What leaves the house is on [What leaves the house](/wiki/security/what-leaves-the-house).
