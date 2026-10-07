# Plans and the calendar

A [plan](/wiki/reference/glossary#plan) is something the family has decided to do on a day, and Google Calendar holds a second copy of it. This page explains how FamilyDB keeps the two in step, what creating, moving and canceling do, how times are stored, and what happens with no calendar. To add or move a plan, use [Plans and To do](/wiki/controls/plans-and-tasks).

## What a plan is

A plan has a title, a start, an optional end, an all-day mark, a place and notes, plus three links: the idea it is for (optional), its Google event, and the chat it was made in. A new plan is *confirmed*. It becomes *tentative* when Google marks the event so, or when a change sets it, and goes back to *confirmed* when Google drops the mark or a change sets it. A canceled plan stays on record.

With a calendar connected, a plan has a Google event. With none, it is a *saved plan*, kept by FamilyDB alone until a calendar is connected.

Making a plan for an idea sets the idea to planned. Canceling the plan, or deleting its event in Google, puts a planned idea back to idea ([Ideas and places](/wiki/model/ideas-and-places)).

## The calendar is the second copy

People move and delete events in Google without telling FamilyDB. So FamilyDB checks a plan against its event before anything acts on it, and the event wins. The check, called the sync, runs:

- when the assistant searches plans or reads the calendar;
- for the one plan, before the assistant edits or moves it (deleting a plan skips this check and goes straight to Google);
- before the evening-before check and before the day-after follow-up.

Viewing a page does not sync. The page reads Google directly and keeps the answer for 1 minute unless FamilyDB has written to the calendar since. With no calendar, or when Google does not answer, it shows the saved plans and says which ([Plans and To do](/wiki/controls/plans-and-tasks)).

The sync asks Google one question for every plan: what changed since last time? Google answers with a *sync token*, a bookmark FamilyDB saves only after the plans are updated, so a failure just reads the same changes again. The first time, or after Google forgets the token, the answer is the whole calendar, and a plan whose event is missing from it counts as deleted.

| Google did | The plan |
|---|---|
| Moved or edited the event | Takes the event's title, time, place, notes and tentative mark |
| Deleted it | Is canceled, and a planned idea goes back to idea |
| Nothing | Is left alone |

Only live plans with an event on the connected calendar are synced: not canceled ones, not ones already followed up, not plans on another calendar. An event added by hand in Google has no plan. It shows on the page, and the assistant can change or delete it by its event id.

## Creating, moving and canceling

- **Create.** FamilyDB refuses a time in the past. With no end, a timed plan lasts 2 hours. A date alone makes an all-day plan. Google gets the plan as an event, and the idea becomes planned.
- **Move.** FamilyDB checks the plan against its own event first. It refuses a new start in the past. A new start keeps the length unless an end is given or all-day is switched. Google is changed, then the plan. A canceled plan cannot be moved, and neither can one on a different calendar.
- **Cancel.** The event is deleted from Google (one already gone counts as done), the plan is marked canceled, and a planned idea goes back to idea.

A retry does not make a second event. Before FamilyDB asks Google, it writes the event's id down, keyed by the request (the message or form it came from, plus title, time and idea). A retry after a crash, a lost answer or a resent form uses the same id and finds the event if Google made it. Without a calendar, asking twice for the same plan finds the one already saved.

## The evening before and the day after

Both run with no model call, once per plan, and wait if Google cannot be asked. When they run is on [The scheduled jobs](/wiki/behavior/jobs), and the path of a message is on [From message to reply](/wiki/behavior/message-to-reply). Each is switched on or off on [Messages](/wiki/controls/settings/messages).

| | Evening before | Day after |
|---|---|---|
| Which plans | Not canceled, tied to an idea, made in a chat, starting tomorrow | Confirmed, made in a chat, ended before today, started within the last 7 days |
| What it does | Checks tomorrow's rain for an outdoor idea or one that needs dry weather, and the place's looked-up hours against the plan's time. All well, or hours unknown: says nothing. Otherwise a heads-up, with a backup idea when one fits | Asks how it went, with buttons when an idea is tied (**Yes, again**, **Not again**, **Didn't go**). Skipped if an outcome is already recorded from that day on |
| Goes to | The chat the plan was made in | The plan maker, in their own chat when it began in a group |

The hours check fires when the plan's time does not overlap the listed hours at all, or the place is listed closed that weekday. An all-day plan needs only the place open. A check that did not run the evening before is not made up later ([A skipped evening-before check is not retried](/wiki/reference/known-limits#a-skipped-evening-before-check-is-not-retried)).

A plan made on the page has no chat, so it gets no follow-up and no evening-before check ([Plans made on the page get no follow-up](/wiki/reference/known-limits#plans-made-on-the-page-get-no-follow-up)). Its only prompt is **How did it go?** on the page. When somebody is taken off the family list, plans made in their chat forget it and stay.

## How time is stored

| What | Stored as |
|---|---|
| Moments FamilyDB records (messages, reminders, deadlines, last checked) | UTC with a `Z`, to the second |
| A timed plan | The family's local time with its offset, to the minute, such as `2026-10-10T18:00+02:00` |
| An all-day plan | The date, and its end is the last day covered (Google's own end is the day after) |
| An idea's dates, an outcome's day | A date, or a date and local start time with no offset |

The family time zone (`family_tz`, on [General](/wiki/controls/settings/general)) decides what "tonight" means and when a timed plan falls. FamilyDB converts events read from Google to it.

## What free time means

The suggestion step and the nudges count free time in minutes of the family's own clock. A day's free stretches lie between 08:00 and 22:00 unless a question names a part of the day, and the part of today already gone is not free. A busy event takes its minutes out, an event marked free in Google takes none, and a busy all-day event takes the whole day.

The assistant's calendar tool reports three blocks instead: morning (08:00 to 12:00), afternoon (12:00 to 17:00) and evening (17:00 to 22:00), each free when no busy event overlaps it. A nudge asks whether the next 60 minutes are free ([Things to do and reminders](/wiki/model/tasks-and-reminders#preferred-windows-and-nudges)).

## With no calendar

A new plan is saved in FamilyDB, the assistant says nothing is on a calendar, and the page shows saved plans and says so. The assistant cannot read the calendar. Free time is unknown: the suggestion step skips that check, assumes the days are free, and says so.

Once a calendar is connected, the next time the assistant reads the calendar or searches plans, FamilyDB copies saved plans that have not ended across, up to 20 at a time. Changing a saved plan copies that plan first. A plan on a calendar that is no longer connected cannot be moved. Connecting is on [Connections](/wiki/controls/settings/connections#google-calendar), and what Google sees is on [Google Calendar](/wiki/boundaries/google-calendar).

Developer docs: src/familydb/calendar_sync.py, agenda.py, free_time.py, jobs/plan_checks.py and jobs/follow_ups.py; docs/DESIGN.md, "Data model".
