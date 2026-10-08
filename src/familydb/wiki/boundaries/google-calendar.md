# Google Calendar

FamilyDB puts confirmed plans on one shared Google calendar and reads that calendar to see when the family is free. The calendar is optional. To connect it, use the form on [Connections](/wiki/controls/settings/connections#google-calendar) or the step in [Setup](/wiki/controls/setup#google-calendar).

## Why a service account

FamilyDB signs in as a Google [service account](/wiki/reference/glossary#service-account): a robot account with an address of its own, which you share the family calendar with. Nobody's Google sign-in is stored, no one's mail or other calendars are within reach, and the server needs no browser to connect. Its key asks for one scope, calendar events, so FamilyDB can read and write events and nothing else. It reaches only calendars shared with it.

## What it reads and writes

| What | How |
|---|---|
| Events in a window | The calendar tools, the suggestion engine and the nudges job ask Google each time. Recurring events arrive as single events |
| One event | By its id, before a plan is changed. When Google says it is not found, FamilyDB asks for one event of the calendar to check that the calendar is still there, so each such lookup costs one more request |
| What changed since last time | One request for all plans, using Google's sync token, which FamilyDB keeps; it pages at 2,500 items |
| A new event, a change, a removal | When a plan is made, moved, edited or canceled, or when the page's forms do the same |

Which tools ask Google, and what Google then sees, is on [What leaves the house](/wiki/security/what-leaves-the-house).

## Keeping plans in step

People move and cancel events in Google without telling FamilyDB, so a plan is checked against its event before anything acts on it, and when the evening-before check and the follow-ups run. A moved or edited event changes the plan. An event missing from a calendar Google still shows cancels the plan and puts its idea back. When Google no longer shows the calendar itself, FamilyDB leaves the plan as it is ([When Google says no later](#when-google-says-no-later)). FamilyDB asks Google what changed since the stored token, and keeps the new token only after the plans are updated, so a failure reads the same changes again. If Google has forgotten the token, FamilyDB starts again from the whole calendar.

A retry must not make a second event. Before Google is contacted, FamilyDB records the event id an attempt will use, so after a crash or a lost answer the retry asks for the same event, or fetches it if Google says the id is taken.

## What the page shows

| Situation | What the page says |
|---|---|
| Google answered | `From Google Calendar, including anything added there directly.` |
| No calendar connected, or its key file is missing | `Google Calendar is not connected, so these are the plans FamilyDB has saved.` |
| Google did not answer | `Google Calendar did not answer, so these are the plans as FamilyDB last saw them. Times may have moved since.` |

The page, and Telegram's `/today` and `/week`, keep Google's answer for 1 minute, so an event added on a phone can take that long to appear. Anything FamilyDB writes clears it at once.

## Connecting

The form tries the key and the calendar's id before keeping either: it reads the calendar, adds an all-day event called `FamilyDB connection check`, and deletes it. That event may show briefly in calendar notifications. If the check fails, the page says what is wrong, such as a key that is not a service account's, a calendar that is not found, or a Calendar API switched off in the key's project.

## When Google says no later

When Google says a plan's event is not found, FamilyDB reads one event of the calendar to tell a deleted event from a calendar it can no longer see. If the calendar is gone, the plan stays as it is and is not canceled. Status shows `Google Calendar is no longer showing the bot its calendar` under Needs a look, and each admin with a Telegram id is told to check that the calendar is still shared with the service account and not deleted. The row clears when a Google request next works. Share the calendar again, or connect another, before you change any plans.

Reading the calendar's events, as the page and the suggestions do, still fails as `Google Calendar error 404` with no alert; suggestions skip the calendar check and say so, and the evening-before check and follow-ups wait ([known limits](/wiki/reference/known-limits#an-unshared-calendar-raises-an-alert-only-when-one-event-is-looked-up)).

| What happened | What follows |
|---|---|
| The calendar was made read-only | Reading works. A write fails with `Google Calendar error 403`, so a plan is not made or changed. No alert is raised |
| The Calendar API was switched off in the key's project | Calls fail as `Google Calendar error 403`, with no alert. Setup recognizes this case, but only when you connect |
| Google refused the key at sign-in (the key deleted, the service account disabled, or the server's clock far off), or the key file is unreadable | Reads and writes fail, Status shows `Google Calendar refused the bot's key, or it has none`, and each admin with a Telegram id is told to connect again with a new key. It clears when a Google request next works |
| The key file was deleted from the server | Status says a calendar is named but not connected. A running FamilyDB that already built its client keeps working, and after the next restart the calendar counts as not connected. New plans are saved in FamilyDB only, and plans still to come are copied to Google once it is connected again, up to 20 a run |

That alert is for the key only. A plan already on Google cannot be changed while the calendar is not connected. If you connect a different calendar id, the old plans belong to the other calendar and are refused.

## Disconnecting

An admin can disconnect the calendar on [Connections](/wiki/controls/settings/connections#disconnect-google-calendar). FamilyDB deletes the key file and forgets the calendar's id, and clears any Needs a look row about the calendar. Plans stay saved in FamilyDB, nothing is taken off Google, and the service account still has the calendar shared with it until you stop sharing in Google.

## The key

The key is a file, `data/google_key.json` (`google_key_path`), written owner-only. It is not in the database, so a [backup](/wiki/operations/backup-and-restore) holds the calendar's id but not the key.

> **Deleting the old key first shuts FamilyDB out of the calendar until you connect again.** To rotate it, make a new key for the same service account in Google Cloud, paste it on Connections with the calendar's id, and wait for the check to pass. Then delete the old key.

If the key is gone, make a new one and connect again. The events are in Google, and plans on the same calendar id follow them again.

## Limits

- Time zones. Times are read in the family's time zone and written with it. An event in another zone shows converted.
- All-day and timed. A busy all-day event takes the whole day in the free-time check. An event marked free in Google, such as a birthday, blocks nothing. Google's all-day end is the day after, and plans store the last day.
- Free time. The calendar tools report which of morning (from 08:00), afternoon (from 12:00) and evening (from 17:00, to 22:00) are free. The suggestion engine works in minutes between 08:00 and 22:00.
- Hand-added events. They appear and count as busy. They stay events, not plans. FamilyDB can move or remove one by its id when asked, and the page's move and cancel forms work on FamilyDB's own plans.

Developer docs: src/familydb/integrations/google_calendar.py, src/familydb/calendar_sync.py, src/familydb/agenda.py, src/familydb/free_time.py, src/familydb/tools/gcal.py; docs/DESIGN.md, "Integrations".
