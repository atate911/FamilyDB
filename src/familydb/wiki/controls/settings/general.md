# General settings

Where home is, the family's clock and units, and how the page itself looks and is named.
Home and the time zone matter most: they decide the forecast, how far away things are, and
what "tonight" and "this weekend" mean.

## Where home is

| Setting | Default | What it does |
|---|---|---|
| Home town or area (`home_area`) | empty | A town and a state or country, as you would say it. When it changes it is looked up on the map and the page says what it found. A town is enough; no street address |
| Time zone (`family_tz`) | set by the installer from the server | What "tonight" and "this weekend" mean, and when the messages that go out on their own are sent. Choose the nearest city in the same zone |
| Units (`weather_units`) | metric | Metric or imperial, for the forecast and for distances |

**Check the time zone.** The installer sets it from the server, and a rented server is usually
on UTC, so unless you changed it, reminders, the weekend digest and the evening-before check
will come at the wrong hour. The setup asks for it again; look here if times seem off. (If it were
never set at all, FamilyDB would use the server's own `TZ`, else UTC.)

### Exact position and travel times

Folded away on the page, under "Exact position and travel times".

| Setting | Default | What it does |
|---|---|---|
| Latitude (`home_lat`) | found from the town | Negative south of the equator, between -90 and 90. Type it only to be more exact |
| Longitude (`home_lon`) | found from the town | Negative west of Greenwich, between -180 and 180 |
| Average driving speed (`travel_speed_kmh`) | 50 km/h | Across town and highway together, more than 0 and up to 200 |
| Road detour factor (`road_factor`) | 1.3 | How much longer the road is than a straight line, between 1 and 3 |

How long a journey takes is guessed from the position, the speed and the detour factor. It
is an estimate, not a route. Without a home position there is no forecast.

## This page

| Setting | Default | What it does |
|---|---|---|
| Name of this page (`web_title`) | FamilyDB | Shown in the bar, on the sign-in page and in the browser's tab. A family name works well |
| A mic to speak instead of typing (`web_dictation`) | on | Puts a mic beside each box that takes words. The browser writes down what is said: Safari sends the sound to Apple and Chrome to Google, as a phone keyboard's mic does. It never passes through FamilyDB, it costs nothing, and it is not a message until the form's button is pressed. Firefox has no mic |

## The server's log

| Setting | Default | What it does |
|---|---|---|
| Log detail (`log_level`) | INFO | How much the server writes to its log: DEBUG, INFO, WARNING or ERROR. DEBUG also logs every web request and is loud: use it to chase a problem, then put it back |

## Where this page is served, and a name for it

Two read-only cards at the bottom of the page show how the page is reached (the address you
opened it at, the port FamilyDB listens on, whether Caddy passes it on) and the steps to give
it a domain name. Nothing on them is saved; they fill the commands in for you. The commands run
on the server: `maintain.sh https <name>` for a domain, `https --port random` or `port N` for
ports. [Install and first run](/wiki/operations/install#choices-you-can-make) covers the
choices, and `docs/INSTALL.md`, "A domain name instead of the address", has the full steps.
