# How "what should we do?" is answered

When someone asks what to do this weekend, says "I'm bored", or sends `/now`, code does the checking and the model only frames the question and words the reply. The checking is the suggestion engine, a fixed series of stages in `suggest/` that weighs every idea against the calendar, forecast, opening hours and travel. The weekend digest asks the same question through the chat.

## What the model does and does not do

The chat model turns the message into one `suggest` call (window, part of the day, who is coming, topic, where they are, limits such as cheap or close by) and writes three to five options from the result. It does not decide a verdict, and the prompt tells it not to repeat the checks with the calendar, forecast or hours tools. `/now` and `familydb suggest` skip the model and call the engine directly.

## The stages

| Stage | Who | What it does |
|---|---|---|
| Frame | the model | Turns the words into the `suggest` input |
| Context | code | Free minutes per day from the calendar, and the forecast per day |
| Shortlist | code | Rules out ideas that cannot fit; keeps at most eight to check in detail |
| Evaluate | code | Checks each of those against hours, travel, booking and daylight |
| Discover | code, then a worker turn | Optionally searches the web for things that are on |
| Compose | code | Orders the verdicts and trims them to what a reply can use |
| Log | code | Stores every verdict and reason |

Time is counted in minutes. Each day runs from 08:00 to 22:00 unless the question names a part of the day. "Now" starts at this minute and covers 1 to 12 hours, four by default; the part of today that has gone is not free. A weekend is Saturday and Sunday, or what is left of them; a range of dates spans at most 15 days.

## What is checked for each idea

| Check | Result when it fails |
|---|---|
| Already planned, done in the last 60 days, rated under 5 out of 10, or marked "would not repeat" | Ruled out |
| Who is coming, the season, and the cost, indoor or outdoor and duration limits asked for | Ruled out |
| An idea tied to dates: over, or on days outside the window | Ruled out |
| Forecast: an outdoor or dry-weather idea on a day with a 50% or higher chance of rain (rain and snow codes count only when no chance is given), a warm one under 18 °C (64 °F), a snow one without snow | Ruled out when no day fits |
| Free time: the idea's length against the longest free stretch; an unknown length needs an hour, a day trip or anything of eight hours or more needs a whole free day, a trip needs the whole window | Ruled out |
| Opening hours saved by a lookup: open that day, long enough inside a free stretch, with travel at both ends | Closed is ruled out; unknown, or an idea with no place, is possible ("hours unknown") |
| A saved place's details older than the stale limit (`place_stale_days`, 30 days) or never checked | Possible; a chat question also queues a refresh |
| Booking: the lead time against the days left | Too late is ruled out; an unknown lead time is possible |
| Travel: a straight-line estimate times the road factor at the average speed, from home or where they are | Over the limit asked, or the round trip plus the visit longer than the free time, is ruled out |
| Daylight for an outdoor idea, from sunrise and sunset | Possible, never ruled out, since lights and stars are outdoors too |

Free time comes from the connected calendar: an all-day busy event takes the whole day, and an event marked free in Google takes none. Gift and dropped ideas are never offered. Travel speed and road factor are on [General settings](/wiki/controls/settings/general), the stale limit on [Lookups settings](/wiki/controls/settings/lookups).

## The verdicts

- **Good:** nothing failed and none of the causes of possible applies.
- **Possible:** nothing failed, but something could not be checked or only partly fits: hours unknown or not listed, details stale, booking unknown, open for part of the free time, distance from where they are unknown, or too dark. An idea beyond the first eight (never-done first, then longest since done) is possible, "not checked in detail".
- **Ruled out:** a check failed, and the reason says which.

A reply carries at most three reasons each, in the order good, possible, ruled out. Within a group, ideas suggested as good in the last two weeks come last; then never-done ideas first, and a higher rating before a lower.

The log is the `suggestions` table: every idea's verdict and reasons, any web finds, who asked, the window and, for a chat answer, its reply. No page lists it. Every run adds a row, including `/now`, the command line and each evening-before backup, and the good verdicts in any of them push those ideas to the back of real answers for 14 days.

The `someday` window is thin: with no dates there is no weather, free-time, hours, daylight or travel-fit check, only status, who, season, dates and the limits asked for.

## What a check that cannot be made does

A missing service does not fail the answer: the engine notes it, and the model is told to say so plainly. A missing calendar, forecast or home position does not lower a verdict by itself.

| Missing | What happens | The note |
|---|---|---|
| No calendar, or it did not answer | The whole time asked about counts as free | "calendar not connected" or "calendar check failed: ..." |
| No home position, or no forecast | Weather is unchecked and the verdict is not lowered | "weather not configured", "forecast failed: ..." or "no forecast for those dates" |
| A place they named that cannot be found, or "here" with no shared position in the last 3 hours | Travel is counted from home | "could not place ...", "no location shared in the last 3 hours, so travel is from home" |
| An idea number that is not on the list | The check widens to every idea when none is left | "no idea #N on the list" |

## Web discovery

Discovery adds time-bound things that are not on the list: festivals, markets, shows. It is one worker turn on the lookup model, with up to four searches, that hands back up to six finds, offered with their link and marked as not on the list.

It runs only when the call asks for it, lookups are on, and a key serves lookups. The chat model sets it: the tool's default is on, and the prompt says to leave it off for now or today unless asked what is on. When asked for but unable to run, the skipped checks say "web discovery off" or "web discovery waits for a model key".

The request is built from the window, hours, home area, topic, constraints and, when set, where they are, never from the question's wording, so differently worded questions share one search. Results are kept 12 hours in memory, per window, request and day, and cleared on a restart or when a setting is saved. A failure is noted ("web discovery failed: ...") and not kept; an empty result is kept.

It costs tokens plus a charge for each search, within the daily limit, recorded as "searching for what is on" ([Cost](/wiki/operations/cost)). A place or shared position goes in the search, name and coordinates, to the model company ([Data and privacy](/wiki/security/data-and-privacy)).

## /now without the web

`/now` asks the engine for the next four hours as the person who sent it, using their shared position if fresh. It turns discovery off and queues no refresh of stale places, so it makes no model call and works when the model is down or the limit is spent. It shows up to five options, three ruled out, and a "Not checked" line naming what was skipped. [Telegram](/wiki/controls/telegram) has the rest.

## Limits

At most eight ideas are checked in detail. A reply gets at most 12 offered and 6 ruled out, and the result counts the rest. The forecast covers today and the next 15 days. A chat question or the command line queues a refresh of stale places when lookups are on; `/now` does not.

## Inspecting it

Run the engine without the model:

```bash
cd /opt/familydb
sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb suggest --window this-weekend --json
```

On Docker:

```bash
sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb suggest --window this-weekend --json
```

`--window` takes `now`, `today`, `this-weekend`, `next-weekend`, `someday` or `START..END` as dates; `--as <name>` asks as that person; `--discover` adds the web search, which costs money and needs lookups on. Without `--json` it prints each day's free time and forecast, then a line per idea. The JSON adds each candidate's checks, the finds, the skipped checks and the log row's id.

To see what the model got for one real question, an admin opens that message under [Recent activity](/wiki/controls/status/activity), where the `suggest` call shows what it was given and what it answered. A test run adds a log row, so its good ideas come last in real answers for 14 days.

Developer docs: `familydb/suggest/` (one module per stage, `engine.run`), `familydb/tools/suggest.py`, `familydb/commands.py` (`_now`), and `docs/DESIGN.md`, "Suggestion engine: answering what should we do".
