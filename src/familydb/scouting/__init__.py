"""Scouting: finding things on the web for the family (docs/FINDS.md). Every web search made to
find something new goes through here, and nothing else talks to the web to find things:

- `search`: the searches made while answering somebody (`discover`, `find_places`), cached,
  and `saved`, which marks what the family already has.
- `near_home`: the search for what is on near home, and the lookup for event calendars, which
  the hourly job runs (jobs/happening.py).
- `fill`: filling in an idea's details from the web (the evening's lookups, jobs/enrich.py).
- `reach`: what a search reaches the world through: the connection, settings, clock, tools,
  the model client, the cache. Never the App, so this package stands below the engine.

The jobs keep when each runs, what it may spend, and what it tells the family; the engine
keeps checking and choosing. Kept small here on purpose: nothing is imported at the package
level, so importing a shape from `scouting.types` never pulls in the tools.
"""
