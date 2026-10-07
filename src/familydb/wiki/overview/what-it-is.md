# What it is and isn't

## Overview

FamilyDB is a private assistant for one family. It runs on a machine the family
owns (a home server or a rented server), talks to the family through Telegram and
a web page, and remembers what they tell it. It is not a service you sign up
for: there is one install per family, one database file, and nobody else can see
into it.

## What it does

It keeps track of four different things, and the difference between them matters:

- **Ideas**: possibilities. A restaurant to try, a day trip, a show, "one day we go to the Hopscotch thing in Portland with the girls". An idea is complete as soon as it is said; a background lookup fills in the address, hours, tickets and travel time later.
- **Plans**: commitments. "We're going to the symphony next Saturday" becomes an event on the shared Google Calendar, and the calendar stays the second copy.
- **Things to do**: obligations, with reminders. They can repeat on a schedule or from when they were last done, and a birthday's reminder lists the gift ideas saved for that person.
- **Answers**: "what should we do this weekend?", "I'm bored", "is the ramen place open now?". Each stored idea is checked against the free time, the forecast, opening hours, booking needs and travel time, and fresh finds from the web are added.

Around those it also:

- remembers what the family says about itself ("the girls are vegetarian now") and weighs it whenever it bears on a question, and lets a parent see and forget any of it;
- hears voice notes and reads photos on Telegram, keeping the words and never the recording or the picture;
- speaks up on its own, but only when there is something to say: a weekend digest, the evening-before check of a plan, a follow-up the day after, and reminders;
- keeps a wish list for each of the kids, which the parents answer;
- offers the same things in a browser, where each person signs in as themselves.

[What it does on its own](/wiki/behavior) lists the jobs, and [How you control
it](/wiki/controls) goes through the pages.

## What it needs

- A machine that stays on, with the install in one folder and an owner-only data folder. The installer in `docs/INSTALL.md` takes about ten minutes and puts HTTPS in front of the page.
- A key for at least one model company (OpenAI, Anthropic or Google). The default is OpenAI's GPT-6 Luna, chosen as the cheapest model that is good enough.
- Optionally: a Telegram bot (the page's own chat works without it), and a Google Calendar shared with a service account (without one the page shows the saved plans and says so).

The page walks a new install through the rest, one step at a time, and Home sends
an admin there until somebody is on the list and a model can answer.

## What it is not

- **Not a way around the family's choices.** Who may message the bot, who may sign in, what leaves the house, what may be spent and what each role may do are the family's decisions, and the model can never change them. The family list is not a tool.
- **Not a window into how it works for the kids.** A kid sees her own chat, her own to-dos and her own wishes, within a number of messages a day the family sets. She is never shown a key, a limit in dollars, a log or why something failed.
- **Not a bill.** The spending figure is an estimate from each call's size and the price table, there to stop a runaway day, not to match the invoice.
- **Not a chatbot that browses.** The chat model never gets the web. Lookups run as separate, bounded worker turns that hand their results back through strict tools.

## Why it is built this way

Two things shaped it more than any others. The first is that a family is small
scale: a few hundred ideas fit in a prompt, one SQLite file is enough, and one
process is easy to look after. The second is cost: a model is paid for by the
token, so the design keeps replies short, keeps what changes out of the cached
part of the prompt, and does by code whatever code can do. The reasons behind each
decision, and the family's own choices, are in `docs/DESIGN.md`.
