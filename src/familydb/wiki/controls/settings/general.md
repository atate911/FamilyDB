# General

The General card sets where home is, the family's clock and units, and how the web page is named. Home and the time zone matter most: they decide the forecast, how far away things are, and what "tonight" and "this weekend" mean.

## Where home is

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Home town or area (`home_area`) | empty | Where home is, as you would say it. When it changes, or you save it again while no position is kept, FamilyDB looks it up on the map and the card says what it found; if the town is not found, or the box is emptied, the previous position is kept. | A town and a state or country; no street address |
| Time zone (`family_tz`) | the server's, set by the installer | Decides what "tonight" and "this weekend" mean, and when the messages that go out on their own are sent. | The nearest city in the same zone |
| Units (`weather_units`) | metric | The units for the forecast and for distances. | metric or imperial |

**Check the time zone first.** The installer copies the server's zone, so a server set to UTC gives the family UTC, and reminders, weekend ideas and the evening-before check arrive at the wrong hour. Setup asks for the zone again; look here if times seem off. With none saved anywhere, FamilyDB uses the server's own `TZ`, else UTC. A zone saved on this card (Setup saves it too) overrides `.env`; empty the box to go back.

### Exact position and travel times

Folded away on the card, under "Exact position and travel times".

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Latitude (`home_lat`) | found from the town | Type it only to be more exact. Negative is south of the equator. | -90 to 90 |
| Longitude (`home_lon`) | found from the town | Negative is west of Greenwich. | -180 to 180 |
| Average driving speed (`travel_speed_kmh`) | 50 km/h | Across town and highway together. | More than 0, up to 200 |
| Road detour factor (`road_factor`) | 1.3 | How much longer the road is than a straight line. | 1 to 3 |

FamilyDB guesses how long a journey takes from the position, the speed and the detour factor. It is an estimate, not a route. Without a home position there is no forecast.

## This page

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Name of this page (`web_title`) | FamilyDB | Shown in the bar, on the sign-in page and in the browser's tab. A family name works well. | Any text |
| A mic to speak instead of typing (`web_dictation`) | on | Puts a mic beside each box that takes words, in a browser that has speech recognition. Off removes it. | on or off |

The mic uses the browser's own speech recognition: Safari sends the sound to Apple and Chrome to Google, as a phone keyboard's mic does, and Firefox has no mic. The sound never passes through FamilyDB, costs nothing, and is not a message until you press the form's button. Where the mic appears is on [Home and Chat](/wiki/controls/home-and-chat#the-mic).

## The server's log

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Log detail (`log_level`) | INFO | How much the server writes to its log. DEBUG also logs the program's own network traffic, to Telegram and the model companies, and is loud: use it to chase a problem, then put it back. | DEBUG, INFO, WARNING or ERROR |

Reading the log is on [Diagnostics](/wiki/operations/diagnostics#logs).

## Where the web page is served, and a name for it

Two read-only cards at the bottom of General show how the web page is reached (the address you opened it at, the port FamilyDB listens on, whether Caddy passes it on) and the steps to give it a domain name. Nothing on them is saved; they fill the commands in for you, and the commands run on the server. The choices and the commands are on [HTTPS and the firewall](/wiki/operations/https-and-firewall).
