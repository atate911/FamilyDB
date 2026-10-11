# How suggestions are made

When someone asks what to do this weekend, says "I'm bored", or sends `/now`, code does the checking and the model only frames the question and words the reply. The checking is the suggestion engine: a fixed series of stages that weighs every idea against the calendar, forecast, opening hours and travel. The weekend ideas job asks the same question through the chat.

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

Time is counted in minutes. Each day runs from 08:00 to 22:00 unless the question names a part of the day. "Now" starts at this minute and covers 1 to 12 hours, 4 by default; the part of today that has gone is not free. A weekend is Saturday and Sunday, or what is left of them. A range of dates spans at most 15 days.

## What is checked for each idea

Two kinds of check. A fact rules an idea out. A matter of taste only makes it possible, with the reason said first, and the choice is left to the family and to the [stronger call](#choosing-what-to-suggest), which sees their ratings and what they have told the assistant. What the family plans anyway shows on [Status](/wiki/controls/status#what-came-of-her-suggestions), and the family can change the rest and the rain for themselves by saying so, which the assistant keeps as a [rule](/wiki/model/memory#rules-suggestions-keep-to).

| Check | Result when it fails |
|---|---|
| Already planned and still to come, or marked "would not repeat" | Ruled out |
| Done lately, or planned for a day that has passed: a restaurant rests 21 days, an activity 30, a day trip 180, anything else 60, a week when they ask for favorites | Possible, said first ("done 6 days ago"); it comes last among the possible and is never one of her picks on Now |
| Its last rating in the year under 5 out of 10, or its last two | Possible, said first ("rated 4 and 3/10 the last two times") |
| Who is coming, the ages it suits, the season, and the cost, indoor or outdoor and duration limits asked for | Ruled out |
| An idea tied to dates: over, or on days outside the window | Ruled out |
| Forecast: an outdoor or dry-weather idea on a day with a 50% or higher chance of rain (rain and snow codes count only when no chance is given), a warm one under 18 °C (64 °F) | The days that fit; when none does, possible on the wet or cold days with the forecast said first |
| Forecast: a snow idea with no snow forecast | Ruled out when no day has snow |
| Free time: the idea's length against the longest free stretch; an unknown length needs an hour; a trip needs the whole window | Ruled out |
| A day trip, or anything of 8 hours or more: a day with nothing else on it | With nothing else on any day but 8 hours free around something, possible, "something else on that day"; with no 8 hours free, ruled out |
| Opening hours saved by a lookup: open that day, long enough inside a free stretch, with travel at both ends | Closed is ruled out; unknown is possible ("hours unknown"). A stay-at-home idea with nothing to look up has no hours and is not held to any |
| A saved place's details older than the stale limit (`place_stale_days`, 30 days) or never checked | Possible; a chat question also queues a refresh |
| Booking: the lead time against the days left | Too late is ruled out; an unknown lead time is possible |
| Travel: a straight-line estimate times the road factor at the average speed, from home or where they are | Over the limit asked, or the round trip plus the visit longer than the free time, is ruled out |
| Daylight for an outdoor idea, from sunrise and sunset | Possible, never ruled out, since lights and stars are outdoors too |

Free time comes from the connected calendar: an all-day busy event takes the whole day, and an event marked free in Google takes none. Gift and dropped ideas are never offered. The travel formula, with a worked example, is on [Weather, maps and price lists](/wiki/boundaries/weather-and-maps#travel-time-estimates). Travel speed and road factor are on [General settings](/wiki/controls/settings/general), and the stale limit is on [Lookups settings](/wiki/controls/settings/lookups).

Where a person is comes from the place they name or from [Shared location](/wiki/model/location); with neither, travel starts from home.

## The verdicts

- Good: nothing failed and none of the causes of possible applies.
- Possible: no fact ruled it out, but something could not be checked, only partly fits, or is a matter of taste: done lately, disappointing last time, rain or cold forecast, a long day out with something else on the day, hours unknown or not listed, details stale, booking unknown, open for part of the free time, distance from where they are unknown, or too dark.
- Ruled out: a fact failed, and the reason says which.

A reply carries at most 3 reasons each, in the order good, possible, ruled out. Within a group, what was done lately comes last; then ideas shown as good lately: for 3 days when nothing came of that suggestion, and for 2 weeks when the family planned something else from it; then never-done ideas first, and a higher rating before a lower.

The engine logs every idea's verdict and reasons, any web finds, who asked, the window and, for a chat answer, its reply. [Status](/wiki/controls/status#what-came-of-her-suggestions) reads it against the plans made afterwards and how they went. Every run adds a row, including `/now`, the command line and each evening-before backup, and the good verdicts in any of them push those ideas to the back of real answers for 3 days, or 2 weeks when something else was planned from that run.

The `someday` window is thin: with no dates there is no weather, free-time, hours, daylight or travel-fit check, only status, who, season, dates and the limits asked for.

## When a check cannot be made

A missing service does not fail the answer: the engine notes it, and the model is told to say so plainly. A missing calendar, forecast or home position does not lower a verdict by itself.

| Missing | What happens | The note |
|---|---|---|
| No calendar, or it did not answer | The whole time asked about counts as free | "calendar not connected" or "calendar check failed: ..." |
| No home position, or no forecast | Weather is unchecked and the verdict is not lowered | "weather not configured", "forecast failed: ..." or "no forecast for those dates" |
| A place they named that cannot be found, or "here" with no fresh shared position | Travel is counted from home | "could not place ...", "no location shared in the last 3 hours, so travel is from home" |
| An idea number that is not on the list | The check widens to every idea when none is left | "no idea #N on the list" |

## Choosing what to suggest

For a planning question from a grown-up, the engine's checked options go to a stronger model before the chat model answers. Code gathers everything that bears on the question: who asks and who reads, the days, every option with what was checked, how each went before, what the family has told the assistant, the weeks before and after, what was picked lately and the chat's last three days. The stronger model picks up to five, usually a favorite, something new and a wildcard, each with a reason that cites what it rests on. Code checks every pick against the options and the citations, and the chat model leads its reply with them.

If the chat model framed the question plainly wrong, such as the whole weekend for "Saturday morning", the stronger model may correct the days, the hours, who is coming or favorites once before it picks. Code runs the checks again in the corrected terms, without searching the web, and the reply says what was looked at.

It never runs for a kid's question, `/now`, the evening check or the command line, nor for a question about right now unless `choose_now` is on. When it is off, over its monthly budget or fails, the engine's own order is the answer and nobody is told. The row, the budget and what it costs are on [AI model](/wiki/controls/settings/ai-model#choosing-the-suggestions).

## Searching the web

When somebody asks for suggestions, the assistant also searches the web, so the answer is not limited to the list. It is one turn on the lookup model, with up to 4 searches, that hands back up to 6 things: events on the days asked and places to go alike, for the whole family, the grown-ups or the kids, each with its link, who it suits and one line of why. They are offered after the family's own ideas and marked as not on the list.

The search is told the question in your words and what is known about the family: how many grown-ups and the kids' ages, the musts and tastes you have told the assistant, the ideas you loved, home and the [other places you go](/wiki/controls/settings/general#where-home-is), what is on your list, what was found for you before and what you said is not for you. People are described as "a kid, 9" or "a grown-up", never by name, and presents, wishes and other chats' words are never sent ([What leaves the house](/wiki/security/what-leaves-the-house)).

Everything found, by this search, an earlier one or the family's calendars, is checked by the same code as the ideas: a show's time against your free time, rain for something outdoors, who it is for and the ages of the kids coming, your musts against its words, and the drive when its place is known. Each gets a verdict and reasons in an event's words ("on Saturday 19:00-21:00", "busy while it is on"); a day the page gives only in words is possible at best. What is ruled out is logged but not offered.

What it finds is kept, so nothing paid for is lost: each thing with a day, or a place to go any time, joins the finds listed on [Soon](/wiki/controls/plans-and-tasks#soon), where **Not for us** keeps it from being offered again. Something you already saved is marked with its idea; something you passed on is left out; where a kid reads, something for the grown-ups alone is left out.

It runs once for each message while lookups are on and a key serves lookups. The chat model can leave it off only when you ask for your own list alone. When it cannot run, the skipped checks say "web discovery off" or "web discovery waits for a model key". The same question in other words, for the same days, is searched once: results are kept 12 hours in memory and cleared on a restart or when a setting is saved. A failure is noted ("web discovery failed: ...") and not kept.

It costs tokens plus a charge for each search, about a cent or two, within the daily limit, recorded as "searching for what suits them" ([Cost](/wiki/operations/cost)), and adds 10 to 40 seconds to the answer. A place or shared position goes into the search, name and coordinates, to the model company.

## Limits

Every idea that passes the rules is checked in detail. A reply gets at most 12 offered and 6 ruled out, and the result counts the rest. The forecast covers today and the next 15 days. A chat question or the command line queues a refresh of stale places when lookups are on; `/now` does not.

## Trying it without the model

`/now` runs the engine for the next 4 hours with discovery off, so it makes no model call and works when the model is down or the limit is spent ([Telegram: commands and buttons](/wiki/controls/telegram)). On the server, `familydb suggest` runs the engine for any window and prints its verdicts; run it as in [The command line](/wiki/operations/command-line#how-to-run-it), where its options are listed. It adds a log row, so its good ideas come last in real answers for 3 days.

To see what the model got for one real question, an admin opens that message under [Recent activity](/wiki/controls/status/activity), where the `suggest` call shows what it was given and what it answered.

Developer docs: src/familydb/suggest/, src/familydb/tools/suggest.py, src/familydb/commands.py; docs/DESIGN.md, "Suggestion engine: answering "what should we do?"".
