# Spending settings

What the model may cost: a limit for the whole family, a share for each kid, limits on what one
message may use, and how hard the model thinks. The page opens with a line saying about how much
has been spent today against the limit.

**The spending figure is an estimate.** It is worked out from each call's size and a table of
prices, to stop a runaway day. It is not your bill, so also set a spending limit with the AI
company.

## The daily limit

| Setting | Default | What it does |
|---|---|---|
| Daily spending limit, US$ (`daily_spend_limit`) | 2.00 | Estimated across every model call. Once it is reached, nothing more is asked of a model until midnight in the family's time zone. Whoever writes is told (an adult is told to raise the limit on this page; a kid is only told to come back tomorrow, never about money). Voice notes, photos and the evening lookups wait too, and admins with a Telegram id are told if "Tell admins on Telegram" is on. 0 means no limit. Between 0 and 500 |
| Messages a kid may send a day (`kid_daily_messages`) | 0 | For each kid on the family list, counting only messages a model answered: `/today` and the buttons under a reminder cost nothing and are not counted. Past it, the kid is told the number ("That's 20 messages today, which is all for today") and to ask again tomorrow or ask a grown-up. 0 means no limit. Between 0 and 500 |
| Each kid's daily share, US$ (`kid_daily_spend`) | 0.25 | What each kid's own messages may spend in a day. It counts toward the daily limit, which still applies. It is checked before each message is answered, so one message may cross it. When it is used up the kid is told, kindly, to come back tomorrow, without a word about money; their wish list still works on the page. 0 means no share of their own. Between 0 and 50 |

**A kid has two limits, and the second is on by default.** The message count is off until you set
it, but the dollar share is 25 cents a day from the start.

## The kids' wish lists

How much the kids may ask for, and how the bot guides how they ask (see `docs/WISHES.md`).

| Setting | Default | What it does |
|---|---|---|
| Everyday wishes a day (`wish_daily_count`) | 5 | How many things a kid may add to their everyday list in a day. The next is kindly turned away and shows on the Kids card. Christmas and birthday lists have no daily count. Between 1 and 50 |
| Longest Christmas or birthday list (`occasion_list_size`) | 25 | How many wishes each of a kid's Christmas and birthday lists may hold at once. Between 1 and 100 |
| Ask a parent, times a week (`parent_asks_per_week`) | 2 | How often a kid may send a parent something the bot said no to, when it offers. 0 means never. Between 0 and 14 |
| Nudge "we should" every day after (`wording_daily_after`) | 3 | Once a kid has said "we should" for a want of their own this many times in a week, the bot reflects "I want" back once a day; less often, every few days. Between 1 and 20 |

## Thinking

How long the model may think before it answers. More helps with hard questions and costs more.

| Setting | Default | What it does |
|---|---|---|
| Chat thinking (`effort`) | medium | low, medium, high, xhigh or max |
| Lookup thinking (`worker_effort`) | low | Looking a place up needs little: low is usually plenty |

## What one message may use

Folded away, under "What one message may use". Limits for a single message: lower is cheaper but can
cut an answer short. The defaults suit a family.

| Setting | Default | What it does |
|---|---|---|
| Longest answer (tokens): `max_output_tokens` | 16000 | A token is about three quarters of a word. An answer is rarely near it. Between 256 and 64000 |
| Steps per message (`agent_max_iterations`) | 8 | How many tools (a search, a save) it may use before it has to answer. Between 1 and 20 |
| Steps per lookup (`worker_max_iterations`) | 12 | Between 1 and 30 |
| Ideas sent with every message (`prompt_idea_limit`) | 150 | The newest this many; older ones are still found by searching. 0 sends them all. Between 0 and 5000 |
| Messages of chat remembered (`history_limit`) | 20 | How many earlier messages go with each new one. Between 0 and 200 |
| Hours of chat remembered (`history_hours`) | 6 | Older messages are left out. 0 makes every message stand on its own. Between 0 and 720 |
| Claude's prompt cache (`anthropic_cache_ttl`) | 1h | Only for Claude: how long it keeps the part of every request that does not change. An hour costs less, as a family writes in bursts; the other choice is 5m |

To see what a message costs before anyone types, run `familydb debug cost` on the server; the Status
page shows the last thirty days per model.

Developer docs: `docs/DESIGN.md`, "Cost", and `docs/AI_CALLS.md`.
