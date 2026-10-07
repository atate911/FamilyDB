# Glossary

Plain-language definitions of the words this guide uses. You don't need to read it
top to bottom; it is a place to look things up.

## The things it keeps

### Idea
A possibility: a restaurant to try, a day trip, a show, "one day we go to…". It has a
*kind* (open text, so any new kind works), may say who it is for, and is complete as
soon as it is said. Its status moves through idea, planned, done and dropped.

### Plan
An idea tied to an event on the shared Google Calendar: a commitment. The calendar
is the second copy, and a plan is kept in line with its event.

### Thing to do
An obligation with a reminder (the code calls it a *task*). It may have no date, may
repeat, and a birthday's reminder lists the gift ideas saved for that person.

### Outcome
How a plan went: a rating from 1 to 10. An idea can have many, so a
restaurant can be done five times with five ratings.

### Memory
A short fact the family told the bot about itself, about the person it concerns. A
*firm* one is always weighed; a guess only leans. A parent can forget any of them.

### Lookup
Filling an idea in from the web: address, hours, tickets, travel time. It runs as a
bounded *worker turn* rather than in the chat. By default lookups wait for the
evening and arrive together.

## The people

### Admin, parent, kid
The three roles. A parent can chat, change ideas, plans and things to do, browse the
household's pages and answer the kids' wishes. An admin can do all that and also
change settings, set up and manage the family list. A kid can sign in, chat within a
daily number, keep her own wish lists and tick off her own things to do.

### Family list
Who the bot talks to and who signs in. It is changed only on the Family page or the
command line, never by the model.

### Starting password
A password an admin makes up for somebody, shown once. That person can go nowhere
but the page to choose their own until they have.

### Shared password
The password the whole family uses until an admin has one of their own. The first
admin's own password ends it for good.

### Vera
The default name of the assistant. She is the *persona*: a name, a character and
the wording of everything said unprompted, which the family can rename and rewrite.

## How it works

### Provider (model company)
Anthropic, OpenAI or Google. Each sits behind one protocol, so nothing else in the
code knows which is in use.

### Level
Everyday, better or best: a company's lineup by strength. Everyday is its cheapest
model unless the family chooses another; a stronger level is used only where it is
chosen.

### Gateway
The one door to a model. Every call goes through it, so the daily spending limit is
checked and every call is recorded in the same way.

### Worker turn
A small separate model turn that may use the web (a lookup, or a search for what is
on). Its own prompt, a subset of the tools, and a cap on searches. The chat model
never gets the web.

### Spending limit
The most a day's model calls may be estimated to cost ($2 unless changed; 0 for no
limit), checked before every call. It is an estimate from each call's size and the
price table, not the bill.

### Prompt cache
The company's saving for a request that starts the same way as the last one. It is
why nothing that changes (dates, the sender, a location) is put in the front of a
request: it would make the saving miss.

### Lease
An expiring claim on a message, renewed while a turn runs. It means a restart strands
nothing and two workers never answer one message.

### Setup
The page's step-by-step walk through a new install: you, your password, an AI model,
home, Telegram, the family and the calendar. Progress is read from what is configured
and never stored.

*See also: [Map to the developer docs](/wiki/reference/dev-docs) ·
[The pieces](/wiki/model).*
