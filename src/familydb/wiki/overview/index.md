# The big picture

Start here to understand what FamilyDB is and how its parts fit together, before
going into the details. These pages begin at the wide view and go down: what the
product is and isn't, the shape of the software, and how a message crosses it.

## In one paragraph

FamilyDB is a private family planning assistant that lives in the family's chat
app. People tell it things (ideas for places to go, plans, things to do, facts
about the family) and ask it what to do. It keeps everything in one SQLite file on
a machine the family owns, mirrors confirmed plans to a shared Google Calendar,
and uses a model from Anthropic, OpenAI or Google to understand sentences and
word replies. The assistant is called Vera by default, and the family can rename
her.

## The shape of it

One Python process does all of it. A chat adapter (Telegram, or the web page's
chat) hands each message to a pipeline. The pipeline saves the message first,
builds a request from the family's context, the ideas list and the recent
conversation, and lets the model decide which tools to call. The tools are
ordinary, tested functions over the database. Every model call and every tool call
is logged. The web page, the scheduled jobs and the Telegram commands read and
change the same database through the same code.

The layers, from the outside in:

1. **Channels**: Telegram (text, voice notes, photos, buttons) and the web page.
2. **The pipeline**: one inbound message end to end. It stores the message, takes a lease on it so two workers never answer one, and sends the stored reply at least once.
3. **The gateway and the agent**: the one door to a model, with a limit checked before every call, and a loop that runs the tools the model asks for.
4. **Tools and engines**: small deterministic functions (ideas, plans, tasks, memory, places, wishes) and the suggestion engine, which weighs each idea against the calendar, the forecast and opening hours.
5. **The store**: SQLite, one repository per table, migrations that are only ever added.
6. **Jobs**: a scheduler for the things that happen on their own, such as reminders, lookups, the weekend digest and the daily check of models and prices.

## Three ideas that explain most of its choices

- **The model understands; the code knows.** Code decides what can be decided (dates, checks, who may do what, what is sent and when). The model turns sentences into structured records and words the reply.
- **Tokens are the running cost.** Every model call is paid for, so replies are short, memory and retrieval run locally, nothing volatile sits in the cached part of the prompt, every loop is bounded, and a daily spending limit is checked before every call.
- **Own the data, lose nothing.** Every message is written to disk before anything else happens. If a model company or Google is down, the message is kept, retried, and the sender told.

## In this section

- [What it is and isn't](/wiki/overview/what-it-is): the product, what it needs, and where it stops

**Still to come:** how it is built (one process, its parts and their threads), the layers and how a request crosses them, and the building blocks (the libraries and why each is there).

*See also: [The pieces](/wiki/model) · [What it does on its own](/wiki/behavior) · `docs/DESIGN.md`.*
