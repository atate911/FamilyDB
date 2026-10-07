# Google Calendar

FamilyDB puts confirmed plans on one shared Google calendar and reads that calendar to see when the family is free. This page covers how it reaches Google, what it reads and writes, what happens when Google says no, and how to look after the key. Connecting is a form on [Connections](/wiki/controls/settings/connections#google-calendar) or a step in [Setup](/wiki/controls/setup#google-calendar), and the calendar is optional.

## Why a service account

FamilyDB signs in as a Google *service account*: a robot account with an address of its own, which you share the family calendar with. Nobody's Google sign-in is stored, no one's mail or other calendars are within reach, and the server needs no browser to connect. Its key asks for one scope, calendar events, so it can read and write events and nothing else. It reaches only calendars shared with it.

## What it reads and writes

| What | How |
|---|---|
| Events in a window | The calendar tools, the suggestion engine and the nudges ask Google each time. Recurring events arrive as single events |
| One event | By its id, before a plan is changed |
| What changed since last time | One request for all plans, using Google's sync token, which is kept in `calendar_sync_state` |
| A new event, a change, a removal | When a plan is made, moved, edited or cancelled, or when the page's forms do the same |

An event carries a title, times, a place and notes. Which tools ask Google, and what Google then sees, is in [What leaves the house](/wiki/security/data-and-privacy#what-leaves-the-house).

## Keeping plans in step

People move and cancel events in Google without telling the bot, so a plan is checked against its event before anything acts on it, and when the evening-before check and the follow-ups run. A moved or edited event changes the plan. A deleted event cancels the plan and puts its idea back as an idea. Google is asked what changed since the stored token, which is nothing most of the time. The token is kept only after the plans are updated, so a failure reads the same changes again. If Google has forgotten the token, FamilyDB starts again from the whole calendar.

A retry must not make a second event. Before Google is contacted, `calendar_creations` keeps the event id an attempt will use, so after a crash or a lost answer the retry asks for the same event. If Google says the id is taken, FamilyDB fetches that event instead of making another. An attempt is finished when a plan holds that event id.

## What the page shows

| Situation | What the page says |
|---|---|
| Google answered | "From Google Calendar, including anything added there directly." |
| No calendar connected, or its key file is missing | "Google Calendar is not connected, so these are the plans FamilyDB has saved." |
| Google did not answer | "Google Calendar did not answer, so these are the plans as FamilyDB last saw them. Times may have moved since." |

The page keeps Google's answer for a minute, so an event added on a phone can take that long to appear. Anything the bot writes clears it at once. No page view asks a model.

## Connecting, and the check

The form takes the key file and the calendar's id, and tries them before keeping either: it reads the calendar, adds an all-day event called "FamilyDB connection check", and deletes it. That event may show briefly in calendar notifications. `familydb google connect <KEY_FILE> <CALENDAR_ID>` does the same on the server, and `familydb google events` shows what the bot sees.

| Google says | The page tells you |
|---|---|
| The key is not a service account's, or not JSON | To paste the whole file Google saved |
| The calendar is not found | To check the id and the sharing, naming the account's address |
| It can see the calendar but not change it | To give the address "Make changes to events" |
| The Calendar API is off in the key's project | To turn it on and try again in a minute |
| The key is refused | That it may have been deleted |

## When Google says no later

| What happened | What follows |
|---|---|
| The calendar was unshared | Reads fail with "Google Calendar error 404". The page shows the saved plans as above, suggestions skip the calendar check and say so, and the evening-before check and follow-ups wait. No alert is raised for this |
| The calendar was made read-only | Reading works. A write fails with "Google Calendar error 403", so a plan is not made or changed. No alert is raised for this |
| The key was deleted or refused in Google Cloud | Reads and writes fail, Status shows "Google Calendar stopped letting the bot in", and each admin with a Telegram id is told. It clears when a Google request next works |
| The key file was deleted from the server | Status says a calendar is named but not connected, and after the next restart the calendar counts as not connected. New plans are saved in FamilyDB only, and plans still to come are copied to Google once it is connected again |

A plan already on Google cannot be changed while the calendar is not connected. If you connect a different calendar id, the old plans belong to the other calendar and are refused.

## The key

The key is a file, `data/google_key.json` (`google_key_path`), written owner-only. It is not in the database, so a [backup](/wiki/operations/backup-and-restore) holds the calendar's id but not the key.

**Deleting the old key first shuts the bot out of the calendar until you connect again.** To rotate it, make a new key for the same service account in Google Cloud, paste it on Connections with the calendar's id, and wait for the check to pass. Then delete the old key.

If the key is gone, make a new one and connect again. Nothing is lost: the events are in Google, and plans on the same calendar id follow them again.

## Limits

- **Time zones.** Times are read in the family's time zone and written with it. An event in another zone shows converted.
- **All-day and timed.** A busy all-day event takes the whole day in the free-time check. An event marked free in Google, such as a birthday, blocks nothing. Google's all-day end is the day after, and plans store the last day.
- **Free time.** The calendar tools report which of morning (from 08:00), afternoon (from 12:00) and evening (from 17:00, to 22:00) are free. The suggestion engine works in minutes between 08:00 and 22:00.
- **Windows.** The calendar tool reads at most 60 days at a time.
- **Hand-added events.** They appear and count as busy. They stay events and never become plans. The bot can move or remove one by its id when asked, and the page's move and cancel forms work on the bot's own plans.

Developer docs: `src/familydb/integrations/google_calendar.py`, `src/familydb/calendar_sync.py`, `src/familydb/agenda.py`, `src/familydb/free_time.py`, `src/familydb/tools/gcal.py`, `src/familydb/web/settings.py` (`google_connect`), and `docs/DESIGN.md`, "Integrations" (Google Calendar).
