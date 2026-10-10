# Week, Soon, Lists and Did

Four destinations read the calendar, the [things to do](/wiki/reference/glossary#thing-to-do) and the family's lists. **Week** is this week a day at a time, with the reminders due and what is on your plate. **Soon** is what is on near home in the weeks ahead. **Lists** is the shopping list and the family's other lists. **Did** is what we did and how it went. Each opens on its answer with no model call, and the box on each is about it.

## Who sees what

| Who | Week | Soon and Lists | Did |
|---|---|---|---|
| Admin, parent | Everybody's plans, the plate, the pencil pick, each person's chip, Month and Past; the forms to move, take off and rate | Everything | Everything, and the faces for what is still to rate |
| Kid | **My week**: the family's plans and her own things to do, which she ticks off herself; no plate, no pencil, no forms. She asks the assistant to add or change one | Not in her row | What we did, with no faces |
| Anyone on the shared password | Everything | Everything | Everything |

Who may change what is in [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions). Every page leaves out plans for a present hidden from you, and things to do about one ([Presents](/wiki/model/ideas-and-places#presents)). So do **How did it go?** and its "to rate" count.

## Week

Seven days from today, each under its own heading (Today, Tomorrow, then the day's name): what is on, as a row with its time and who it is for; the free time in words ("Free till 5 pm, then from 8 pm"); the forecast where there is one; the reminders due that day, each a link to its page; and, on a free weekend stretch, one of the assistant's picks in pencil, with Plan it. The line under the question sums it up: "Tomorrow: free till 5 pm, then from 8 pm · 2 on your plate, 1 late".

**On your plate**, for a grown-up, is what has no day yet and what is late, each with its tick, and **I'll handle it** under one that is everyone's, which makes it yours (signed in as yourself; the same as saying so to the assistant); **All to-dos** opens the full list. The chips narrow the week to one person; **Month** opens the month, **Past** the plans that are over. **Earlier** and **Later** move a week, **This week** comes back. A day's heading opens the day on its own, with everything on it and, after it, how it went. The note at the foot says where the plans come from:

| Note | Meaning |
|---|---|
| From Google Calendar | Everything on the calendar, including events added in Google, which have no Move or Take off. Google's answer is kept for 1 minute, unless FamilyDB has written to the calendar since |
| Google Calendar is not connected | The plans FamilyDB has saved |
| Google Calendar did not answer | The plans as FamilyDB last saw them, so times may have moved |

### Plans

A plan's row opens its page: when, in words and how far off; the time to leave, from the drive; who and where; what it is a plan of, linking to the place; and after the day, how it went, or the faces to say. **Move it** and **Take it off the calendar** are folded under it, for whoever may change things.

- **Add a plan.** Tell the assistant ("put the zoo on Saturday at 10"), use **Plan it** on a place's page, or **Put something on the calendar by hand** at the foot of Week (**Add something to the plans** with no calendar). A timed plan lasts 2 hours.
- **Move a plan.** Open it, open **Move it**, set the new time, and save. It keeps its length, unless you switch between timed and all day.
- **Take a plan off.** Open it, open **Take it off the calendar**, then **Yes, take it off**. If its place was Planned, it goes back to "An idea".

> **Taking a plan off deletes the event from Google Calendar for everyone.** FamilyDB keeps the plan marked canceled but cannot bring the event back: add a new plan instead.

- **Rate a plan.** On Now, on Did, on the day's page or the plan's own, choose Loved it, OK or Not great. These record 9, 6 and 3 out of ten. The question asks about confirmed plans linked to an idea that ended in the last 14 days and have no rating, and counts them as "to rate" on Did.

### Rules for plans

- A time before now, or an all-day date before today, is refused, for adding and moving.
- Only plans FamilyDB made can be moved or taken off on the page. An event added in Google is changed in Google, or by asking the assistant.
- With no calendar, a plan is saved in FamilyDB alone and the page says so. Once a calendar is connected, FamilyDB copies the plan across the next time a calendar tool runs, and until then it does not show on the page.
- If someone moves or deletes the event in Google, the page shows that within 1 minute. FamilyDB's own copy follows the next time it acts on the plan, and a deleted event cancels it.
- A plan made on the page has no chat, so it gets no day-after question or evening-before check on Telegram. **How did it go?** is its only prompt ([Plans made on the page get no follow-up](/wiki/reference/known-limits#plans-made-on-the-page-get-no-follow-up)).

### To do

A reminder's page says when, whose, the window it suits, how it repeats and where it is sent, with **Done**, **In an hour** and **Tomorrow** under it, the buttons a reminder carries in the chat, by code; a done one offers **Not done after all**. The box is about the reminder, with three sentences that fill it ("Move it to Saturday", "Remind me the evening before", "Make it weekly"). **Edit by hand** is folded last: change any box, set Status, or choose **Cancel the pending reminder**; a new reminder time snoozes it, and emptying the deadline clears it.

**All to-dos** is the full list. Each tab, **Open**, **Done**, **Canceled** or **All**, lists at most 100, soonest deadline first, and search matches words inside titles and notes. Open ones are grouped **Overdue** (the deadline's day has passed, in the family's time zone), **Coming up** and **No date**. A row shows the tick, title, who, when, the reminder (Scheduled, Waiting for delivery or Delivered) and any window or repeat. To add one by hand, type what needs doing there and choose **Add**; under "Who, when, reminder", choose who it is for, a deadline, a preferred window, a reminder time and a repeat. It is for you unless you choose someone else. Telling the assistant is the usual way: "remind me Tuesday at 5 to call the dentist".

**Tick it off** on Now, Week, the list or its own page. **Undo** beside the receipt reopens it. To cancel one, use Edit by hand; a canceled one can be set back to Open. Reopening does not restore its reminders.

### Rules for reminders

- A deadline sets no reminder and a window books nothing. Only a reminder time sends one.
- The repeat choices are every day, week, 2 weeks, month, 3 months, 6 months or year, and a repeat needs a first reminder. By default it keeps its schedule from that first reminder. With **Count from when it's done**, the next comes that long after each tick. Done on a repeating thing records this time round and keeps it coming; canceling ends it ([Repeats](/wiki/model/tasks-and-reminders#repeats)).
- A window such as "Saturday morning" is read in code from a short word list. A window that does not read is kept but never nudged ([Preferred windows and nudges](/wiki/model/tasks-and-reminders#preferred-windows-and-nudges)). The nudge switch is on [Messages](/wiki/controls/settings/messages).
- If someone changed the thing while you had it open, or a reminder is being delivered, FamilyDB refuses the edit: reload and try again. A double click adds one thing.
- A reminder made on the page appears in the page's chat while FamilyDB is running. It does not reach Telegram or phones ([How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered)).

## Soon

What is on near home in the weeks ahead, by day, with the family's own things that have a closing date among them and the free time on each day. It is read from the family's sources, the calendars and the listings set on [its settings page](/wiki/controls/settings/happening), with no model call. The chips are **This weekend**, **Free** (only days with free time) and each source.

Each find has a page of its own: its day, place and cost, the listing in its own words and a link to it, and who listed it. **Save it** keeps it as an idea with its dates and place (the tool the assistant would call); **Put it on the calendar** adds it as a plan. Once it is over, the page says so.

## Lists

The shopping list, always, and the family's other lists as chips, each at its own address (`/lists/costco`). Each thing is a big tick; **Got** folds what was ticked, where a thing can be put back; **Add something** adds. Every tick and add is the same tool the assistant runs for "we need milk", and the kids are told what is on a list when they ask. `/list` on Telegram reads it.

## Did

What we did, newest first: each outing with its face (Loved it from 8 out of ten, OK from 5, Not great below), when, who went and the note. What is still to rate comes first, with the faces to say. **Loved** keeps only the loved ones; **Favorites** shows one row a place the family loved on average, with how many times; **This time last year** shows the month either side of the day a year ago; each person's chip, what they were at.

Each outing opens a page of its own: when, who went, how it went out of ten and whether they would go again, the words said about it and who recorded it, and the other times at the same place. **What made it good?** offers a few chips (An early start, A friend came, Short, Cheap, Close to home, Outdoors); a tap becomes something the assistant remembers about the family, which you can see and forget on [What Vera knows](/wiki/controls/memory). **Again?** puts the place back among the things to do.

## Birthdays and the same from chat

A thing to do can name whose birthday or anniversary it is. The page's forms have no box for this: ask the assistant, and its reminder lists gift ideas for that person (kept from anyone who may not see them).

Every form here runs the same tool the assistant runs, so you can ask for any of this from the box on any page. `/today`, `/week`, `/tasks` and the buttons under a reminder are on [Telegram](/wiki/controls/telegram). An admin connects the calendar under [Connections](/wiki/controls/settings/connections#google-calendar) and checks the time zone on [General](/wiki/controls/settings/general); a wrong one moves every reminder.

How plans and the calendar stay in step is on [Plans and the calendar](/wiki/model/plans-and-calendar), and reminders and repeats are on [Things to do and reminders](/wiki/model/tasks-and-reminders).
