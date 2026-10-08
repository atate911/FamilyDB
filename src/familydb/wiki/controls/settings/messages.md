# Messages

The Messages card sets what FamilyDB sends without being asked, and when. The top of the card lists each kind of message with whether it is on, when it goes, what it costs, how many went in the last 30 days and when the last one did; below that are the 20 most recent in full. The settings under it turn each kind on or off and move its time. All times are in the family's time zone.

With no key for a model yet, the card warns that no weekend ideas are sent until there is one.

## Weekend ideas

Once a week the assistant asks itself what the family should do at the weekend and sends the answer: one chat turn a week, which can be a few model calls. The model level for it is **The weekend digest** (`digest_level`) on [AI model](/wiki/controls/settings/ai-model#how-strong-a-model-answers).

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Weekend ideas go to (`digest_chat_id`) | none; a new install sets the web page's chat | Where the weekend ideas go. Empty sends none, and the weekend ideas job does nothing. | A chat from the list, or a Telegram chat id |
| Weekend ideas day (`digest_day`) | Thursday | The day they are sent. | Monday to Sunday |
| Weekend ideas time (`digest_hour`) | 18 (6 pm) | The hour they are sent. | 0 to 23 |

The installer sets the first one to the web page's own chat, because a Telegram group needs somebody to write in it first. Saving a choice on the card overrides that. Move it to the family's Telegram chat once they have written there. A group is offered once somebody on the family list has written in it; anything else you type is treated as a Telegram chat id, and the Telegram bot must be in that chat.

Weekend ideas also need a model key and an admin on the family list to ask as. If the chosen Telegram chat cannot be reached, FamilyDB skips them and writes a warning in the log. After a restart on the right day and past the hour, the [catch-up](/wiki/reference/glossary#catch-up) still sends them.

## Follow-ups and notes

FamilyDB words these from the assistant's lines, not a model, so they cost nothing.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Ask how a plan went (`follow_ups`) | on | Asks once for each plan that ended before today (up to a week back), with buttons to answer in one tap, so the ideas list learns what you liked. Off means nobody is asked; how it went can still be told at any time. | on or off |
| Time to ask how a plan went (`follow_up_hour`) | 10 | The hour of the day after a plan. | 0 to 23 |
| Check tomorrow's plans the evening before (`plan_checks`) | on | Speaks only when something is off, with another idea for the same time when one fits. Also covers a plan of today that has not begun. | on or off |
| Time to check tomorrow's plans (`plan_check_hour`) | 19 | The hour of the evening before. The check runs every hour from then to 22:00, so a plan made later that evening is still checked. | 0 to 23 |
| Bring up a task kept for "some Saturday morning" (`task_nudges`) | on | Brings a task up when its part of the week comes round and the calendar is free. | on or off |
| Say in the chat when an idea is filled in (`enrichment_notes`) | on | Sends a short note with what a lookup found. | on or off |

The follow-up goes to the chat the plan was made in, or to the person's own chat when **Send what's for one person to them** (`private_when_personal`) is on.

The evening check names two things that are off: rain for an outdoor plan (needs a home position), or a place whose saved hours show it closed at the plan's time (needs hours from a lookup). It covers only plans for an idea, made in a chat, and checks each once. It runs every hour from the check's hour to 22:00, so a plan made late in the evening is still checked. It also checks a plan of today that has not begun, worded for today, which catches one whose evening was missed because nothing could send to its chat; a plan of today that has begun is skipped.

Nudges follow the rules in [Preferred windows and nudges](/wiki/model/tasks-and-reminders#preferred-windows-and-nudges); the nudges job looks every 15 minutes. Where a reminder goes is in [How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered).

## Each morning

Once a morning FamilyDB sends one message in each chat that has something for it, and none on an empty day. It is written from the lines in code, not by a model, so it costs nothing. A chat gets at most one a day, and it is never held back to ride on a reply.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Time of the morning message (`morning_hour`) | 7 (7 am) | The hour it goes, in the family's time zone. After a restart it still goes, until noon. | 0 to 23 |
| The day ahead (`morning_agenda`) | on | Today's plans, reminders and deadlines, and an idea with dates that ends this week when a free day could fit it (said once). | on or off |
| A reminder nobody acted on, once more (`chase_missed`) | on | The morning after a reminder went and was neither done nor snoozed, once, with a button to tick it off. | on or off |
| What is due tomorrow (`deadline_heads_up`) | on | The morning before a deadline, so it is not missed for want of a reminder. | on or off |
| What has waited a week or more (`forgotten_roundup`) | on | Once a week, the things to do a week old or more that have no reminder or time to bring them up, 5 at most. | on or off |
| Day of the week for that (`roundup_day`) | Sunday | The day the round-up goes, in that day's morning message. | Monday to Sunday |

With all four parts off, no morning message is sent. The plans for the day go to the family's chat ([The family's chat](/wiki/controls/settings/connections#in-a-telegram-group)); each reminder, deadline and forgotten thing goes where that thing's reminders go, so a person's own things reach them and the web page's shared conversation gets one message with all of it. Where a kid reads, it is said plainly and never names a birthday's thing to do or a present's plan. Each part is counted on the card's list, and reminders are described in [Things to do and reminders](/wiki/model/tasks-and-reminders).

## On phones and tablets

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Say when she has written (`web_push`) | on | Lets a person who uses only the web page turn on a notice, for their own device, that the assistant has a message. Off removes the setting from every person's **Your password** page and sends none. | on or off |

Each person turns notices on for their own device under **Your password** ([Look and your password](/wiki/controls/look-and-password#your-password)), in the card **Notifications on this device**. The notice says only that the assistant has a message, never the words. It goes only for a message the assistant sent of her own accord (a reminder, the morning message), once it is delivered, to the devices of the people who read that conversation: a kid's own conversation reaches that kid's devices, and the family's reaches the devices of whoever may decide, parents and admins.

Apple's, Google's or Mozilla's push service carries the notice and sees the device's address and when it was sent, not the words. On an iPhone or iPad the web page must be added to the Home Screen first. A notice that fails is logged and forgotten, and never changes whether the message counts as delivered; a device the browser has let go is taken off.

## When something needs fixing

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Tell admins on Telegram (`admin_alerts`) | on | Sends each admin with a Telegram id the troubles on the list below. Off sends none; Status still shows them. | on or off |

FamilyDB tells every admin with a Telegram id within a minute, and again after 12 hours at the soonest while the trouble lasts. It forgets one when the thing works again, and shows the same list under Needs a look on [Status](/wiki/controls/status#needs-a-look). With no admin who has a Telegram id and a connected Telegram bot, Status is the only place a trouble shows. The troubles:

- A model company says the account is out of credit.
- A model company refuses the key.
- The day's spending limit is used up.
- Google Calendar refuses the key, or none is saved.
- Google Calendar no longer shows the calendar, for example because it is no longer shared with the service account.
- A model in use is going away, or its name is unknown to the company.
- A price moved, or the price lists could not be checked.
- New models to choose from, or a big move in what the calls cost or do (once a week for each kind of call).
- A model company stopped taking part of a request, or keeps refusing requests for a reason FamilyDB cannot read (told on the second refusal).
- A calendar or other source of [what is on near home](/wiki/controls/settings/happening) could not be read for 3 days running, or new calendars were found to tick.
- A judgment changed the models, when [judgments](/wiki/controls/settings/ai-model#asking-a-stronger-model-to-weigh-a-change) are on.

## When a message cannot be answered

Folded away on the card, under "When a message cannot be answered". If the model cannot be reached, FamilyDB keeps the message and the retry job tries again later.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Minutes between retries (`retry_interval_minutes`) | 5 | How often the retry job looks, so a message waits up to this long for a try. | 1 to 1440 |
| Retries before giving up (`retry_max_attempts`) | 3 | Tries after the first one. 0 gives up at once. | 0 to 20 |

A message is **failed** while it will be retried and **given up** when it will not be tried again ([Failed and given up](/wiki/reference/glossary#failed-and-given-up)); with the defaults that is the first try plus 3 retries. While FamilyDB answers a message it holds a [lease](/wiki/reference/glossary#lease) on it, a claim that runs out after 5 minutes if the program stops, so the retry job can pick it up and nobody is answered twice. The steps a message goes through are in [From message to reply](/wiki/behavior/message-to-reply); the replies the family sees are in [Troubleshooting](/wiki/operations/troubleshooting#a-message-got-no-reply). What each unprompted message says, word for word, is under [Personality and family](/wiki/controls/settings/personality#what-she-says-unasked), and [What it does on its own](/wiki/behavior) lists the jobs that send them.
