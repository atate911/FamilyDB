# FamilyDB

A private family assistant that lives in our chat app. It remembers the things we say we'd like to do, puts confirmed plans on the shared Google Calendar, and suggests what to do this weekend based on the calendar, the weather and the ideas we've collected.

**Status:** design stage. See [docs/DESIGN.md](docs/DESIGN.md) for the architecture, data model, tool definitions, deployment plan, roadmap and open decisions.

## How it will work

- Someone messages the bot "we should try that ramen place sometime" and it is logged as an idea, tagged with what it can infer (restaurant, cheap, any season).
- "We're going to the symphony next Saturday" becomes an event on the family calendar, with the resolved date echoed back.
- "What should we do this weekend?" returns a short list of ideas that fit the free time and the forecast, with an offer to schedule them.
- The day after a plan, the bot asks how it went so it can suggest repeats or avoid duds.

## Planned stack

One long-running Python process on the home server (Docker), Claude through the Anthropic API for understanding, SQLite for storage, the Google Calendar API, Open-Meteo for weather, and Telegram as the first chat channel. The final choices are tracked in the design doc's open decisions.
