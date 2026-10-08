# Troubleshooting card

The Troubleshooting card shows what went wrong lately, sets how much the server logs, and keeps the words of every call to a model so you can read them. It is the card on the Settings page; [Troubleshooting](/wiki/operations/troubleshooting) is the guide's page of symptoms and fixes, and the card is where you look first to see what FamilyDB itself recorded. Only admins see it.

> **The models' words hold the family's own words, and any admin can read them.** That includes the family and ideas lists sent with every message and whatever a grown-up kept from the kids. A [backup](/wiki/operations/backup-and-restore) keeps what the database held.

## What the card shows

| Part | What it shows |
|---|---|
| The last day | Errors and warnings logged in the last day, calls to a model that failed in the last 7 days, and the same **Needs a look** list as [Status](/wiki/controls/status#needs-a-look). It also lists messages that did not go through (marked **Given up** when no more tries are coming) and ideas a lookup could not fill in. |
| Calls to a model that failed | The 10 newest: when, what for, which model, and what it said. Each opens that call in full. The list fills only while the models' words are kept. |
| Read what the models were sent and said | Every call to a model, newest first, 100 at a time, filtered to all or failed, or to one kind of call. Each opens in full: the instructions and tools it started from, the settings it ran with, the conversation, each step, and the reply or why it failed. A call on a message's history in [Recent activity](/wiki/controls/status/activity) links here. |
| The problem log | Warnings and errors the server logged, newest first, 100 at a time, filtered to everything kept or errors only. The same trouble again within a day is one line with a count. Each opens to show when it was first and last seen, which part of the program wrote it, and the traceback. |

The settings below it set how much is kept. A failed call always leaves a line in the problem log, even when its words are not kept. Taking a person off for good removes the kept words of calls made for their messages.

## How much is logged

Turn these up when chasing a problem and back down afterwards: more detail is more to read, and Debug writes a lot.

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| What the server writes (`log_level`) | Info | The lowest severity the server writes to its own log, which the lines below are drawn from; nothing less than this can be kept or shown. Debug also logs the program's own network traffic to Telegram and the model companies. | Debug, Info, Warnings and errors, or Errors only |
| What is kept here to read (`problem_log_level`) | Warnings and errors | The lines at least this serious are kept in the database and listed on the card for 30 days, 2000 at most. | Debug, Info and up, Warnings and errors, or Errors only |
| A different level for one part (`log_areas`) | none | One part a line, such as `models=DEBUG`, so chasing a Telegram problem needs no flood from everything else. A line the card cannot read is refused with the reason. | 2000 characters; levels DEBUG, INFO, WARNING or ERROR |

The parts are `models` (asking the models), `messages` (messages in and out), `telegram`, `jobs` (background jobs), `web` (the web page), `tools` (what the models do), `calendar` (calendar and weather) and `suggestions`. Anything else with a dot in it is taken as a program part's own name. A part's level sets what the server writes for that part. A line reaches the problem log only if it is also at least the **kept here** level.

Keys and tokens are taken out of the problem log: a model company's key, the Telegram bot token, and a key or token in a web address. The server's log is the one in [Diagnostics](/wiki/operations/diagnostics#logs).

## The models' own words

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Days the models' words are kept (`keep_ai_text_days`) | 14 | Keeps everything each model was sent and said, so an admin can read it on the card. 0 keeps none, and the card then lists no failed calls. When messages are set to be forgotten, they go with the messages' words if that is sooner, and never before 30 days. | 0 to 365 |

FamilyDB lets go of what is past its time each night at 03:30. A part longer than 20,000 characters is cut when kept. How many calls are kept, and their size, is shown on the card. The messages' own limit is on [Sign-in and security](/wiki/controls/settings/sign-in#how-long-messages-are-kept).
