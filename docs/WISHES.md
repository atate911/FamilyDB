# Wish lists

The girls ask for things all day: an app approved, something to buy, somewhere to go, a present,
a film, a game. They say "we should…" when they mean "I want". Each girl keeps her own wish lists,
ranked by her, and a parent answers when they choose, so "put it on your list" is an answer. Vera
also guides how she asks and how often, kindly and at her age.

This file is what the family decided and how it is built. It is being built in steps; what is not
built yet is marked *planned*.

## What the family decided

- **Sisters never see each other's wishes.** Gifts are private too: a present for Chloe is never
  shown to Chloe, and the parents' gift ideas are never shown to the kids.
- **The girls use iPads, through the page.** No Telegram for them. Each has a private
  conversation with Vera that the parents can read. Everything goes through tools, so another
  home app can be connected later.
- **What a kid may do** (`roles.py`): sign in, read the ideas and the plans (not gifts), talk to
  Vera, keep her own wishes, and see her own things to do. Nothing else changes from her screen.
- **Everyday wishes** have daily rules. **Christmas and birthday wishes** are flagged
  (`occasion`), kept apart, and have looser rules.
- **"Not this time" locks an everyday wish** for 14 days, then 30, then 90, then 120, then a year,
  and a year each time after. Materially similar asks are one ask: a cat and a dog share one
  lockout.
- **Vera answers every wish at once**, in her voice, pitched to the girl's age. What else a kid's
  message sets off, such as looking up a place, is batched.
- **Vera sorts what they say.** "I want an iPhone" is a wish. A "one day" family thing (Thai food,
  poker, a trip to Astoria) is a family idea or a thing to do. Something can be both: "sushi for
  my birthday" is a birthday wish and a restaurant idea.
- **Each girl's model calls count against her own daily limit.** Reordering on the page is code,
  free, capped only against excess.
- **Overuse is flagged,** kindly ("you've asked for 5 things already today, let's exercise some
  restraint").
- **Helping a sibling is fine** ("get Chloe a birthday present"). **Complaints about one are
  turned away** ("Chloe has X and that's not fair").
- **Asking to override a house rule** ("more internet time") is turned away: ask a parent, not
  Vera.
- **An inappropriate request** is turned away, and the parents get one Telegram message.
- **Ask a parent**: a button, offered only when Vera judges it reasonable, a couple of times a
  week, that sends the request to the parents on Telegram.
- **Nothing else goes to the parents' phones.** A new wish sends nothing; there is no summary.
  They look at the lists when they choose.
- **"We should" → "I want"**: Vera nudges her wording at most once a day, more often the more she
  says "we should", less as she improves, with a warm word now and then when she says "I want".
- **The kids' screens** are the same Phosphor look, optimised for an iPad, with limited changes.
- **Tokens**: as few as possible go to the model.
- **Chores for money** are not part of this.

## How it is built

### Permissions (built)

`roles.py` gives each role its permissions; the page asks for a permission, never a role.

| Permission | Means | Admin | Parent | Kid |
| --- | --- | --- | --- | --- |
| `sign_in` | sign in, read the ideas and plans | yes | yes | yes |
| `chat` | talk to Vera | yes | yes | yes |
| `wish` | keep your own wish lists | yes | yes | yes |
| `change` | the forms that change ideas, plans, things to do | yes | yes | no |
| `browse` | memory, status, everybody's things to do | yes | yes | no |
| `decide` | see every kid's wishes and answer them | yes | yes | no |
| `manage` | settings, setup, the family list | yes | no | no |

`auth.NEEDS` gates by blueprint and `auth.NEEDS_HERE` by page. Templates hide what a visitor may
not use; the gate refuses it anyway.

### Gifts stay private (planned)

For a visitor without `decide`, the ideas and plans pages leave out ideas of kind `gift` and plans
made from them. Gift ideas also leave the idea list in the cached prompt prefix for everyone: they
are already kept out of suggestions and lookups, the birthday reminder reads them by code, and a
parent's chat can still find one with the idea search, which drops gifts for anybody without
`decide`. Vera cannot mention a gift she was never shown, and every request gets a little
smaller. A kid's wish to give a sister something is a wish on her own list, category `gift`.

### Birthdate and age (planned)

`members.birth_date`, set by an admin on the Family page through `familydb/family.py` (the
family list is never a tool). Code works out her age and the days to her birthday in the family's
timezone. Only her age reaches the model, in her turn line; never the date.

### Wishes (planned)

One table, `wishes`: whose (`member_id`), `occasion` (none for everyday, `christmas`,
`birthday`), `title`, `notes`, `category`, `topic` (a short key similar asks share: pet, phone),
`rank`, `status` (`open`, `granted`, `declined`, `withdrawn`, `turned_away`), for a turned-away
one its `concern` (`rule`, `sibling`, `inappropriate`, `too_many`), the answer, the lockout
(`locked_until`, `refusal_rung`), `parent_review` (`none`, `offered`, `asked`), and links to an
idea and the message it came from.

`familydb/wish_service.py` holds the rules, in code:

- **Everyday**: the lockout ladder `(14, 30, 90, 120, 365)` days per topic, counted by her
  declines of that topic; asking while locked does not lengthen it. At most `wish_daily_count` a
  day (default 5); the next is turned away as `too_many` and kept, so the parents see it.
- **Occasions**: no daily count, a cap on open wishes per list (`occasion_list_size`, default
  25), no ladder: a "not this time" holds until the occasion has passed. A topic locked on the
  everyday list may still go on an occasion list: "that's one for your birthday list" is the
  habit to encourage.
- **The same thing** is the same `topic`, or a close title match as a backstop. An open duplicate
  in the same list comes back as that wish rather than a copy.
- **Moving** (her order, or flagging it for an occasion and back) is free, capped at
  `wish_moves_per_day` (default 300).
- **Who**: a kid adds, retitles, reorders, flags and withdraws her own; `decide` does it for any
  kid and grants or declines.

### Tools and what the model sees (planned)

Two chat tools: `add_wish` (title, topic, occasion, category, notes, for whom: parents only, the
idea made alongside) and `update_wish` (position, occasion, status, answer note, parent review);
and `turn_away` (a one-line summary, the concern, whether a parent may review it). Results are a
few fields. There is no list tool: her topics come in her turn line, and parents use the page.

In her private chat only, code adds one line to the current (uncached) turn, for example
`Mia, 9. Topics: pet (locked to Nov 3), phone, roblox. Wording: nudge.` At most twelve topics,
the locked first. Usually under 30 tokens; nothing is added to the cached prefix but the tools.

### Wording (planned)

Code spots "we should", "we could", "can we", "let's get", and "I want" / "I'd like", and keeps a
little state per kid: how often she said "we should" in the last week, and when she was last
nudged and last praised. Never twice a day; on the first "we should" of a day when she has used
it at least `wording_daily_after` times in the week (default 3), otherwise at most every three
days; so the nudges thin out as she improves. "I want" earns a warm word at most every three
days. The prompt keeps it to one kind line at her age, never a lecture, and never when "we"
really is the family.

### Her conversation, her limit, the two messages to parents (planned)

A kid's chat is `member:<id>`: private, read by parents at `/chat?with=<id>`. Her calls are
summed per day against `kid_daily_spend`; past it, a line from `voice.say` and no call. Ideas her
messages make are looked up in one daily pass at `kid_lookup_hour`. A parent's answer is a line in
her chat, worded by `voice.say`.

Telegram goes to the parents for two things only: an inappropriate request, and an Ask-a-parent
tap. Each has buttons (Yes!, Not this time, Later) that answer through `update_wish` as the parent
who tapped, with no model call.

### Screens (planned)

A kid's Home: her conversation with Vera, her wishes (the top of the everyday list, the Christmas
and birthday lists with their countdowns, new answers), what is coming up (no gifts), and her own
things to do. Her bar: Home, Vera, Wishes, Ideas, Plans, To do. A parent's Home gains a Kids card:
each girl's open wishes, anything flagged, requests waiting. `/wishes` is the lists, reordered by
buttons, and by dragging where scripts run (`static/wishes.js`).

## Settings (planned)

`kid_daily_spend`, `wish_daily_count`, `occasion_list_size`, `wish_moves_per_day`,
`parent_asks_per_week`, `kid_lookup_hour`, `wording_daily_after`, on a Kids group of the
settings.
