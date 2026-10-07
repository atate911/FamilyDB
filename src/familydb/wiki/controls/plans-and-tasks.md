# Plans and To do

The Plans page shows what is on the family calendar and lets a parent add, move and cancel [plans](/wiki/reference/glossary#plan). The To do page lists the family's [things to do](/wiki/reference/glossary#thing-to-do) and their reminders, and lets people add, edit and tick them off.

## Who sees what

| Who | Plans | To do |
|---|---|---|
| Admin, parent | The month and the list, and the forms to add, move and cancel | Everybody's things to do, filters, search, and every form |
| Kid | One list, "What the family is doing next", with no forms | "My to-dos": only their own open ones. They can tick one off, and undo it for a week, but cannot add or edit on the page. They ask the assistant to add one |
| Anyone on the shared password | Everything | Everything |

Who may change what is in [the roles table](/wiki/security#who-may-do-what). A plan or a thing to do about a present hidden from you does not show.

## Plans

**The month** is a calendar with a bar for each plan, then **Coming up** and **How did it go?**. **The list** shows the next 90 days by month, then **Recently** (the last 30 days) and the add form.

The note at the top says where the page got its plans:

| Note | Meaning |
|---|---|
| From Google Calendar | Everything on the calendar, including events added in Google, tagged "added in Google" with no Move or Cancel. Google's answer is kept for one minute, unless FamilyDB has written to the calendar since |
| Google Calendar is not connected | The plans FamilyDB has saved |
| Google Calendar did not answer | The plans as FamilyDB last saw them, so times may have moved |

### What you can do

1. **Add a plan.** On the list, open **Put something on the calendar** (**Add something to the plans** with no calendar), give what, when (or all day) and where, and save. A timed plan lasts two hours. To plan an idea, open the idea and use **Plan it**: the plan is linked to it and the idea becomes Planned.
2. **Move a plan.** Choose **Move it**, set the new time, and save. It keeps its length.
3. **Cancel a plan.** Choose **Cancel it**, then **Yes, cancel it**. If its idea was Planned, it goes back to "An idea".
4. **Rate a plan.** Under **How did it go?**, choose Loved it, OK or Not great.

**Cancelling deletes the event from Google Calendar for everyone.** FamilyDB keeps the plan marked canceled but cannot bring the event back: add a new plan instead.

### The rules that matter

- A start in the past is refused, for adding and moving.
- Only plans FamilyDB made can be moved or cancelled on the page. An event added in Google is changed in Google, or by asking the assistant.
- With no calendar, a plan is saved in FamilyDB alone and the page says so; it is copied across the next time a calendar tool runs once one is connected.
- If someone moves or deletes the event in Google, the page shows that within a minute, and FamilyDB's own copy follows the next time it acts on the plan. A deleted event cancels the plan.
- **Rating:** Loved it, OK and Not great record 9, 6 and 3 out of ten. The page asks about confirmed plans linked to an idea, ended before today, begun in the last 14 days and not yet rated, and counts them as "to rate" beside Plans. A plan added on the page has no chat to ask in, so it gets no day-after follow-up or evening-before check on Telegram; those cover plans made in chat (see [Messages](/wiki/controls/settings/messages)).

## To do

Tabs show **Open**, **Done**, **Canceled** or **All**, with a search of titles and notes (at most 100). Open ones are grouped **Overdue** (the deadline's day has passed, in the family's time zone), **Coming up** and **No date**. A row shows the tick, title, who, when, the reminder and whether it is Scheduled, Waiting for delivery or Delivered, and any window or repeat.

### What you can do

1. **Add one.** Type what needs doing and choose **Add**. Under "Who, when, reminder", choose who it is for, a deadline, a preferred window, a reminder time and a repeat. It is for you unless you choose someone else.
2. **Edit one.** Choose **Edit** for its own page: change any box, set Status, or choose **Cancel the pending reminder**. A new reminder time snoozes it. Emptying the deadline clears it.
3. **Tick it off.** Choose the tick. **Undo** on a done one reopens it. Cancel from Edit; a canceled one can be set back to Open.

### The rules that matter

- A deadline sets no reminder and a window books nothing; only a reminder time sends one. Every form works once, so a double click adds one thing.
- **A repeat** is every day, week, 2 weeks, month, 3 months, 6 months or year, and needs a first reminder. By default it keeps its schedule from that first reminder. With **Count from when it's done**, the next comes that long after each tick. Done on a repeating thing records this time round and keeps it coming; canceling ends it. Times follow the family's time zone, so a reminder keeps its hour when the clocks change, and one on the 31st lands on a shorter month's last day.
- **A window** such as "Saturday morning" is read in code from days, weekend, weekdays, morning, afternoon and evening, plus fillers like "some" and "one of these". Any other word ("before Christmas", "next Saturday") and it is not read: the row says so, and the thing to do is only brought up when asked about.
- **Bringing one up:** a readable window, no reminder still to come and no repeat, and the assistant mentions it when the window comes round, from an hour into the part (morning 8 to 12, afternoon 12 to 5, evening 5 to 10) until an hour before its end. With a calendar connected, it waits until the next hour is free. Each is mentioned about once a week at most, and one a day per chat. A thing to do with no window and no reminder is never raised unprompted. The switch is on [Messages](/wiki/controls/settings/messages).
- Reopening does not restore reminders. An edit is refused while a reminder is being delivered, or if someone changed the thing while you had it open: reload and try again.
- Reminders from the page appear in the Chat while FamilyDB is running, and in Telegram once it is connected. They are not phone notifications. The page alone (`familydb web`) runs no jobs and sends none.

## Presents and gift ideas

A yearly thing to do for a birthday can name whose it is. Its reminder lists up to five open gift ideas naming that person, only where everyone reading may see them. The page's forms have no box for this: ask the assistant in chat.

## Telegram, chat and admins

The forms run the tools the assistant runs (`create_event`, `update_event`, `delete_event`, `add_task`, `update_task`), so you can ask for any of this in chat. `/today`, `/week`, `/tasks` and the buttons under a reminder are on [Telegram](/wiki/controls/telegram). Admins connect the calendar under [Connections](/wiki/controls/settings/connections) and check the time zone on [General](/wiki/controls/settings/general): a wrong one moves every reminder.

Developer docs: `src/familydb/agenda.py`, `calendar_sync.py`, `task_service.py` and `windows.py`; `src/familydb/web/edits.py`; `src/familydb/tools/gcal.py` and `tasks.py`; and `docs/DESIGN.md`, "Tasks, reminders and free-form capture".
