# Lookups settings

Filling ideas in from the web: an idea's address, opening hours and prices, and what is on nearby.
A separate, smaller turn reads the web, and each lookup costs a little, within the daily limit. The
chat itself never gets the web.

If looking ideas up is on but there is no key for the company that does it, the page warns that
nothing is looked up until there is one. Which company and which model do it is on the
[AI model](/wiki/controls/settings/ai-model#a-second-company) page.

## Looking ideas up

| Setting | Default | What it does |
|---|---|---|
| Look ideas up on the web (`web_tools_enabled`) | on, after an install | Without it, the lookup job is not run, no idea is filled in and nothing new is discovered, and `/lookup` says lookups are switched off. The program's own default is off; the installer turns it on, so a new install has it on. With no key for the company that does it, ideas wait and are looked up once a key is added |
| Days before details look old (`place_stale_days`) | 30 | After this, an idea's hours and prices are marked as worth checking again, and looked up again the next time the idea is suggested (within the spending limit) |

## When

Filling an idea in rarely changes what you do next, so by default it waits for the evening, when the
ideas waiting are looked up together (up to 40 in one run, the rest at the next checks), with one note in
each chat for what was found. An idea edited after that hour waits for the next evening, and everything
waits until tomorrow when the day's spending limit is used up. Asked for now, by
asking the assistant, by the button on the Status page or an idea's page, or by `/lookup` on Telegram,
one is looked up within a few minutes.

| Setting | Default | What it does |
|---|---|---|
| Look ideas up (`lookups_when`) | in the evening | In the evening, or as soon as each idea is added ("asap") |
| Time for the evening's lookups (`lookup_hour`) | 21 | In the family's time zone |

## How often

Folded away, under "How often".

| Setting | Default | What it does |
|---|---|---|
| Minutes between checks (`enrich_interval_minutes`) | 2 | How often it checks for ideas due to be looked up, which is how soon one asked for now is. Between 1 and 1440 |
| Ideas looked up at a time (`enrich_batch`) | 3 | When each is looked up as it is added. The evening's lookups take every idea waiting. Between 1 and 20 |

A lookup is bounded: a few searches and page reads, a cap on steps, and a cap on its answer. The job
checks the database first and calls no model when nothing is due.

Developer docs: `docs/DESIGN.md`, "Enrichment: filling in the details" and "When ideas are looked up".
