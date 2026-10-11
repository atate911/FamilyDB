# AI model

The AI model page says which model does what, what each would cost, and who stands in when one cannot. Everything the family writes goes to a model company, and you pay that company for what it uses, so this page is also the main lever on cost.

The top of the page has a card for each company, with what it answers now and costs, and the cost of the last 30 days as a daily chart. Under it, one row for each thing the assistant does. A row opens for its detail; the settings at the bottom are folded away.

Nothing here is a model call. Every figure is the last 30 days of calls, priced again at each model you could choose, so a change shows what it would have cost before you save it. They are estimates, never a bill. A use with no calls yet is priced at a typical month's, and says so.

## What does what

There are eight rows. Each has a **company** dropdown and a **model** dropdown, and the month's cost beside them; a changed row also shows the difference.

| Row | What it covers | When nothing is chosen |
|---|---|---|
| **Answering the family** | Each message, and answering it again after a failure | The company in `provider` at everyday: OpenAI with `gpt-6-luna` |
| **The weekend digest** | The weekly ideas | The same model as chat, for as long as the two strengths agree |
| **Choosing suggestions** | The stronger model that [picks what to suggest](#choosing-the-suggestions) | Best, on the company that answers the chat; off while `choosing` is off |
| **Looking things up** | Filling in an idea, finding what is on, a disputed price | Everyday on the lookup company |
| **What is on near home** (under the family's own name for it) | The weekly search for what is on near home | The same as looking things up |
| **Voice notes** | Writing a [voice note](#voice-notes-and-photos) down | OpenAI's `gpt-4o-mini-transcribe` |
| **Photos** | Reading a poster, a menu or a ticket | The same as looking things up |
| **Weighing changes** | A [judgment](#asking-a-stronger-model-to-weigh-a-change) about a model that is going or a price that moved | Off |

How a row's choice reads:

- **A company and a model.** The company dropdown also offers **Same as chat** (or lookups) where a row can follow another, and **Off** where a row can be off. Changing the company keeps the strength: Luna becomes Haiku at Anthropic. **Other…** takes any model name the company offers, counted at more than any listed model until the [daily check](/wiki/controls/status/models-and-prices#what-the-daily-check-does) knows its price; a name the company says it does not have is refused.
- **The default** is marked on the model it names ("GPT-6 Luna · default") when another is chosen, and **Use default** inside the open row puts it back. A row left at its default goes on following whatever it follows: Choosing suggestions moves with the chat's company, the digest with the chat. Only a choice that differs from the default is stored.
- **A company that cannot answer** (no key, or not let to) can still be chosen, ahead of a key; the row says who answers instead until it can, or that nothing can.
- **Choosing suggestions on another company than the chat's** sends the family's words, memories and ratings there as well. The row says so, but the decision is yours.

Open a row for its default and a line on what a dearer model would cost, what it sees and where it goes, **Thinking** (how long the model may think; empty uses the one on [Spending](/wiki/controls/settings/spending#thinking)), **If it cannot answer** (who stands in), a monthly cap where the use has one, a chart of its cost by day, **Compare models** (every model with its price, a month's cost and the difference from now; the lineup first, the rest one press away), and the calls it covers.

Two conveniences need the page's script: the **Presets** dropdown (thrifty, balanced, quality first) and each company's **Use for everything**, which fill the table at the same strength wherever the company can do the work; nothing saves until **Save**. Without scripts each row is one dropdown of every model grouped by company, a model typed in goes in the box under the row, and costs are the saved ones, shown after **Save**.

The **Save** bar stays in view. It says what is unsaved ("Answering the family → Claude Haiku 4.5 · 2 more follow") and **Reset** discards it.

### Settings an older page drew

Earlier versions drew a box for each of these. They are read from `.env` as the choice a row falls back to when nothing is chosen for it on this page (so an install that never uses the page behaves as its `.env` says), and what an older version stored became this page's choices once, on upgrade. They are not drawn, and the page never stores them.

| `key` | What it was |
|---|---|
| `provider` | The company that answers. Saving a key in setup, or pressing **Answer with** on an added company, still sets it |
| `worker_provider` | The company for lookups |
| `provider_fallback` | Ask another company when the first cannot. Each company's own **May stand in** now says it, and when one has not said, this decides |
| `chat_level`, `digest_level`, `lookup_level` | The strength for chat, the digest and lookups |
| `judgements`, `judgement_level` | Whether to weigh a change, and how strongly |
| `choosing`, `choose_level` | Whether to choose suggestions, and how strongly |
| `picks` | Whether a few picks are kept ready on Now under **What about…**, worked out by code every few hours from the family's own ideas and what is on near home: never a model call |
| `voice_notes`, `transcribe_provider`, `openai_transcribe_model`, `gemini_transcribe_model` | Whether voice notes are heard, and by whom |
| `photos` | Whether photos are looked at |

## Companies

Each company's card says what it answers now ("3 of 8 · $4.31/mo"), or why it cannot ("no key", "off"). **Settings** opens its panel:

| Setting | What it does |
|---|---|
| Let it answer | Off, the company is never asked, and a row chosen to it is answered by a stand-in. |
| May stand in when another company cannot | On by default for the companies you have a key for. When the chosen company is down, out of credit, busy, not let to answer or over its limit, the first other company that has a key, is let to answer and may stand in answers instead, at the same strength as the model chosen (everyday for a model off the lineup), and only before anything has been done on that turn, so nothing happens twice. |
| Most to spend a month | Counted from this calendar month's calls to the company, in the family's time zone. Once it is reached the company is not asked again until the month turns, and a stand-in answers; 0 asks it nothing. Empty is no limit. Counted within the [daily limit](/wiki/controls/settings/spending#the-daily-limit) as well. |
| Use for everything | Fills the table with this company's models at the same strength, wherever it can do the row; a row it cannot do stays as it was. |
| Key | **Check** asks the company whether its key works, a free request that changes nothing. **Replace** and **Remove** are in [Keys](#keys). |

The companies you can pick are the three built in (OpenAI, Anthropic and Google) and any [other company](#other-companies) you have added. A company without hosted web search is not offered for the lookup rows; one that cannot hear or read pictures is not offered for those.

## Keys

Paste a company's key into **Every company's key** at the bottom of the page. A saved key is never shown again in a form; to see it, use [See a key](/wiki/controls/settings/sign-in#see-a-key). **Check** on the company's card asks the company whether the key works, which costs nothing. A key is also checked with its company before it is kept, here as in setup's model step, and one the company clearly refuses is not saved; one it cannot be asked about is kept, and **Check** or the first message shows whether it works. Setup's model step makes that company the one that answers; the keys saved here do not change who answers.

> **A key saved here is stored in the database as plain text, so it is in every [backup](/wiki/operations/backup-and-restore).** A key kept in `.env` is not. The Technical details fold on [Status](/wiki/controls/status) says which key each company uses and where it came from.

## Everyday, better and best

Folded under **More settings**. Every company has a lineup of three: **everyday** (its cheapest model unless you choose another), **better** and **best**; a stronger level is never cheaper than everyday. The lineup is what a stand-in answers with at the strength of the model it replaces, what **Presets** and **Use for everything** fill from, and what changing a row's company keeps.

| Label (`key`) | Default |
|---|---|
| OpenAI everyday chat model (`openai_model`) | `gpt-6-luna` |
| OpenAI everyday lookup model (`openai_worker_model`) | `gpt-6-luna` |
| Claude everyday chat model (`anthropic_model`) | `claude-haiku-4-5` |
| Claude everyday lookup model (`worker_model`) | `claude-haiku-4-5` |
| Gemini everyday chat model (`gemini_model`) | `gemini-3.1-flash-lite` |
| Gemini everyday lookup model (`gemini_worker_model`) | `gemini-3.1-flash-lite` |

Better and best are `anthropic_better_model`, `anthropic_best_model`, `openai_better_model`, `openai_best_model`, `gemini_better_model` and `gemini_best_model`. Empty uses the ones this version knows; a judgment (below) may suggest newer ones. A name a company says it does not have is refused; any name is accepted when the company cannot be asked. A model the lineup has no place for can still be chosen for a row with **Other…**.

## Keeping up with the companies

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Check models and prices daily (`model_watch`) | on | Runs the [daily check](/wiki/controls/status/models-and-prices#what-the-daily-check-does) of which models each company offers and what they cost. Off, the prices built into this version are used and nobody is told when a model goes. | on or off |

The fold says when the check last ran and what it found in the last week.

## Other companies

Any service that speaks the OpenAI chat protocol can answer the family too, without a release: **OpenRouter**, which reaches hundreds of models from many companies (DeepSeek, Kimi, GLM, Qwen, MiniMax and more) with one key, or a company you have an account with and its own address, or a model you run on your own network. The **Other companies** card adds, changes, chooses and takes them away. Nothing is sent to one until you choose it for a row, press **Answer with** (it then answers the chat row, and what follows it) or switch on **May stand in**; what you write goes to that company, and for OpenRouter to the company it routes to as well.

| What you set | What it does |
|---|---|
| Name, address and key | The address is the part before `/chat/completions`. It must be https and out on the internet, unless you tick that it runs on your own network, which also needs no key. The key is checked with the company (a free request) before it is kept, and only a key the company refuses stops the save. |
| Model for chat, for the rest, better and best | Names as the company writes them (OpenRouter's look like `vendor/model-name`). Empty uses the chat model. A model the company's list does not have is kept with a word about it. |
| May stand in | Off by default. On, the company answers when the one chosen cannot, and what was asked then goes to it. The company's own panel above can say it too, and then says it instead. |
| Prices | One model a line: its name, then US dollars per million tokens in, out and (if cheaper) for a cached read. A model with no price here, and none in the company's own list when it gives prices (OpenRouter's does, found by the [daily check](/wiki/controls/status/models-and-prices#what-the-daily-check-does)), is counted at more than any listed model, so the daily limit stops early. |
| Fields its thinking comes back in | Some companies need a model's thinking sent back unchanged beside a tool call. The first field a reply carries is used. |
| Extra request fields | A JSON object sent with every request, always: a company's own switches. OpenRouter is added asking only for companies that keep and train on nothing, and refusing a model that cannot use the tools; a request that leaves one out is never sent in its place. |

A saved key is not sent to a new address: change a company's address and the key is asked for again. When a company is added, FamilyDB reads its own list for what its models cost (OpenRouter's does) and says which models are still unpriced; type a price under **What it costs** for those, since until then every message to them is counted at more than any listed model and the daily limit is reached early. The keys are kept in the database like the other keys, so they are in every [backup](/wiki/operations/backup-and-restore), and are never shown again or written to the change history. Taking a company away takes its key. A company that is chosen for a row, or answers one by default, cannot be taken away; the page names the rows, and you choose another company for them first.

These companies cannot search the web, hear voice notes or look at photos, so they are not offered for those rows. Lookups and discovery go to the cheaper company with a key that can search and may stand in; with none, they wait, since one company is then the only one that sees what you write.

## Asking a stronger model to weigh a change

The **Weighing changes** row. Some changes need judgment and not a rule: which model replaces one that is going, what a refusal nobody can read means, which new models belong at which level, what a disputed price really is. When the row is on, FamilyDB asks the day's questions together after the evening's lookup time, in one call, plus at most two price checks that search the web; a refusal is asked at once. The call carries model names, prices and error messages, never the family's messages. It is off until a model is chosen for the row, which turns it on; **Off** turns it off. Older installs that set `judgements` on keep it on.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| What weighing a change may do by itself (`judgement_acts`) | within cost | **Put in a model at most about 10% dearer** (`within_cost`) saves a chosen model costing no more than about 10% over the one it replaces, tells admins, and lets you put the old one back. **Only suggest** (`suggest`) puts nothing in. In the row's settings. | `within_cost` or `suggest` |
| Most to spend on weighing changes in a month (`judgement_budget`) | US$1 | The monthly cap in the row. Counted within the daily limit too, over the calendar month in the family's time zone. A budget under about 5 cents, or 0, asks nothing. | 0 to 50 |

A judgment never changes a setting by itself except under "within cost"; a dearer model waits for an admin to press **Put these in** on [Models and prices](/wiki/controls/status/models-and-prices#put-these-in-and-put-back). A judgment must pick one of the options it was given, and a price is accepted only when it matches a price list.

## Choosing the suggestions

The **Choosing suggestions** row. For a planning question from a grown-up, such as "what should we do this weekend?" or "where should we eat tonight?", and for the weekend ideas, a stronger model picks first and the assistant then says the picks in her words. FamilyDB gives it what the family has told the assistant and done that bears on the question: ratings and notes, what the assistant remembers, the weeks before and after, and that chat's last few days. It picks a favorite, something new and a wildcard, each with a reason, and FamilyDB checks every pick against the options it was given. The call goes to the company that answers the chat unless you choose another for the row, and nowhere else.

A question about right now, a kid's question and any command such as `/now` are answered as before, at no extra cost. When choosing is off, over its budget or fails, the suggestions come in FamilyDB's own order and nobody is told. About 3 to 13 cents a planning question, depending on the company.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Most to spend on choosing suggestions in a month (`choose_budget`) | US$5 | The monthly cap in the row. Counted within the daily limit too, over the calendar month in the family's time zone. Once it is spent, suggestions go back to FamilyDB's own order until the month turns. 0 chooses nothing. | 0 to 50 |

## Voice notes and photos

The **Voice notes** and **Photos** rows. **Off** turns either off and the family is asked to type or to say it in words. Claude cannot hear voice notes, so only OpenAI and Google models are offered for that row, and they need that company's key.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Longest voice note heard (`voice_max_minutes`) | 5 | In the Voice notes row's settings. A longer one is not heard at all, since every minute is paid for. | 1 to 30 |

A voice note goes to the company that hears it; a photo goes to the company that looks things up, costs about a tenth of a cent, and is not kept. A recording's length is not kept either, so its cost here is counted at about 20 seconds a note. Of an album, only the first 4 photos are looked at. In a group, a photo is looked at only when it is sent to the bot, by a mention in its caption or a reply. Neither recording is kept; only the words are. What leaves the house is on [What leaves the house](/wiki/security/what-leaves-the-house).
