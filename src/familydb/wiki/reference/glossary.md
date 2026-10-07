# Glossary

Plain-language definitions of the words this guide uses. Look a word up here; you do not need to read it top to bottom.

## The things it keeps

### Idea
A possibility: a restaurant to try, a day trip, a show, "one day we go to...". It has a kind (open text, so any new kind works), may say who it is for, and is complete as soon as it is said. See [Ideas and places](/wiki/model/ideas-and-places).

### Plan
An idea tied to an event on the shared Google Calendar: a commitment. The calendar is the second copy, and a plan is kept in line with its event. See [Plans and the calendar](/wiki/model/plans-and-calendar).

### Thing to do
An obligation with a reminder; the code calls it a task. It may have no date, may repeat, and a birthday's reminder lists the gift ideas saved for that person. See [Things to do and reminders](/wiki/model/tasks-and-reminders).

### Outcome
How a plan went: a rating from 1 to 10. An idea can have many, so a restaurant can be done five times with five ratings.

### Memory
A short fact the family told the assistant about itself, kept about the person it concerns. Each is a Must or a guess, and a parent can forget any of them. See [How memory works](/wiki/model/memory).

### Must and a guess
The two labels on a memory. A Must is a rule the assistant never suggests against (an allergy); a guess is something it noticed itself and only leans on. The stored name for a Must is *firm*.

### Lookup
Filling an idea in from the web: address, hours, tickets, travel time. By default lookups wait for the evening and arrive together. See [Lookups](/wiki/controls/settings/lookups).

### Present
An idea of kind gift (any way of saying present is saved as gift). It is kept from every kid and from the grown-up it names, unless an admin chose others. See [Presents](/wiki/model/ideas-and-places#presents).

### Weekend ideas
The message with the weekend's options, posted to a chat on a day and hour you choose. Settings and logs call it the weekend digest. See [Weekend ideas](/wiki/controls/settings/messages#weekend-ideas).

## The people

### Admin, parent, kid
The three roles. An admin may do everything, a parent may do everything except settings, setup and the family list, and a kid may chat and keep their own wishes and things to do, within limits. See [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions).

### Family list
Who the assistant talks to and who signs in. An admin changes it on the Family page or with `familydb members` on the server, never the model. See [Who may message the bot](/wiki/model/family-and-roles#who-may-message-the-bot).

### Starting password
A made-up password an admin gives a person, shown once. The person can reach only the page where they choose their own until they have. See [Passwords](/wiki/controls/family#passwords).

### Shared password
The one password the family uses until an admin has their own; the installer prints it, and `.env` keeps it as `WEB_PASSWORD`. Once any admin has an own password it ends for good, unless you restore an older backup. See [The shared password](/wiki/security/passwords-and-sessions#the-shared-password).

### Vera
The default name of the assistant. Vera is the persona: the name, the character and the wording of everything said unasked, which the family can rename and rewrite. See [Vera](/wiki/model/vera).

### Persona
The name, character and wording the assistant speaks with. Vera is the default; see the entry Vera.

### Knock
What a stranger leaves by messaging the assistant: it replies with their id, and an admin can use the saved knock to let them in. See [Link a Telegram](/wiki/controls/family#link-a-telegram).

## How it works

### Model company
Anthropic, OpenAI or Google, the business whose model answers. The setting that picks one is called `provider`. See [Model companies](/wiki/boundaries/model-companies).

### Level
Everyday, better or best: a company's lineup by strength. Everyday is its cheapest model unless the family chooses another. See [How strong a model answers](/wiki/controls/settings/ai-model#how-strong-a-model-answers).

### Turn
One message in, the assistant's thinking and any tools it calls, and one reply out. See [From message to reply](/wiki/behavior/message-to-reply).

### Token
The small piece of text a model company charges by, about three quarters of a word. See [Cost](/wiki/operations/cost).

### Gateway
The one door to a model, so the daily limit is checked and every call is recorded the same way. See [The layers](/wiki/overview/how-its-built#the-layers).

### Worker turn
A small separate turn that may use the web (a lookup, or a search for what is on), with its own prompt and a cap on searches. The chat model never gets the web; see Turn above.

### Spending limit
The most a day's model calls may be estimated to cost (US$2 unless changed; 0 for no limit), checked before every call. It is an estimate, not the bill. See [The daily limit](/wiki/controls/settings/spending#the-daily-limit).

### Prompt cache
A company's discount for a request that starts the same way as the last one. FamilyDB keeps what changes (dates, the sender, a location) out of the front of a request so the discount applies. See [What the cache does](/wiki/operations/cost#what-the-cache-does).

### Lease
A claim on a message that runs out if the program stops, so nothing is answered twice. It is renewed while a turn runs. See [From message to reply](/wiki/behavior/message-to-reply).

### Failed and given up
A failed message will be tried again by the retry job. A given-up message has no more tries. See [When a message cannot be answered](/wiki/controls/settings/messages#when-a-message-cannot-be-answered).

### Needs a look
A trouble only an admin can fix, shown on Status and sent on Telegram to an admin who has a Telegram id. See [Status](/wiki/controls/status#needs-a-look).

### Nudge
An unprompted note about a thing to do kept for a part of the week, sent when that part comes round and the calendar is free. See [Preferred windows and nudges](/wiki/model/tasks-and-reminders#preferred-windows-and-nudges).

### Pill
The health word at the top of every page for parents and admins: Ready, Writing back, Resting or Can't answer. See [The pill and the verdict](/wiki/controls/status#the-pill-and-the-verdict).

### Catch-up
The run after a restart that does the follow-ups, evening-before checks and weekend ideas whose hour has already passed. See [After a restart](/wiki/behavior/jobs#after-a-restart).

## Server words

### SQLite
The database: one file on disk, with two companion files (`-wal` and `-shm`) beside it while it runs. Use a backup, not a hand copy. See [State and the database](/wiki/model/state-and-database).

### Migration
A numbered change to the database layout, applied once, in order, on start or upgrade. Migrations only go forward. See [Migrations](/wiki/model/state-and-database#migrations).

### Hash
A one-way scramble of a password. The server can check a typed password against it but cannot read it back. See [Passwords and sessions](/wiki/security/passwords-and-sessions).

### Safety backup
A backup FamilyDB takes by itself before a restore or an upgrade, so either can be undone. See [Backup and restore](/wiki/operations/backup-and-restore).

### Service account
A Google account for a program rather than a person. The family shares the calendar with it, so FamilyDB holds nobody's sign-in. See [Google Calendar](/wiki/boundaries/google-calendar).

### Deploy key
A read-only SSH key that lets the server fetch FamilyDB's code from its repository. See [Install and first run](/wiki/operations/install).

### Caddy
The reverse proxy that serves the web page over HTTPS; the page itself listens only on the machine. See [HTTPS and the firewall](/wiki/operations/https-and-firewall).

### Crontab
The server's list of timed commands. The nightly backup is one line in it. See [The nightly backup](/wiki/operations/backup-and-restore#the-nightly-backup).

### systemd
The part of the server that starts FamilyDB at boot and restarts it if it stops. See [The server](/wiki/operations/host#the-service).

### Journal
The server's log, where FamilyDB writes under systemd. See [Logs](/wiki/operations/diagnostics#logs).

### Detached commit
A git checkout of one version rather than a branch. A rollback leaves the install on one, which is expected. See [If it goes wrong](/wiki/operations/upgrade-and-rollback#if-it-goes-wrong).
