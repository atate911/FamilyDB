# Wish lists

Each kid keeps what they would like on lists of their own, in their own order, and a parent answers when they choose. A parent or admin opens **Kids' lists**; a kid opens **My list**, which holds only their own.

## What each person sees

| Who | Page | What they can do |
|---|---|---|
| A kid | **My list** | Tell the bot what they would like, in a box at the top. Reorder (Top, Up, Down, or drag where scripts run), move a wish to another list, take one off. See **Answers** (the last 30 days) and **Not on your list**. A line says which parents can see the list |
| A parent or admin | **Kids' lists** | Each kid's top three on each list; open a kid for their full lists. Add, reorder, move and take off for them, and answer. **Flagged** shows what the bot turned away, **Answers** what was answered; both show the last 30 days |

Each kid has three lists: **Every day**, **Christmas** and **Birthday**. A kid never sees another kid's list. Kids switched off on the [Family](/wiki/controls/family) page are left out. A **to decide** badge counts what waits on a parent. A parent can read a kid's conversation with the bot on Chat.

## How a kid asks

1. The kid writes in the box on My list, Home or Chat: "I'd like roller skates."
2. The bot sorts it. A want of their own goes on a list. Something the family could do together becomes an idea or a [thing to do](/wiki/reference/glossary#thing-to-do), and "sushi for my birthday" is both a birthday wish and an idea.
3. The bot answers at once, briefly, at the kid's age. It is told the age and, if set on the Family page, male or female, never the birthday date.

Adding goes through the bot, so it counts as one of the kid's messages (see the limits on [Spending](/wiki/controls/settings/spending)). Moving and taking off are done by code: they cost nothing and still work when a limit is reached.

## How the bot guides

- **"We should" becomes "I want".** Code spots a message that opens with a phrase such as "we should", "we need to", "can we" or "let's get". The bot kindly reflects "I want" back at most once a day: if the kid has said such a phrase `wording_daily_after` or more times in the past 7 days (counting this one), the first one each day gets the nudge; otherwise a nudge needs the last one to be three or more days ago, or none yet. "I want" earns a warm word at most every three days. This is a word in the chat call already being made, never a second call.
- **Turned away.** A house rule ("more screen time"), a complaint about a sibling and an inappropriate request are each kept for the parents. A house rule gets "ask a parent"; an inappropriate request gets a plain no. Helping a sibling ("get Chloe a present") is fine: it goes on the kid's own list as a gift.
- **Ask a parent.** For an ask the bot judged fair to put to a parent, the kid gets an **Ask a parent** button, once per ask. An inappropriate one is not offered it.

## The limits

| Rule | What happens | Setting |
|---|---|---|
| Wishes a day on Every day | The next is kept as "Too many in one day", visible to parents. Default 5 | `wish_daily_count` |
| Length of Christmas or Birthday lists | A full list refuses another. Default 25 each | `occasion_list_size` |
| Ask a parent | Offered to each kid at most this many times in any 7 days, an offer counting when made. Default 2; 0 means never | `parent_asks_per_week` |
| Nudging wording | Described above. Default 3 | `wording_daily_after` |

Change these on the Spending page (admins), under [The kids' wish lists](/wiki/controls/settings/spending#the-kids-wish-lists).

**Not this time** locks an Every day wish for 14 days, then 30, 90 and 120, then a year each time after. The count is per topic, so a cat and a dog share one lockout when the bot files them under the same topic (from the page's form, the title is the topic). Asking while locked adds nothing and does not lengthen the lock. The bot says when the kid may ask again and offers the Christmas or Birthday list. The ladder is in code, not a setting.

Christmas and Birthday lists have no daily count and no ladder: a "not this time" holds until the day after the occasion, or about a year if no birthday is on the Family page. A lock belongs to one list, so a locked Every day wish can go on Christmas or Birthday. A wish moved off Every day cannot go back while a declined wish on that topic still locks it there, and a move onto Every day counts toward the day's count and is refused when it is used up.

A wish already on a list (same topic or nearly the same title) is not added twice. A parent adding for a kid is held to neither lock nor daily count, but still to a full list. Moving is capped at 300 a day per person, in code.

## How a parent answers

1. Open **Kids' lists** and choose a kid, or follow the **to decide** badge (it counts kid asks and "Not OK" requests from the last 30 days that no parent has answered).
2. Tap a wish's line to open it, add an optional note (up to 500 characters), and choose **Yes!** or **Not this time**. On a kid's own page, an ask they sent you also shows under **Flagged** with the same two buttons. A request the bot flagged as "Not OK" has no buttons on the page: answer it from the Telegram message. An answered item moves to Answers.
3. The kid is told in their own conversation, in the bot's words with your note and, for no, the day they may ask again. An answered wish leaves the open list and shows under Answers for 30 days.

Only two things reach a parent's phone, each sent to every parent or admin with a Telegram id: an inappropriate request, sent straight away, and a kid's Ask a parent. Each carries **Yes!**, **Not this time** and **Later**. A tap answers as the person who tapped, with no model call; Later leaves it on the page. A new wish sends nothing: look when you choose.

## Presents kept from kids

A kid's list is not secret: the parents can see it, and the page says so. A present for a kid is not a wish. Add it as a gift idea on the [Ideas](/wiki/controls/ideas) page. Every kid is always kept from it. By default so is any grown-up the idea names, and on the idea you choose which grown-ups it is hidden from; the page says "Hidden from the kids and Alex". Things to do about it are hidden from the same people. In a kid's chat the bot is not shown gift ideas and is told not to mention presents or other kids' wishes.

## What a kid is shown

A kid is shown what to do next, not how the bot works. A limit is put plainly ("come back tomorrow"), without dollars, settings or logs. [Security and trust](/wiki/security#who-may-do-what) lists what each role may do.

## What is not for the bot to change

Only a parent or admin can grant or decline a wish; the bot acting for a kid cannot. A kid can change only their own list. Who answers and what reaches parents' phones are not the bot's to change.

**Taking a kid off the family list for good deletes their wish lists.** Switching them off keeps them.

Developer docs: `docs/WISHES.md`; `src/familydb/wish_service.py`, `tools/wishes.py` and `wording.py`; `docs/DESIGN.md`, "Kids' wish lists".
