# Messages settings

What FamilyDB sends without being asked, and when. The top of the page lists each kind of message
with whether it is on, when it goes, what it costs, how many went in the last 30 days and when the
last one did, and the 20 most recent in full, so you can see what the family is actually receiving. Below that are the settings
that turn each kind on and off and move its time. All times are in the family's time zone.

If there is no key for the AI model yet, the page warns that no weekend ideas will be sent until there is one.

## Weekend ideas

Once a week the assistant asks itself what the family should do at the weekend and sends the answer:
one chat turn a week, which can be a few model calls. Which model does it is set under "The weekend
digest" on the [AI model](/wiki/controls/settings/ai-model#how-strong-a-model-answers) page.

| Setting | Default | What it does |
|---|---|---|
| Weekend ideas go to (`digest_chat_id`) | the page's chat, on a new install | Choose the chat on this page, or one of the Telegram chats it has seen (a group is offered once somebody on the family list has written in it). Anything else you type is treated as a Telegram chat id, and the bot must be in that chat. Empty sends none, and the weekly job does not run |
| Weekend ideas day (`digest_day`) | Thursday | |
| Weekend ideas time (`digest_hour`) | 18 (6 pm) | In the family's time zone |

A new install's `.env` sets this to the page's own chat, because a Telegram group needs someone to write
in it first; saving it on the page overrides that. Move it to the family's Telegram chat once they have.
It also needs an AI key and an admin to ask as. If the chosen Telegram chat cannot be reached, the digest
is skipped and a warning goes in the log. A restart after the hour on the right day still sends it.

## Follow-ups and notes

These are written from the assistant's lines, not thought up by a model, so they cost nothing.

| Setting | Default | What it does |
|---|---|---|
| Ask how a plan went (`follow_ups`) | on | Asked once, for plans that ended before today (up to a week back), with buttons to answer in one tap, so the ideas list learns what you liked. It goes to the chat the plan was made in, or to the person's own chat when that setting is on. Off means nobody is asked; how it went can still be told at any time |
| Time to ask how a plan went (`follow_up_hour`) | 10 | The day after a plan |
| Check tomorrow's plans the evening before (`plan_checks`) | on | Said only when something is off: rain for an outdoor plan (this needs a home position), or the place's saved hours show it closed or not open at the plan's time (this needs hours from a lookup), with another idea for the same time when one fits. It covers only plans for an idea, made in a chat, and each is checked once, so a plan made after that hour the evening before is not checked |
| Time to check tomorrow's plans (`plan_check_hour`) | 19 | |
| Bring up a task kept for "some Saturday morning" (`task_nudges`) | on | On such a morning, from an hour into it, when the next hour is free on the connected calendar (with no calendar, it goes anyway). Each task at most once every six days, and one task a day in each chat. Not for tasks that repeat or have a reminder set, or ones less than 12 hours old. It looks every 15 minutes |
| Say in the chat when an idea is filled in (`enrichment_notes`) | on | A short note with what was found |

## When something needs fixing

| Setting | Default | What it does |
|---|---|---|
| Tell admins on Telegram (`admin_alerts`) | on | When a company says its account is out of credit or refuses its key, the day's spending limit is used up, or Google stops letting it at the calendar, and also when a model name is unknown to its company, a request part was refused, or the daily check finds a model going or a price moved. Each admin with a Telegram id is told, and again after 12 hours at the soonest while it lasts; one is forgotten when the fault clears. Without an admin who has a Telegram id and a connected bot, the Status page is the only place it shows |

## When a message cannot be answered

Folded away, under "When a message cannot be answered". If the model cannot be reached, the message is
kept and tried again later.

| Setting | Default | What it does |
|---|---|---|
| Minutes between retries (`retry_interval_minutes`) | 5 | How often the retry job looks, so a message may wait up to this long for a try. Between 1 and 1440 |
| Retries before giving up (`retry_max_attempts`) | 3 | 0 gives up at once. Between 0 and 20 |

What each message says, word for word, is on the
[Personality and family](/wiki/controls/settings/personality#what-she-says-unasked) page.
[What it does on its own](/wiki/behavior) lists the jobs that send them.
