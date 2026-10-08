# Models and prices

The Models and prices card on [Status](/wiki/controls/status) shows what the daily check read from the model companies and the public price lists, what changed, and what a stronger model was asked to weigh. It tells you that a model is going away, or got dearer, before it costs you. Parents see it; only admins get the buttons.

## What the daily check does

It runs at 05:17 in the family's time zone, calls no model and sends nothing about the family. It asks each model company you have a key for which models the key may use, and reads two public price lists, LiteLLM's and OpenRouter's.

- **Both lists agree** (within 5% of each other): it takes that price.
- **Only one list has the model:** it takes that list's price.
- **The lists disagree, or a price moves more than fivefold:** it keeps the old price and notes it.

If a model in use is gone, the nearest model costing no more than twice as much answers in its place until you choose another.

The check is on by default and set on [AI model](/wiki/controls/settings/ai-model#keeping-up-with-the-companies). With it off, the card says prices are the ones this version was released with and nobody is told when a model goes. Before its first run it says nothing has been read yet. The estimate rules and what to turn down are on [Cost](/wiki/operations/cost).

## What the card shows

- **The sources.** One row for each price list and each company with a key: when it was read and how many models, or why it could not be.
- **Changed in the last 30 days.** A table of when, company, model and what: new, no longer offered to the key, offered again, a price moved, or a retirement date.
- **Judgments.** Each question a stronger model weighed, with its answer, outcome and reason. They need **Ask a stronger model when a change needs judgment** on, which is off by default; see [AI model](/wiki/controls/settings/ai-model#asking-a-stronger-model-to-weigh-a-change).

## Put these in and Put back

A judgment can suggest or make a change to the models. An admin gets two buttons, each saving the settings it names.

| Button | Shown when | What it does |
|---|---|---|
| **Put these in** | A model was suggested and is not in force yet. | Saves the suggested models. Under "within cost", a model more than about 10% dearer than the one it replaces waits for this press; under "suggest", every one does. |
| **Put back** | A judgment put a model in and it is still in force. | Restores what was there before. |

A judgment is only ever one of the options the check gave it, and a price is accepted only when it matches a price list.

## Needs a look rows about models

These appear under Needs a look on Status, and an admin with a Telegram id is told as for any other row. A row is cleared after seven days without being seen again.

| Row | It means | Goes away when | Do this |
|---|---|---|---|
| A **model in use is going, or has gone** | The model company says it has no model of that name, or the check no longer finds it offered to your key, or a price list gives it an end date within 60 days. | That model answers a call, or the next check lists it again. A retirement notice is only cleared after seven days. | Choose another model on [AI model](/wiki/controls/settings/ai-model#which-model-is-everyday). If a box names the model and a replacement is on offer, an admin gets a **Use [model] instead** button that saves it. |
| The **price of a model in use changed** | The check read a new price. | Seven days pass. | Nothing, unless the new price is more than you want to spend. |
| **The price lists need a look** | A list could not be read 3 days running, or the two lists disagree, or a price jumps more than fivefold, for a model in use. The old price is kept. | A list is read again. A disagreement also clears when a stronger model settles the price. | Wait a day. The row says which list. |
| **What the calls cost or do moved** | In the last 7 days one kind of call changed by a factor of 1.5 either way in cost per answer, tokens a call or calls an answer, or became twice as slow, or ended badly at least 5 points and twice as often as in the 28 days before. It needs at least 20 calls in each period. | Seven days pass. | Look at the cost figures and Recent activity to see what changed. |
