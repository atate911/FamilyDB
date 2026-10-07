# Kids' wish lists

The wish lists are how a kid asks for things without the asking taking over the day: each kid keeps their own lists, the bot answers at once, code holds the limits, and a parent decides. This page explains the rules. For the screens, see [Wish lists](/wiki/controls/wish-lists).

## Why it is built this way

Kids ask for things all day and say "we should" when they mean "I want". So each kid has a list a sibling never sees, a parent rather than the bot says yes or no, and the bot helps a kid ask kindly, at their age, without becoming a way around the house rules. The page says "list" and "I'd like"; the code, the tools and the model say "wish".

## Three lists

Each kid has **Every day**, **Christmas** and **Birthday**, ranked in the kid's own order. Every day has daily rules. The other two are looser: no daily count, a cap on length, and no ladder.

## How the bot sorts an ask

The model reads what a kid says, under rules in the product spec. A want of their own (to have, buy, be allowed, or get for Christmas or a birthday) becomes a wish with `add_wish`. Something the family could do together, such as Thai food or a trip, becomes an idea or a [thing to do](/wiki/reference/glossary#thing-to-do). Something can be both: "sushi for my birthday" is a birthday wish and a restaurant idea.

`update_wish` moves, rewords or withdraws a wish, and a parent uses it to answer. `turn_away` records an ask the model refuses, with one of three concerns: a house rule, a complaint about a sibling, or an inappropriate request. Helping a sibling ("get Chloe a present") is not turned away: it goes on the kid's own list as a gift. The sorting is the model's judgement; what follows is code.

## The rules code holds

| Rule | What happens | Setting |
|---|---|---|
| Asks a day, Every day list | The next is kept, marked "too many", and parents see it. Default 5 | `wish_daily_count` |
| Length of Christmas and Birthday lists | A full list refuses another. Default 25 each | `occasion_list_size` |
| Ask a parent | Offered only when the model judged the ask fair and it was not inappropriate, at most this many times in 7 days per kid. Default 2 | `parent_asks_per_week` |
| "We should" to "I want" | See below. Default 3 | `wording_daily_after` |

Values are on [Spending](/wiki/controls/settings/spending#the-kids-wish-lists). Moving within a list, or onto Christmas or Birthday, is free, capped at 300 moves a day per person, a limit in code. For a kid, moving a wish onto Every day is held to the lock and the daily count, and counts as an every-day ask. A move into a full list is refused.

**The lockout ladder.** A parent's "not this time" on an Every day wish locks that topic for 14 days, then 30, 90 and 120, then a year each time after. The count is the number of earlier declines of the same topic. A topic is a short key the bot gives (cat and dog can share "pet"), with a close title match as a backstop. Asking while locked adds nothing and does not lengthen the lock. A lock belongs to one list, so a locked Every day wish can go on Christmas or Birthday, which the bot encourages. On those lists a "not this time" lasts until the day after the occasion.

A parent adding for a kid is held to neither the lock nor the daily count, but still to a full list.

**"We should" to "I want".** Code spots a message that opens with a phrase like "we should" or "can we". It sets a word in the turn asking the bot to reflect "I want" back kindly, at most once a day: on the first one of a day when the kid has said it `wording_daily_after` or more times in the past 7 days, otherwise only if the last nudge was 3 or more days ago. "I want" earns a warm word at most every 3 days. It is a word in a call already being made, never a second call.

## Who may answer, and how

Only somebody with the "decide" permission, a parent or admin, grants or declines a wish. A kid changes only their own list. There are two ways to answer: the form on the page, with an optional note, or a button on Telegram. Both run `update_wish` as the person who answered, so the rules above apply either way, and a tap makes no model call. The kid is told in their own conversation, in the bot's words, with the note and, for no, the day they may ask again.

Only two things reach a parent's phone, each sent to every parent and admin with a Telegram id: an inappropriate request, sent straight away, and a kid's Ask a parent. Each has **Yes!**, **Not this time** and **Later**. Later only leaves it waiting. A kid who taps is told only a parent can answer. A new wish sends nothing.

## Presents are kept from kids

A present is an idea of kind "gift", not a wish. Every kid is kept from every present, and by default so is any grown-up it names. Gift ideas are left out of the idea list in the cached prefix, so the model is not shown them unless it searches, and the idea search leaves them out for anybody they are kept from. Things to do about a present are hidden from the same people. The spec also tells the model not to mention presents or other kids' wishes in a kid's chat. That part is an instruction, not code.

## What a kid's message carries

Every message from a kid carries one line, built by code, in the current turn (not cached): the name, "a girl", "a boy" or "a kid", and an age if set. Then the wish topics, up to 12, locked ones first with the day they unlock. Topics are included only in a private chat. Where anybody else reads the reply, they are left out. Then, when code has decided, a wording word, "nudge" or "praise". The spec tells the model to speak to that age. A birthday date never goes in it.

## Limits on spending

A kid adds a wish by talking to the bot, so it counts toward their daily messages and dollar share ([The family and roles](/wiki/model/family-and-roles#kids)). A parent can add for a kid with a form on the Wishes page, which runs `add_wish` with no model call and costs neither. Moving and taking off cost nothing, except that a kid's move onto Every day is held to the rules above.

Developer docs: `docs/WISHES.md`, `src/familydb/wish_service.py`, `tools/wishes.py`, `wording.py`, `presents.py`, `buttons.py`, `agent/render.py` (`render_kid_line`), and `docs/DESIGN.md`, "Decisions" (the row "Kids' wish lists").
