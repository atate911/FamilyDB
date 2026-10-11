# What is on near home

The card for what is on near home sets how FamilyDB finds what is on near home over the next 4 weeks: shows, markets, library and park events. It reads calendars you give it or tick, Ticketmaster with a free key, and her scouting on the web each evening. The finds are listed on their own tab beside Plans, which parents and admins see, shown on [Status](/wiki/controls/status), and offered when somebody asks what to do.

A job checks every hour and reads each source only when it is due: calendars and Ticketmaster about once a day, scouting once each evening after the evening's lookups (`lookup_hour`), on a theme that turns with the week: food and drink, outdoors, shows and music, grown-ups' evenings, the weekend ahead, classes and clubs, the weeks ahead. Scouting is told about the family as a search for suggestions is ([Searching the web](/wiki/behavior/suggestions#searching-the-web)), and what it finds is sorted by code: nothing already on your list, saved, passed on, or that one of your musts avoids, and only what has a day it can read or is a place to go any time. After scouting, the same evening fills in up to three of the newest finds as ideas are looked up (address, hours, price, the drive), and, when something is new, judges the whole pocket: code checks each find against your calendar, the forecast and your musts, and one call with no web chooses up to five worth putting forward to you, each with why and when. Each step runs only while the evening has room. It needs home to be set on [General](/wiki/controls/settings/general). A source that cannot be read is tried again the next day.

| Source | Cost | Needs |
|---|---|---|
| Calendars | Free, no model | A calendar address |
| Ticketmaster | Free, no model | A free Ticketmaster key and home |
| Scouting and the lookup for calendars | A few cents a call, within the monthly budget | Web lookups on, home, and a key for the company that looks things up |

If one of those is missing, the card shows a warning that says which. The search and the lookup send the home town or area to the model company and its web search; Ticketmaster is sent home's position rounded to about 1 kilometer. Reading a calendar sends nothing of the family. What leaves the house is on [What leaves the house](/wiki/security/what-leaves-the-house).

## Calendars

Once home is set and web lookups are on, FamilyDB looks for the public calendars of libraries, parks, venues and the city near home, and lists them under **Calendars found near home**. Tick the ones to read. A calendar is offered only after FamilyDB has read it and found something on in the next 60 days. When new ones turn up, each admin with a Telegram id is told once.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Calendar addresses (`event_feeds`) | none | The calendars read, one address a line: the iCal or `.ics` link a library, school or venue gives for subscribing. Ticking a found calendar adds its address here. A `webcal://` link is read as `https://`, and an address on this server or the home network is refused. | `https://` addresses, 2000 characters in all |

Each calendar is read once a day. A calendar that fails 3 days running is told to the admins, and forgotten with what it found when you take its address off.

## Ticketmaster

A free Ticketmaster key adds shows, concerts and games near home, read once a day. Make an app at Ticketmaster's developer site, then paste its Consumer Key into **Ticketmaster key** and press **Save the key**. The key is write-only like the other keys: it is never shown again, and it is in every [backup](/wiki/operations/backup-and-restore). Tick **Remove it** to take it off.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Kilometers from home (`happening_radius_km`) | 80 | How far Ticketmaster looks. A calendar lists what it lists, and the search keeps to about two hours away. | 5 to 300 |

## Looking on its own

Once a week FamilyDB searches the web for what is on near home over the next 4 weeks. Every so often it also looks for calendars near home to offer you above, and it looks at once when the home area changes. Both are lookups that use the web, so web lookups must be on ([Lookups](/wiki/controls/settings/lookups)) and a key must be saved for the company that does them ([AI model](/wiki/controls/settings/ai-model#what-does-what), the row for what is on near home).

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Scout the web each evening (`happening_search`) | on | Scouting and the lookup for calendars. Off makes neither; calendars and Ticketmaster are still read. | on or off |
| Days between looking for calendars (`happening_refind_days`) | 30 | How often it looks for calendars to offer. | 7 to 90 |
| Most it may spend a month (`happening_budget`) | US$2 | Both kinds of call together, over the calendar month in the family's time zone, and within the daily limit too. FamilyDB makes a call only while the budget has room for one more, and scouts on an evening only when a night's scouting, at what it has cost lately, fits that evening's share of what is left of the month (what is left over the evenings left). 0 makes no model calls for it. | 0 to 20 |

The card says what these calls have cost this month, and Status shows how each source last answered. To run the job by hand, use `familydb happening`, or `familydb happening --now` to read every source and not only those due; run it as in [The command line](/wiki/operations/command-line#how-to-run-it).
