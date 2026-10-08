# Wish-list rules

A kid asks for things on wish lists of their own, the assistant answers at once, code holds the limits, and a parent decides. To use the screens, see [Wish lists](/wiki/controls/wish-lists). To change a limit, use [Spending](/wiki/controls/settings/spending#the-kids-wish-lists).

The page and the assistant say "list" and "I'd like". The code, the tools and the model say "wish".

## Three lists

Each kid has **Every day**, **Christmas** and **Birthday**, ranked in the kid's own order. Every day has daily rules. The other two are looser: no daily count, a cap on length, and no ladder.

## How the assistant sorts an ask

The model reads what a kid says, under rules in the product spec. A want of their own (to have, buy, be allowed, or get for Christmas or a birthday) becomes a wish with `add_wish`. Something the family could do together, such as Thai food or a trip, becomes an idea or a [thing to do](/wiki/reference/glossary#thing-to-do). Something can be both: "sushi for my birthday" is a birthday wish and a restaurant idea.

`update_wish` moves, rewords or withdraws a wish, and a parent uses it to answer. `turn_away` records an ask the model refuses, with one of three concerns: a house rule, a complaint about a sibling, or an inappropriate request. Helping a sibling ("get Chloe a present") is not turned away: it goes on the kid's own list as a gift. The sorting is the model's judgment; what follows is code.

A kid adds a wish by talking to the assistant, so it counts toward their daily messages and dollar share ([Kids](/wiki/model/family-and-roles#kids)). A parent can add one for a kid with the form on that kid's page, which makes no model call and costs nothing. Moving and taking off cost nothing either.

## The rules code holds

| Rule | What happens | Setting |
|---|---|---|
| Asks a day, Every day list | The next is kept, marked "too many", and parents see it | `wish_daily_count` |
| Length of Christmas and Birthday lists | A full list refuses another | `occasion_list_size` |
| Ask a parent | Offered only when the model judged the ask fair and it was not inappropriate, at most this many times in 7 days per kid | `parent_asks_per_week` |
| "We should" to "I want" | Described below | `wording_daily_after` |

Moving within a list, or onto Christmas or Birthday, is free, capped at 300 moves a day per person. A kid moving a wish onto Every day is subject to the lock and the daily count, and it counts as an every-day ask. A move into a full list is refused. A parent adding for a kid is subject to neither the lock nor the daily count, but still to a full list.

## The lockout ladder

A parent's "not this time" on an Every day wish locks that topic for 14 days, then 30, 90 and 120, then a year each time after. The count is the number of earlier declines of the same topic. A topic is a short key the assistant gives (cat and dog can share "pet"), with a close title match as a backstop. Asking while locked adds nothing and does not lengthen the lock.

A lock belongs to one list, so a locked Every day wish can go on Christmas or Birthday, which the assistant encourages. On those lists a "not this time" lasts until the day after the occasion.

## "We should" to "I want"

Kids say "we should" when they mean "I want". Code spots a message that opens with a phrase like "we should" or "can we" and asks the assistant to reflect "I want" back kindly, at most once a day. It does so on the first one of a day when the kid has said it `wording_daily_after` or more times in the past 7 days, and otherwise only if the last nudge was 3 or more days ago. A kid who says "I want" earns a warm word at most every 3 days. Both are one word in a call already being made, never a second call.

## Who may answer, and how

Only somebody with the "decide" permission, a parent or admin, grants or declines a wish. A kid changes only their own list. There are two ways to answer: the form on the page, with an optional note, or a button on Telegram. The page shows the form on a kid's Ask a parent and on a request turned away as inappropriate, to a parent only. Both run `update_wish` as the person who answered, so the rules above apply either way, and a tap makes no model call. The kid is told in their own conversation, in the assistant's words, with the note and, for no, the day they may ask again.

Only two things reach a parent's phone, each sent to every parent and admin with a Telegram id: an inappropriate request, sent straight away, and a kid's Ask a parent. Each has **Yes!**, **Not this time** and **Later**, and Later only leaves it waiting. A new wish sends nothing.

## Presents and the kid's message

A present is an idea of kind gift, not a wish, and it is kept from every kid ([Presents](/wiki/model/ideas-and-places#presents)).

Every message from a kid carries one line, built by code, in the current turn: the name, "a girl", "a boy" or "a kid", and an age if set. Then come up to 12 wish topics, locked ones first with the day they unlock, only in a private chat. Last, when code has decided, a wording word: "nudge" or "praise". A birthday date never goes in it.

## Why it is built this way

Kids ask for things all day. So each kid has a list a sibling never sees, a parent rather than the assistant says yes or no, and the assistant helps a kid ask kindly, at their age, without becoming a way around the house rules.

Developer docs: docs/WISHES.md, "What the family decided"; docs/DESIGN.md, "Decisions".
