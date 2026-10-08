# Spending

The Spending card sets what the model may cost: a limit for the whole family, a share for each kid, limits on what one message may use, and how hard the model thinks. The card opens with a line saying about how much has been spent today against the limit. The figure is an estimate, not the bill: FamilyDB works it out from each call's size and a table of prices to stop a runaway day, so also set a spending limit with the model company. How the estimate is made is on [Cost](/wiki/operations/cost).

## The daily limit

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Daily spending limit, US$ (`daily_spend_limit`) | 2.00 | Once the estimated spend across every model call reaches it, nothing more is asked of a model until midnight in the family's time zone. 0 means no limit. | 0 to 500 |
| Messages a kid may send a day (`kid_daily_messages`) | 0 (off) | Counts, for each kid, only messages a model answered; `/today` and the buttons under a reminder cost nothing. 0 means no limit. | 0 to 500 |
| Each kid's daily share, US$ (`kid_daily_spend`) | 0.25 | What a kid's own messages may spend in a day, inside the daily limit. 0 means no share of their own. | 0 to 50 |

A kid has two limits, and the second is on from the start: the message count is off until you set it, and the dollar share is US$0.25 a day.

When the daily limit is reached, voice notes, photos and the evening lookups wait too, and an admin with a Telegram id is told if **Tell admins on Telegram** is on. Whoever writes is told. An adult is told to raise the limit on this card. A kid is told only to come back tomorrow, with no word about money.

The message count is checked before anything is heard or asked. Past it, the kid is told the number ("That's 20 messages today, which is all for today") and to ask again tomorrow or ask a grown-up. The daily share is checked before each message is answered, so one message may cross it. When it is used up, the kid is told kindly to come back tomorrow, and their wish list still works on the web page. What a kid sees of all this is on [The family and roles](/wiki/model/family-and-roles#kids).

## The kids' wish lists

How much the kids may ask for, and how the assistant guides how they ask. The rules are on [Wish-list rules](/wiki/model/wishes).

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Everyday wishes a day (`wish_daily_count`) | 5 | How many things a kid may add to their everyday list in a day. The next is kindly turned away. | 1 to 50 |
| Longest Christmas or birthday list (`occasion_list_size`) | 25 | How many wishes each of a kid's Christmas and birthday lists may hold at once. | 1 to 100 |
| Ask a parent, times a week (`parent_asks_per_week`) | 2 | How often a kid may send a parent something the assistant said no to, when it offers. 0 means never. | 0 to 14 |
| Nudge "we should" every day after (`wording_daily_after`) | 3 | After a kid has said "we should" for a want of their own this many times in a week, the assistant reflects "I want" back once a day instead of every few days. | 1 to 20 |

Christmas and birthday lists have no daily count, and a wish turned away shows on the Kids' lists page for parents.

## Thinking

How long the model may think before it answers. More helps with hard questions and costs more.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Chat thinking (`effort`) | medium | How hard the model thinks about a message. | low, medium, high, xhigh or max |
| Lookup thinking (`worker_effort`) | low | How hard it thinks when it looks a place up, which needs little. | low, medium, high, xhigh or max |

## What one message may use

Folded away on the card, under "What one message may use". These limit a single message: lower is cheaper but can cut an answer short. The defaults suit a family.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Longest answer (tokens) (`max_output_tokens`) | 16000 | The most a single answer may run to. A [token](/wiki/reference/glossary#token) is about three quarters of a word. | 256 to 64000 |
| Steps per message (`agent_max_iterations`) | 8 | How many tools (a search, a save) it may use before it has to answer. | 1 to 20 |
| Steps per lookup (`worker_max_iterations`) | 12 | The same, for a lookup. | 1 to 30 |
| Ideas sent with every message (`prompt_idea_limit`) | 150 | The newest this many go with each message; older ones are still found by searching. 0 sends them all. | 0 to 5000 |
| Messages of chat remembered (`history_limit`) | 20 | How many earlier messages go with each new one. | 0 to 200 |
| Hours of chat remembered (`history_hours`) | 6 | Older messages are left out. 0 makes every message stand on its own. | 0 to 720 |
| Claude's prompt cache (`anthropic_cache_ttl`) | 1h | Only for Claude: how long it keeps the part of every request that does not change. An hour costs less because a family writes in bursts. | 5m or 1h |

To see what a message costs before anyone types, run `familydb debug cost` as in [The command line](/wiki/operations/command-line#how-to-run-it); [Status](/wiki/controls/status) shows the last 30 days by kind of call.
