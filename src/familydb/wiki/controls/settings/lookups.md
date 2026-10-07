# Lookups

The Lookups card sets whether FamilyDB fills ideas in from the web: an idea's address, opening hours and prices, and what is on nearby. A separate, smaller [turn](/wiki/reference/glossary#turn) reads the web, and each lookup is a model call within the daily limit. The chat itself never gets the web.

If looking ideas up is on but there is no key for the model company that does it, the card warns that nothing is looked up until there is one. Which company and which model do it is on [AI model](/wiki/controls/settings/ai-model#a-second-company).

## Looking ideas up

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Look ideas up on the web (`web_tools_enabled`) | off in the program; the installer turns it on | Off: the lookups job does not run, no idea is filled in, nothing new is discovered, and `/lookup` says lookups are switched off. With no key for the company that does it, ideas wait and are looked up once a key is added. | on or off |
| Days before details look old (`place_stale_days`) | 30 | After this, an idea's hours and prices are marked as worth checking again, and looked up again the next time the idea is suggested (within the spending limit). | 1 to 3650 |

## When

Filling an idea in is seldom urgent, so by default it waits for the evening. Then the ideas waiting are looked up together, up to 40 in one run and the rest at the next checks, with one note in each chat for what was found. An idea edited after that hour waits for the next evening, and everything waits until tomorrow when the day's spending limit is used up.

An idea asked for now is looked up at the next check (every 2 minutes by default). Ask by telling the assistant, by the button on [Status](/wiki/controls/status) or an idea's page, or by `/lookup` on Telegram.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Look ideas up (`lookups_when`) | in the evening | Looks ideas up together in the evening, or as soon as each idea is added ("asap"). | evening or asap |
| Time for the evening's lookups (`lookup_hour`) | 21 | The hour of the evening run, in the family's time zone. | 0 to 23 |

## How often

Folded away on the card, under "How often".

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Minutes between checks (`enrich_interval_minutes`) | 2 | How often the lookups job checks for ideas due, which is how soon one asked for now is looked up. | 1 to 1440 |
| Ideas looked up at a time (`enrich_batch`) | 3 | How many are looked up in one check when each is looked up as it is added. The evening run takes every idea waiting. | 1 to 20 |

A lookup is bounded: at most 3 web searches for an idea (4 when discovering what is on), a cap on steps (**Steps per lookup** on [Spending](/wiki/controls/settings/spending#what-one-message-may-use)), and a cap on its answer. The job reads the database first and calls no model when nothing is due.
