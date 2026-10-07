# Plans and To do

The Plans page shows what is on the family calendar and lets a parent add, move and cancel [plans](/wiki/reference/glossary#plan). The To do page lists the family's [things to do](/wiki/reference/glossary#thing-to-do) and their reminders, and lets people add, edit and tick them off.

## Who sees what

| Who | Plans | To do |
|---|---|---|
| Admin, parent | The month and the list, and the forms to add, move, cancel and rate | Everybody's things to do, filters, search, and every form |
| Kid | One list, "What the family is doing next", with no forms. The month opens if they type it | "My to-dos": only their own open ones, to tick off (and undo for a week). They cannot add or edit on the page; they ask the assistant |
| Anyone on the shared password | Everything | Everything |

Who may change what is in [the roles table](/wiki/security#who-may-do-what). The lists and the month leave out plans for a present hidden from you, and the To do page leaves out things to do about one. The **How did it go?** prompt and its "to rate" count do not apply this, so a grown-up can see a hidden present's plan there.

## Plans

**The month** is a calendar, then **Coming up** and **How did it go?**. **The list** shows the next 90 days by month, then **Recently** (the last 30 days) and the add form. The note at the top says where the plans came from:

| Note | Meaning |
|---|---|
| From Google Calendar | Everything on the calendar, including events added in Google, tagged "added in Google" with no Move or Cancel. Google's answer is kept for one minute, unless FamilyDB has written to the calendar since |
| Google Calendar is not connected | The plans FamilyDB has saved |
| Google Calendar did not answer | The plans as FamilyDB last saw them, so times may have moved |

### What you can do

1. **Add a plan.** On the list, open **Put something on the calendar** (**Add something to the plans** with no calendar), give what, when (or all day) and where, and save. A timed plan lasts two hours. To plan an idea, use **Plan it** on its page: the plan links to it and the idea becomes Planned.
2. **Move a plan.** On the list, choose **Move it**, set the new time, and save. It keeps its length, unless you switch between timed and all day.
3. **Cancel a plan.** On the list, choose **Cancel it**, then **Yes, cancel it**. If its idea was Planned, it goes back to "An idea".
4. **Rate a plan.** On the month, under **How did it go?**, choose Loved it, OK or Not great.

**Cancelling deletes the event from Google Calendar for everyone.** FamilyDB keeps the plan marked canceled but cannot bring the event back: add a new plan instead.

### The rules that matter

- A time before now, or an all-day date before today, is refused, for adding and moving.
- Only plans FamilyDB made can be moved or cancelled on the page. An event added in Google is changed in Google, or by asking the assistant.
- With no calendar, a plan is saved in FamilyDB alone and the page says so. Once one is connected, the plan is copied across the next time a calendar tool runs, and until then it does not show on the page.
- If someone moves or deletes the event in Google, the page shows that within a minute; FamilyDB's own copy follows the next time it acts on the plan, and a deleted event cancels it.
- **Rating:** Loved it, OK and Not great record 9, 6 and 3 out of ten. It asks about confirmed plans linked to an idea that ended in the last 14 days and have no rating, and counts them as "to rate" beside Plans. The day-after question and the evening-before check go only to the chat a plan was made in (Telegram or the page's Chat; see [Messages](/wiki/controls/settings/messages)). A plan made on the page has no chat, so **How did it go?** is its only prompt.

## To do

Each tab, **Open**, **Done**, **Canceled** or **All**, lists at most 100, soonest deadline first, and search matches words inside titles and notes. Open ones are grouped **Overdue** (the deadline's day has passed, in the family's time zone), **Coming up** and **No date**. A row shows the tick, title, who, when, the reminder (Scheduled, Waiting for delivery or Delivered) and any window or repeat.

### What you can do

1. **Add one.** Type what needs doing and choose **Add**. Under "Who, when, reminder", choose who it is for, a deadline, a preferred window, a reminder time and a repeat. It is for you unless you choose someone else.
2. **Edit one.** Choose **Edit** for its own page: change any box, set Status, or choose **Cancel the pending reminder**. A new reminder time snoozes it. Emptying the deadline clears it.
3. **Tick it off.** Choose the tick. **Undo** on a done one reopens it. Cancel from Edit; a canceled one can be set back to Open.

### The rules that matter

- A deadline sets no reminder and a window books nothing; only a reminder time sends one.
- **A repeat** is every day, week, 2 weeks, month, 3 months, 6 months or year, and needs a first reminder. By default it keeps its schedule from that first reminder. With **Count from when it's done**, the next comes that long after each tick. Done on a repeating thing records this time round and keeps it coming; canceling ends it. Times follow the family's time zone, so a reminder keeps its hour when the clocks change.
- **A window** such as "Saturday morning" is read in code from days, weekend, weekdays, morning, afternoon, evening, night and weeknights, plus fillers like "some" and "one of these". Any other word, or any digit ("before Christmas", "next Saturday"), and it is not read. The row says so only while the switch below is on, and the thing to do is brought up only when asked about.
- **Bringing one up:** a readable window, no reminder still to come, no repeat and at least 12 hours old, and the assistant mentions it when the window comes round, from an hour into the part (morning 8 to 12, afternoon 12 to 5, evening 5 to 10) until an hour before its end. With a calendar connected, it waits until the next hour is free. Each is mentioned about once a week at most, and one a day per chat. A thing to do with no window and no reminder is never raised unprompted. The switch is on [Messages](/wiki/controls/settings/messages).
- Reopening does not restore reminders. An edit is refused while a reminder is being delivered, or if someone changed the thing while you had it open: reload and try again. A double click adds one thing.
- **A reminder made on the page appears in the page's Chat** while FamilyDB is running. It is not sent to Telegram or to phones. To get one on Telegram, ask the assistant in the Telegram chat. The page alone (`familydb web`) runs no jobs and sends none.

## Presents and gift ideas

A thing to do can name whose birthday or anniversary it is. Its reminder lists up to five open gift ideas for that person, and their birthday wish list. If anyone reading (a kid, or the person a present is hidden from) could not see them, the reminder leaves presents out altogether. The page's forms have no box for this: ask the assistant in chat.

## Telegram, chat and admins

The forms run the tools the assistant runs (`create_event`, `update_event`, `delete_event`, `add_task`, `update_task`), so you can ask for any of this in chat. `/today`, `/week`, `/tasks` and the buttons under a reminder are on [Telegram](/wiki/controls/telegram). Admins connect the calendar under [Connections](/wiki/controls/settings/connections) and check the time zone on [General](/wiki/controls/settings/general); a wrong one moves every reminder.

Developer docs: `src/familydb/agenda.py`, `calendar_sync.py`, `task_service.py` and `windows.py`; `src/familydb/web/edits.py`; `src/familydb/tools/gcal.py` and `tasks.py`; and `docs/DESIGN.md`, "Tasks, reminders and free-form capture".
