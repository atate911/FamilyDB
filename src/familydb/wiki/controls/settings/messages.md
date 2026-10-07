# Messages settings

What FamilyDB sends without being asked, and when. The top of the page lists each kind of message
with whether it is on, when it goes, what it costs, how many went in the last few days and the
latest in full, so you can see what the family is actually receiving. Below that are the settings
that turn each kind on and off and move its time. All times are in the family's time zone.

If there is no key for the AI model yet, the page warns that no weekend ideas will be sent until there is one.

## Weekend ideas

Once a week the assistant asks itself what the family should do at the weekend and sends the answer:
one model call a week.

| Setting | Default | What it does |
|---|---|---|
| Weekend ideas go to (`digest_chat_id`) | the page's chat, on an install | Choose a chat it has seen, or another Telegram chat by its id. A group is offered once somebody on the family list has written in it. Empty sends none, and the weekly job does not run |
| Weekend ideas day (`digest_day`) | Thursday | |
| Weekend ideas time (`digest_hour`) | 18 (6 pm) | In the family's time zone |

The installer starts this on the page's own chat, because a Telegram group needs someone to write in
it first. Move it to the family's Telegram chat once they have.

## Follow-ups and notes

These are written from the assistant's lines, not thought up by a model, so they cost nothing.

| Setting | Default | What it does |
|---|---|---|
| Ask how a plan went (`follow_ups`) | on | The day after, with buttons to answer in one tap, so the ideas list learns what you liked. Off means nobody is asked; how it went can still be told at any time |
| Time to ask how a plan went (`follow_up_hour`) | 10 | The day after a plan |
| Check tomorrow's plans the evening before (`plan_checks`) | on | Rain for an outdoor plan, or the place listed as closed then: said only when something is off, with another idea for the same time when one fits |
| Time to check tomorrow's plans (`plan_check_hour`) | 19 | |
| Bring up a task kept for "some Saturday morning" (`task_nudges`) | on | When such a morning comes round and the calendar is free for the hour ahead: each task once a week at most, and one a day in each chat |
| Say in the chat when an idea is filled in (`enrichment_notes`) | on | A short note with what was found |

## When something needs fixing

| Setting | Default | What it does |
|---|---|---|
| Tell admins on Telegram (`admin_alerts`) | on | When a company says its account is out of credit or refuses its key, the day's spending limit is used up, or Google stops letting it at the calendar: each admin with a Telegram id is told, and again at most twice a day while it lasts. The Status page lists the same |

## When a message cannot be answered

Folded away, under "When a message cannot be answered". If the model cannot be reached, the message is
kept and tried again later.

| Setting | Default | What it does |
|---|---|---|
| Minutes between retries (`retry_interval_minutes`) | 5 | Between 1 and 1440 |
| Retries before giving up (`retry_max_attempts`) | 3 | Between 0 and 20 |

What each message says, word for word, is on the
[Personality and family](/wiki/controls/settings/personality#what-she-says-unasked) page.
[What it does on its own](/wiki/behavior) lists the jobs that send them.
