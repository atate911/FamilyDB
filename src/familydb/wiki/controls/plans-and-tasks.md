# Plans and To do

The Plans page shows what is on the family calendar and lets a parent add, move and cancel [plans](/wiki/reference/glossary#plan). The To do page lists the family's [things to do](/wiki/reference/glossary#thing-to-do) and their reminders, and lets people add, edit and tick them off.

## Who sees what

| Who | Plans | To do |
|---|---|---|
| Admin, parent | The month and the list, and the forms to add, move, cancel and rate | Everybody's things to do, filters, search, and every form |
| Kid | One list, "What the family is doing next", with no forms. The month opens if they type it | "My to-dos": only their own open ones, to tick off (and undo for a week). They ask the assistant to add or change one |
| Anyone on the shared password | Everything | Everything |

Who may change what is in [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions). The lists and the month leave out plans for a present hidden from you, and the To do page leaves out things to do about one ([Presents](/wiki/model/ideas-and-places#presents)). So do the **How did it go?** prompt and its "to rate" count.

## Plans

The month is a calendar, then **Coming up** and **How did it go?**. The list shows the next 90 days by month, then **Recently** (the last 30 days) and the add form. The note at the top says where the plans came from:

| Note | Meaning |
|---|---|
| From Google Calendar | Everything on the calendar, including events added in Google, tagged "added in Google" with no Move or Cancel. Google's answer is kept for 1 minute, unless FamilyDB has written to the calendar since |
| Google Calendar is not connected | The plans FamilyDB has saved |
| Google Calendar did not answer | The plans as FamilyDB last saw them, so times may have moved |

### Add a plan

On the list, open **Put something on the calendar** (**Add something to the plans** with no calendar), give what, when (or all day) and where, and save. A timed plan lasts 2 hours. To plan an idea, use **Plan it** on its page: the plan links to it and the idea becomes Planned.

### Move a plan

On the list, choose **Move it**, set the new time, and save. It keeps its length, unless you switch between timed and all day.

### Cancel a plan

On the list, choose **Cancel it**, then **Yes, cancel it**. If its idea was Planned, it goes back to "An idea".

> **Canceling deletes the event from Google Calendar for everyone.** FamilyDB keeps the plan marked canceled but cannot bring the event back: add a new plan instead.

### Rate a plan

On the month, under **How did it go?**, choose Loved it, OK or Not great. These record 9, 6 and 3 out of ten. The prompt asks about confirmed plans linked to an idea that ended in the last 14 days and have no rating, and counts them as "to rate" beside Plans.

### Rules for plans

- A time before now, or an all-day date before today, is refused, for adding and moving.
- Only plans FamilyDB made can be moved or canceled on the page. An event added in Google is changed in Google, or by asking the assistant.
- With no calendar, a plan is saved in FamilyDB alone and the page says so. Once a calendar is connected, FamilyDB copies the plan across the next time a calendar tool runs, and until then it does not show on the page.
- If someone moves or deletes the event in Google, the page shows that within 1 minute. FamilyDB's own copy follows the next time it acts on the plan, and a deleted event cancels it.
- A plan made on the page has no chat, so it gets no day-after question or evening-before check on Telegram. **How did it go?** is its only prompt ([Plans made on the page get no follow-up](/wiki/reference/known-limits#plans-made-on-the-page-get-no-follow-up)).

## To do

Each tab, **Open**, **Done**, **Canceled** or **All**, lists at most 100, soonest deadline first, and search matches words inside titles and notes. Open ones are grouped **Overdue** (the deadline's day has passed, in the family's time zone), **Coming up** and **No date**. A row shows the tick, title, who, when, the reminder (Scheduled, Waiting for delivery or Delivered) and any window or repeat.

### Add a thing to do

Type what needs doing and choose **Add**. Under "Who, when, reminder", choose who it is for, a deadline, a preferred window, a reminder time and a repeat. It is for you unless you choose someone else.

### Edit a thing to do

Choose **Edit** for its own page: change any box, set Status, or choose **Cancel the pending reminder**. A new reminder time snoozes it. Emptying the deadline clears it.

### Tick it off

Choose the tick. **Undo** on a done one reopens it. To cancel one, use Edit; a canceled one can be set back to Open. Reopening does not restore its reminders.

### Rules for To do

- A deadline sets no reminder and a window books nothing. Only a reminder time sends one.
- The repeat choices are every day, week, 2 weeks, month, 3 months, 6 months or year, and a repeat needs a first reminder. By default it keeps its schedule from that first reminder. With **Count from when it's done**, the next comes that long after each tick. Done on a repeating thing records this time round and keeps it coming; canceling ends it ([Repeats](/wiki/model/tasks-and-reminders#repeats)).
- A window such as "Saturday morning" is read in code from a short word list. A window that does not read is kept but never nudged ([Preferred windows and nudges](/wiki/model/tasks-and-reminders#preferred-windows-and-nudges)). The nudge switch is on [Messages](/wiki/controls/settings/messages).
- If someone changed the thing while you had it open, or a reminder is being delivered, FamilyDB refuses the edit: reload and try again. A double click adds one thing.
- A reminder made on the page appears in the page's Chat while FamilyDB is running. It does not reach Telegram or phones ([How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered)).

## Birthdays and the same from chat

A thing to do can name whose birthday or anniversary it is. The page's forms have no box for this: ask the assistant in chat, and its reminder lists gift ideas for that person (kept from anyone who may not see them).

Every form here runs the same tool the assistant runs, so you can ask for any of this in chat. `/today`, `/week`, `/tasks` and the buttons under a reminder are on [Telegram](/wiki/controls/telegram). An admin connects the calendar under [Connections](/wiki/controls/settings/connections#google-calendar) and checks the time zone on [General](/wiki/controls/settings/general); a wrong one moves every reminder.

How plans and the calendar stay in step is on [Plans and the calendar](/wiki/model/plans-and-calendar), and reminders and repeats are on [Things to do and reminders](/wiki/model/tasks-and-reminders).
