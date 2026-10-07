# Weather, maps and price lists

FamilyDB asks three free public services for what it cannot know itself: Open-Meteo for the forecast, OpenStreetMap's Nominatim (with Open-Meteo's geocoder as a spare) for where a place is, and two price lists for what models cost. None needs a key. Each section says what the service is used for, what is sent to it and what happens when it is down. [What leaves the house](/wiki/security/what-leaves-the-house) is the short version.

## The forecast

Open-Meteo gives a daily forecast for the home position: conditions, high, low, chance of rain, precipitation, sunrise and sunset. Each request carries the home latitude and longitude to 4 decimals, the dates, the family's time zone and the units, and nothing else. It reaches today and the next 15 days, and an answer is kept in memory for 1 hour for each range of dates.

The forecast needs a home position, which the home town gives ([General](/wiki/controls/settings/general#where-home-is)). Without one the forecast tool is unavailable and the suggestions say weather is not configured.

It is used for:

- the `get_forecast` tool, when somebody asks about the weather;
- the suggestion engine, to judge outdoor, dry, warm and snow ideas, and daylight left;
- the evening-before check of a plan, which looks for rain on an outdoor idea.

When Open-Meteo does not answer, the forecast tool reports `weather service unavailable` (no connection, a timeout or an unreadable answer) or `weather service returned HTTP <code>`. Requests give up after 15 seconds. A suggestion skips the weather and notes `forecast failed`. The evening-before check goes ahead without the weather. Days past the 15th have no forecast.

## Finding places

| Service | Used for | What is sent |
|---|---|---|
| Nominatim search | The home town when you save it; a place's address when a lookup saves it with no coordinates; a place named in a question ("near the lake") | The text, such as `Portland, Oregon` or an address |
| Nominatim reverse | Naming a position somebody shared, such as "Pearl District, Portland" | The latitude and longitude to 5 decimals |
| Open-Meteo's geocoder | A short name, with no digits and at most four words, that Nominatim did not find | The name |

Every request carries a `User-Agent` naming FamilyDB. When an operator sets `GEOCODER_CONTACT` in `.env` ([The .env file](/wiki/operations/configuration)), Nominatim also gets that email address or web page, which its usage policy asks for. Open-Meteo's geocoder never gets it. Empty sends none.

Nominatim's policy allows one request a second, and FamilyDB spaces its Nominatim requests at least a second apart. A named place that lands more than 150 km from home is retried with the home area added, since it probably matched somewhere else of the same name. If the retry is also far, or no home area is set, the place is rejected. Geocoding gives up after 15 seconds.

A shared position is named once and reused while the person stays within 200 metres ([Shared location](/wiki/model/location)). Lookups are cached in memory, reverse ones to about 100 metres. A forward lookup that finds nothing, or fails, is remembered as nothing until FamilyDB restarts or a setting changes, so a town that failed during an outage can keep answering "not found" until then.

## When a lookup fails

| Where | What you see |
|---|---|
| Saving the home town | `Could not find <town> on the map. Type its latitude and longitude as well.` The previous position stays. Saving the same town text again does not retry the lookup, so type the latitude and longitude instead |
| A place saved by a lookup | The place is saved without coordinates or travel time |
| A suggestion near a named place | `Could not place <name>, so travel is from home`, also when the place was found but too far from home |
| A shared position | FamilyDB still has the coordinates. The reply just does not name the place |

## Travel-time estimates

FamilyDB calls no routing service. A travel time is the straight-line distance, multiplied by a detour factor, divided by an average speed:

minutes = straight-line km × `road_factor` ÷ `travel_speed_kmh` × 60

With the defaults of 1.3 and 50 km/h, a place 20 km away in a straight line is 26 km by road and 31 minutes. The start is home, or a shared position or a named place when a question says so. Without a home position, or a place with no coordinates, there is no travel time. Both numbers are on [General](/wiki/controls/settings/general#exact-position-and-travel-times). It is an estimate across town and highway together, not a route.

## The price lists

Once a day, at 05:17, the daily model check reads LiteLLM's list (a JSON file on GitHub) and OpenRouter's model list. Each is fetched afresh with a 30-second limit, carries nothing of the family, and gives prices, whether a model uses tools, and release and end dates. From LiteLLM only chat models are kept, and OpenRouter's variants such as `:free` are ignored. Turning `model_watch` off stops both requests and puts back the prices built into this version.

[Models and prices](/wiki/controls/status/models-and-prices#what-the-daily-check-does) says how a price is chosen when the lists disagree and what an admin is told.

Developer docs: src/familydb/integrations/open_meteo.py, src/familydb/integrations/geocode.py, src/familydb/integrations/price_lists.py, src/familydb/whereabouts.py, src/familydb/suggest/origin.py; docs/DESIGN.md, "Integrations".
