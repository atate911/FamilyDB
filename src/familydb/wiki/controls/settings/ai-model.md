# AI model settings

Which company answers, with which model, and its key. Everything the family writes goes to
the company that answers, and you pay that company for what it uses, so this page is also the
main lever on cost.

## Who answers

Three companies are supported: OpenAI, Anthropic (Claude) and Google (Gemini). The default is
OpenAI, with `gpt-6-luna`, chosen as the cheapest model that is good enough. A company can be
chosen only with a key.

| Setting | Default | What it does |
|---|---|---|
| Company that answers (`provider`) | OpenAI | Which company reads each message and writes the answer. Choosing a company on the page needs its key, and saving a key makes that company the one that answers |

### Keys

Paste the company's key into its form. It is checked with the company (a free request) before it is
kept, and saving it makes that company the one that answers. A key the company refuses is not saved. If the
company cannot be reached just now, the key is saved unchecked and the first message shows whether it works. A key you have
saved is never shown again in a form: to see it, use [See a key](/wiki/controls/settings/sign-in#see-a-key),
which asks for your password first. The "Every company's key" fold at the bottom saves or removes
a second company's key without switching to it; keys saved there are not checked with the company.

A key saved here is stored in the database as plain text, so **it is in every
[backup](/wiki/operations/backup-and-restore)**. A key kept in `.env` is not. The Status page says
which key each company uses and where it came from.

## How strong a model answers

Three strengths, whichever company: **everyday** (the company's own model, its cheapest by
default), **better** and **best**. A stronger level is never cheaper than everyday.

| Setting | Default | What it does |
|---|---|---|
| Answering the family (`chat_level`) | everyday | The strength used for chat |
| The weekend digest (`digest_level`) | everyday | Once a week, so a stronger model adds little to the month |
| Looking things up (`lookup_level`) | everyday | Filling in an idea and finding what is on; everyday is usually plenty |

### Which model is everyday

| Setting | Default |
|---|---|
| OpenAI everyday chat model (`openai_model`) | `gpt-6-luna` |
| OpenAI everyday lookup model (`openai_worker_model`) | `gpt-6-luna` |
| Claude everyday chat model (`anthropic_model`) | `claude-haiku-4-5` |
| Claude everyday lookup model (`worker_model`) | `claude-haiku-4-5` |
| Gemini everyday chat model (`gemini_model`) | `gemini-3.1-flash-lite` |
| Gemini everyday lookup model (`gemini_worker_model`) | `gemini-3.1-flash-lite` |

The page shows the models for the company in use, least expensive first, with its price per
million tokens read and written; "Another model" accepts any name the company offers, and a name
the company says it does not have is refused on save; if the company cannot be asked, the name is accepted. The other companies' are under "Other models".
A model's price comes from the daily check below; a model it does not know is counted dearer than any
listed, so the daily limit errs on the safe side.

#### Better and best models

Folded away, under "Better and best models". Empty uses the ones this version knows (shown as the
default). A judgement (below) may suggest newer ones. These are `openai_better_model`,
`openai_best_model`, `anthropic_better_model`, `anthropic_best_model`, `gemini_better_model` and
`gemini_best_model`.

## A second company

| Setting | Default | What it does |
|---|---|---|
| Company for lookups (`worker_provider`) | the same company | Who looks ideas up on the web; needs a key |
| Ask another company when the first cannot (`provider_fallback`) | on | When the first is down, out of credit or busy, a company with a key answers instead, at the same level. Only before anything has been done, so nothing happens twice |

## Keeping up with the companies

| Setting | Default | What it does |
|---|---|---|
| Check models and prices daily (`model_watch`) | on | Once a day, at 05:17, it asks each company you have a key for which models the key can use, and reads two public price lists (LiteLLM's and OpenRouter's), taking a price when they agree. New models then appear here, prices are counted, and admins are told on Telegram when a model in use is going or its price moves. A price is taken when the two lists are within 5% of each other. No model call, and nothing about the family is sent. Off, the prices built into this version are used and nobody is told |

If a model in use is withdrawn, the nearest model costing no more than twice as much answers in its place until you
choose another, with no setting changed and whether or not judgements are on, and admins are told if alerts are on.
The check runs at 05:17 family time.

## Asking a stronger model to weigh a change

Some changes need judgement and not a rule: which model should replace one that is going, what
a refusal nobody can read means, which new models belong at which level, what a price the lists
disagree on really is. With this on, the questions that come up are asked together, by default after the evening's lookup time (at
once if lookups are set to "as soon as added"), in one call, plus at most two price checks that search the web;
only a refusal is asked at once. It is sent model names,
prices and error messages, never the family's messages.

| Setting | Default | What it does |
|---|---|---|
| Ask a stronger model when a change needs judgement (`judgements`) | off | A few cents each time, and nothing on a day with no question |
| How strong a model weighs it (`judgement_level`) | best | Rare questions, where a better answer is worth a cent more |
| What it may do by itself (`judgement_acts`) | within cost | "Within cost" lets it put in a model that costs no more than about 10% over the one it replaces, tells admins, and gives a way to put the old one back; anything dearer waits for an admin. "Suggest" only suggests |
| Most to spend on it in a month (`judgement_budget`) | US$1 | Counted within the daily limit as well, over the calendar month in the family's time zone. It stops when the month's spend plus 5 cents would pass the budget, so a budget under about 5 cents asks nothing. 0 asks nothing. Between 0 and 50 |

Whatever it chooses must be one of the options it was given, and a price is accepted only when it
matches a price list. [Status](/wiki/controls) lists each question, answer and outcome, with buttons to put a
change in or back.

## Voice notes and photos

| Setting | Default | What it does |
|---|---|---|
| Listen to voice notes (`voice_notes`) | on | Voice notes sent on Telegram are written down (by OpenAI's speech model, or by Gemini's ordinary model) and answered as if typed. Off asks the family to type. Claude cannot hear them, so this needs an OpenAI or Gemini key |
| Longest voice note heard (`voice_max_minutes`) | 5 | A longer one is not heard at all, since every minute is paid for. Between 1 and 30 |
| Who hears them (`transcribe_provider`) | the chat company if it can | OpenAI or Gemini; otherwise another company with a key |
| OpenAI hearing model (`openai_transcribe_model`) | `gpt-4o-mini-transcribe` | |
| Gemini hearing model (`gemini_transcribe_model`) | Gemini's lookup model | Empty uses it |
| Look at photos (`photos`) | on | A photo sent on Telegram (a poster, a menu, a ticket) is read by the lookup model, which writes down what it shows. The photo goes to that company, costs a fraction of a cent depending on the company, and is not kept. Of an album, only the first few photos are looked at. In a group, a photo is looked at only when it is sent to the bot, by a mention in its caption or a reply |

The recording of a voice note and a photo are never kept; only the words are. See
[What it touches](/wiki/boundaries#what-leaves-the-house).

Developer docs: `docs/AI_CALLS.md` and `docs/DESIGN.md` ("Model vendor", "Keeping up with models and
prices", "Judgment on changes in the models").
