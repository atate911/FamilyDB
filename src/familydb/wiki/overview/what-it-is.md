# What it is and is not

FamilyDB is a private family planning assistant that lives in the family's chat app. People tell it things (ideas for places to go, plans, things to do, facts about the family) and ask it what to do. It keeps everything in one database file ([SQLite](/wiki/reference/glossary#sqlite)) on a machine the family owns, mirrors confirmed plans to a shared Google Calendar, and uses a model from a model company (Anthropic, OpenAI or Google) to understand sentences and word replies. The assistant is called Vera by default, and the family can rename her.

It is not a service you sign up for. There is one install per family, one database file, and nobody else can see into it. It runs on a home server or a rented one, and talks to the family through Telegram and a web page.

## What it does

It keeps track of four different things, and the difference between them matters:

- **Ideas**: possibilities. A restaurant to try, a day trip, a show, "one day we go to the Hopscotch thing in Portland with the kids". An [idea](/wiki/reference/glossary#idea) is complete as soon as it is said; a background [lookup](/wiki/reference/glossary#lookup) fills in the address, hours, tickets and travel time later.
- **Plans**: commitments. "We're going to the symphony next Saturday" becomes an event on the shared Google Calendar, and the calendar stays the second copy. See [plan](/wiki/reference/glossary#plan).
- **Things to do**: obligations, with reminders. They can repeat on a schedule or from when they were last done, and a birthday's reminder lists the gift ideas saved for that person. See [thing to do](/wiki/reference/glossary#thing-to-do).
- **Answers**: "what should we do this weekend?", "I'm bored", "is the ramen place open now?". Each stored idea is checked against the free time, the forecast, opening hours, booking needs and travel time, and fresh finds from the web are added.

Around those it also:

- remembers what the family says about itself ("the kids are vegetarian now") and weighs it whenever it bears on a question, and lets a parent see and forget any of it ([memory](/wiki/reference/glossary#memory));
- hears voice notes and reads photos on Telegram, keeping the words and never the recording or the picture;
- speaks up on its own, but only when there is something to say: [weekend ideas](/wiki/reference/glossary#weekend-ideas), the evening-before check of a plan, a follow-up the day after, and reminders;
- keeps a wish list for each of the kids, which the parents answer;
- offers the same things in a browser, where each person signs in as themselves.

[What it does on its own](/wiki/behavior) lists the jobs, and [Using FamilyDB](/wiki/controls) goes through the pages.

## What it needs

A machine that stays on, a key for one model company, and optionally a Telegram bot and a Google Calendar shared with a [service account](/wiki/reference/glossary#service-account). The exact list is in [What you need](/wiki/operations/install#what-you-need). The web page walks a new install through the rest, one step at a time, and Home sends an admin there until somebody is on the family list and a model can answer.

## What it is not

- **Not a way around the family's choices.** Who may message the assistant, who may sign in, what leaves the house, what may be spent and what each role may do are the family's decisions, and the model can never change them. The family list is not a tool.
- **Not a window into how it works for the kids.** A kid sees their own chat, their own things to do and their own wishes, within two limits the family sets ([Kids](/wiki/model/family-and-roles#kids)). They are never shown a key, a limit in dollars, a log or why something failed.
- **Not a bill.** The spending figure is an estimate from each call's size and the price table, there to stop a runaway day, not to match the invoice.
- **Not a chatbot that browses.** The chat model never gets the web. Lookups run as separate, bounded calls that hand their results back through strict tools.

## What the family decided

Some choices are the family's, not the software's. Each is set in one place and changed only by asking the family.

| Decision | Where it is set |
|---|---|
| Who may message the assistant | [The family list](/wiki/model/family-and-roles#who-may-message-the-bot) |
| Who signs in, and with what | [Each person's own password](/wiki/security/passwords-and-sessions) |
| What leaves the house | [What leaves the house](/wiki/security/what-leaves-the-house) |
| What may be spent | [Spending](/wiki/controls/settings/spending#the-daily-limit) |
| What each role may do | [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions) |
| Kids never see how it works | [Kids](/wiki/model/family-and-roles#kids) |
| Where a phone is, and for how long | [Shared location](/wiki/model/location) |
| Speaking instead of typing, with the browser's own speech recognition | [General](/wiki/controls/settings/general#this-page) |

## Why it is built this way

A family is small scale: a few hundred ideas fit in one request, one database file is enough, and one program is easy to look after. Three ideas explain most of its choices.

- **The model understands; the code knows.** Code decides what can be decided (dates, checks, who may do what, what is sent and when). The model turns sentences into structured records and words the reply.
- **[Tokens](/wiki/reference/glossary#token) are the running cost.** Every model call is paid for, so replies are short, memory and retrieval run locally, what changes is kept out of the part of each request the company can reuse, every loop is bounded, and a daily spending limit is checked before every call.
- **Own the data, lose nothing.** Every message is written to disk before anything else happens. If a model company or Google is down, the message is kept, retried, and the sender told.

Developer docs: docs/DESIGN.md, "Decisions"; docs/PRODUCT_EXAMPLES.md.
