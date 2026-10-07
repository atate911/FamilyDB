# Things to do and reminders

A [thing to do](/wiki/reference/glossary#thing-to-do) is an obligation the family wants kept in mind, and a reminder is the one message that brings it back at a time. This page explains how they are kept, how repeats and preferred windows work, and when FamilyDB sends a reminder or a nudge. For the screens, see [Plans and To do](/wiki/controls/plans-and-tasks).

A thing to do is not a plan. It puts nothing on the calendar, and it can have no date at all. See [plans and the calendar](/wiki/model/plans-and-calendar) for commitments with a time.

## What is kept

| Part | What it holds |
|---|---|
| Status | open, done or cancelled |
| Deadline | A date and time it is due. It sets no reminder |
| Owner | Who it is for: an active family member, the person who asked unless someone else is named |
| Set by | Who asked for it, shown on a kid's to-do |
| Preferred window | Words such as "some Saturday morning" |
| Repeat | How often it comes round, and from when |
| Gift for | Whose birthday or anniversary it is |
| Idea | The idea it is about |
| Chat | The chat it was asked in, which is where its reminders go |

A reminder is a separate record: a time, a mark when its message is queued, and a mark when it is cancelled. A new reminder time on a thing to do replaces the live one, which is a snooze.

Done on a one-off, and cancelled, both cancel the reminder and any reminder message not yet sent. Reopening does not bring the reminder back, and a reminder can only be set on an open thing to do. An edit is refused while a reminder is being delivered, and when the thing to do changed since the form was opened (each change bumps a revision number).

Times are given in the family time zone. A reminder must be in the future. A local time that does not exist, or happens twice, on a clock-change night is refused rather than guessed.

## Who it is for

A parent or admin may change any thing to do, and a kid only their own. Making one is not restricted that way: a kid can make a thing to do and name another owner. The owner also decides where a reminder goes when the thing to do began in a Telegram group (see below).

## Repeats

A thing to do repeats every 1 to 400 days, weeks, months or years, and needs a first reminder. There are two ways to count.

| Counted | The next reminder comes |
|---|---|
| From the schedule (the default) | At the first reminder's hour, on whole intervals from the first reminder |
| From when it was done | One interval after the day somebody ticks it, at the first reminder's hour |

On a schedule, the next reminder is added when each due reminder is queued, just before it is sent, as the first time still to come. Ticking Done on a scheduled repeat also adds the next one if none is waiting. A snooze does not move the schedule, and a stretch with FamilyDB off sends one late reminder, not a flood. Times follow the family's wall clock, so a reminder keeps its hour when the clocks change, and one set for the 31st lands on the last day of a shorter month without drifting.

**Done** on a repeating thing to do records this time round (its last-done time) and leaves it open, so it keeps coming. **Cancel** ends it. Setting a new reminder time alone snoozes this round only. Stopping the repeat makes it a one-off. The choices the page offers are on [Plans and To do](/wiki/controls/plans-and-tasks).

## Preferred windows and nudges

A preferred window is kept as said. So FamilyDB can bring the thing to do up by itself, code reads it against a short list of words. If it reads, the thing to do is nudged when the window comes round. If any word is not on the list, or there is any digit, it is not read at all, and no nudge ever comes.

| Kind | Words read |
|---|---|
| Days | Monday to Sunday, their plurals, weekend, weekdays |
| Parts of a day | morning (08:00 to 12:00), afternoon (12:00 to 17:00), evening (17:00 to 22:00), night as evening |
| Both | weeknight, weeknights: weekday evenings |
| Ignored | a, an, and, any, of, one, or, some, the, these, those, at, day, days, during, in, on, over, sometime, time, week, free, quiet, spare |

No day named means every day. No part means 08:00 to 22:00. "Before Christmas", "after school" and "next Saturday" are not read. The assistant promises a nudge only for a window that reads, saying "on a free Saturday morning", and promises nothing otherwise.

A nudge goes out when all of these hold:

- The thing to do is open, has a readable window, does not repeat, and has no reminder still waiting to go.
- It was made at least 12 hours ago.
- It has not been nudged in the last six days, so about once a week.
- No other thing to do in the same chat has been nudged since midnight, so one a day per chat. Ones never nudged go first, then the longest ago.
- The window is open now: from an hour into the part of the day to an hour before it ends.
- With a calendar answering, the next 60 minutes are free. A busy all-day event blocks the day. With no calendar, or none answering, it goes anyway.
- Its channel (Telegram or the page's Chat) can send.

A nudge carries the same buttons as a reminder and goes to the owner's own chat when it began in a group. It uses no model call. It is switched by `task_nudges` on [Messages](/wiki/controls/settings/messages).

## How a reminder is delivered

A job runs every minute (schedule on [jobs](/wiki/behavior/jobs)). For each open thing to do whose reminder has come, it stores the reminder message, attaches it, adds the next time for a repeat, and sends it. If the family is mid-conversation, the message waits to ride the next reply, and the job sends whatever no reply carried. A failed send is left to the retry job. No model is asked.

- **Late.** A reminder sent more than 10 minutes after its time says when it was due.
- **Buttons.** **Done** ticks it. **In an hour** and **Tomorrow** snooze it, one hour or one day on from the tap. A tap acts as the person who tapped.
- **Where it goes.** The chat the thing to do was asked in. One made on the page, or in the console, belongs to the page's Chat: it appears there while FamilyDB runs, and reaches no phone. To get it on Telegram, ask the assistant in the Telegram chat.
- **Groups.** A reminder for a thing to do with an owner, asked in a Telegram group, goes to the owner's own chat once they have written to the bot, so the group is not sent somebody's errand. One with no owner stays in the group. `private_when_personal` on [Connections](/wiki/controls/settings/connections) switches this off.

## Birthdays and gift ideas

A birthday or anniversary is a thing to do, usually repeating yearly, with *gift for* set to the person. Its reminder lists up to five open gift ideas (status idea or planned) that name them in the idea's *For*, newest first, or says there are none. If the person is on the family list, the reminder also lists their birthday wish list. The page has no box for *gift for*: ask the assistant in chat.

Presents are listed only where everyone reading may see them. If a kid, or the person a present is hidden from, reads the chat, the reminder leaves presents and wishes out altogether, rather than saying there are none. See [ideas and places](/wiki/model/ideas-and-places) and [wish lists](/wiki/model/wishes).

## A thing to do and an idea

A thing to do can name the idea it is about, such as the present it is to buy. This is set when it is made, and the assistant can set it. A thing to do about a present is hidden from whoever the present is hidden from, on the pages and in the assistant's lists.

Developer docs: `src/familydb/task_service.py`, `windows.py`, `presents.py`; `tools/tasks.py`; `jobs/reminders.py`, `jobs/nudges.py`; `store/tasks.py`; `buttons.py`; `routing.py`; `docs/DESIGN.md`, "Tasks, reminders and free-form capture".
