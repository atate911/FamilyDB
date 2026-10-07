# Status

Status tells a parent or an admin whether the assistant can answer, what it has cost, and what an admin has to fix. Open it first when something seems wrong. It reads the database and the settings only: **no model is called to draw it**, and nothing on it updates by itself, so press **Check again** to read it afresh.

A kid is refused the page. A parent sees everything on it. An admin also gets the buttons that change a setting, the links to the Settings pages, and Recent activity, which holds the family's own words. [Who may do what](/wiki/security#who-may-do-what) has the full table.

## What is on the page, top to bottom

1. **The verdict**, a banner saying whether the assistant is ready.
2. **Needs a look**, only while something only an admin can fix is going on.
3. **Spent today** and **Last 30 days**, the cost figures.
4. **How each part is doing**, one row for each part, each with a tag in words.
5. **Connected to** and **Where the money went**.
6. **Recent activity**, for admins.
7. **Waiting** and **Worth a look**.
8. **Models and prices**, what the daily check found.
9. **Technical details**, folded away: which model answers each job, the keys, and token tables.

## The pill and the verdict

The pill is the small state in the sidebar and the phone's top bar for parents and admins, and it links here. The verdict and the first row of the page are worked out from the same signals, so they cannot disagree. The first of these that is true wins.

| Pill | Banner heading | When |
|---|---|---|
| **Can't answer yet** | "can't answer right now" | A step the assistant cannot work without is not done: an admin on the family list, or a model with a key. |
| **Resting** | "is resting until midnight" | The daily limit is set and today's estimated spend has reached it. Midnight is the family's time zone. |
| **Can't answer** | "can't answer right now" | A trouble that stops answers is listed under Needs a look: a company out of credit, a company refusing its key, or the day's limit used up. |
| **Writing back** | not shown here | A reply is being written in your own chat. Status itself never shows this. |
| **Ready** | "is ready" | None of the above. |

The banner adds one line: what was spent today, what the last 30 days cost, which parts need a look, and which are not connected yet. A part "needs a look" when its row is amber or red. "Not connected" is a choice and is not counted as a fault.

**The pill goes by the list, not by whether anything is still answering.** A company out of credit makes the pill read "Can't answer" even when the backup company is answering. The row clears when the first company answers again.

## Needs a look

This lists what only an admin can fix, for as long as it lasts. A row appears when the trouble is seen. It leaves when the thing works again, or when seven days pass without it being seen again, which the table calls "ages out". Each row says since when, how often, and whether admins were told on Telegram. Admins are told within a minute, and again after 12 hours at the soonest while the trouble goes on, if **Tell admins on Telegram** is on ([Messages settings](/wiki/controls/settings/messages#when-something-needs-fixing)) and at least one admin has a Telegram id. Otherwise this page is the only place it shows.

| Row | What it means | Goes away when | What to do |
|---|---|---|---|
| A company is **out of credit** | The company said the account has no credit. Stops answers. | The company answers a call. | Add credit with the company. |
| A company **refused its key** | The key is wrong, revoked or expired. Stops answers. | The company answers a call. | Paste a good key under Keys on the [AI model](/wiki/controls/settings/ai-model#keys) page. |
| The day's **spending limit was used up** | A call was refused for the limit. Stops answers. | A call is let through on the same day, for example after you raise the limit. Otherwise it ages out. | Raise the limit on the [Spending](/wiki/controls/settings/spending) page, or wait until midnight. |
| **Google Calendar stopped letting the bot in** | Google refused the service account. | Google answers a call. | Check the calendar is still shared with the service account and its key was not deleted, then connect again on [Connections](/wiki/controls/settings/connections#google-calendar). |
| A **model in use is going, or has gone** | The company says it has no model of that name, or the daily check no longer finds it offered to your key, or the price lists give it an end date within 60 days. | That model answers a call, or the next daily check lists it again. A retirement notice is news and is not cleared by a check. | Choose another model on the AI model page. If a box names the model and a replacement is on offer, the row has a **Use [model] instead** button for an admin, which saves it. |
| The **price of a model in use changed** | The daily check read a new price. News only. | Not cleared; it ages out. | Nothing, unless the new price is more than you want to spend. |
| **The price lists need a look** | A price list could not be read for three days running, or the two lists disagree about a model in use (the old price is kept). | A list is read again. A disagreement ages out. | Wait a day. If it goes on, the row says which list. |
| A company **stopped taking part of a request** | A company refused a part of the request. It is now left out and the rest works, without something it had. | Not cleared; it ages out. | Upgrade FamilyDB: a newer version may know what takes its place. |
| A company **is refusing requests** | A refusal FamilyDB cannot read, seen twice with no answer between. Admins are told at the second. | The company answers a call. | Read the row's detail. With judgments on, a stronger model is asked about it at once. |
| **What the calls cost or do moved** | The last seven days of one kind of call, set beside the four weeks before, moved a long way: dearer per answer, more tokens, more calls an answer, twice as slow, or more ending badly. News only. | Not cleared; it ages out. | Open Recent activity to see what changed. |

New models and judgments are not listed here: they are under Models and prices.

## The cost figures

Every figure is **an estimate worked out from each call's size and a price table, not your bill**. Also set a spending limit with the model company. A call to a model with no known price is counted at more than any listed one, and marked with an asterisk in the tables.

- **Spent today** is what recorded calls have cost since midnight in the family's time zone, against the daily limit, with an upright line for a usual day. A usual day is the average over the days in the last 30 that had any calls. Admins get **Change the limit**. The limit check also counts calls still on the network, so it can stop a call slightly before this bar looks full.
- **Last 30 days** shows the cost, the usual day, and "Questions answered", which is the number of calls made for answering the family. A question that uses a tool takes more than one call.
- **Where the money went** is a table of calls and dollars by kind of call, and the share of what was sent that came back from the prompt cache, which costs less. The kinds are answering the family, the weekend digest, answering a message again after a failure, looking ideas up, searching for what is on, weighing a change in the models, checking a disputed price, listening to voice notes and reading photos.
- **Technical details** adds, for each kind, where its input went (instructions, family, ideas, tools, history, message), and a table by model of calls, tokens sent, cached, written and sent back, and dollars.

## How each part is doing

Every row has a tag in words, never colour alone. The states are Working, Needs a look, Can't answer, Not connected (a choice, not a fault) and Off or Optional. An admin sees a button beside a row that needs something.

| Row | What it means | When it looks wrong | What to do |
|---|---|---|---|
| **The assistant** (by its name) | The pill, said once more. | **Can't answer** with "it still needs..." names the needed steps not done. With no steps missing, it says something only an admin can fix is stopping it. **Resting** says the limit is spent. | Press **Open setup**, or read Needs a look. See [Setup](/wiki/controls/setup). |
| **Spending** | **Working** under 75% of the limit. **Near the limit** from 75%. **Limit reached** at 100%. **No limit** when the limit is 0. | No limit means nothing stops a runaway day. | **Set a limit**, or raise it on [Spending](/wiki/controls/settings/spending). |
| **Sign-in** | Working when an admin signs in as themselves, or when no password is set at all, in which case anyone who can reach the page is in. | **Needs a look** when everybody still shares one password, or it is still the one FamilyDB started with. | **Set up sign-ins**: the Password step of [Setup](/wiki/controls/setup). |
| **Backup** | **Ready** when a second company with a key can answer if the first cannot. | **Optional** when there is none, or the fallback is switched off. It only costs when used. | **Add a backup key** on the AI model page. |
| **Telegram** | **Working** when the bot's token works and at least one person on the list has their Telegram linked. | **Needs a look** when a token is saved but Telegram refused it, is still connecting, or nobody is linked. **Not connected** with no token. | Open the Telegram step of Setup. Without Telegram, reminders still appear in the chat. |
| **Google Calendar** | **Connected** when a calendar id is saved and its key file exists. | **Needs a look** when a calendar is named but the key file is missing. **Not connected**: plans stay inside FamilyDB. | Open the Calendar step of Setup. |
| **Looking things up** | **On** when web lookups are switched on. | **Off**: new ideas get no hours, prices or drive times. | **Turn it on** on [Lookups](/wiki/controls/settings/lookups). |

**Connected to** repeats the facts behind these rows: the calendar and the address it is reached as, the home position, whether lookups can run, where the weekend digest goes, and how the page is protected, with a note when it is reachable from other machines.

## Waiting and Worth a look

**Waiting** counts ideas by lookup state: waiting to be looked up, looked up, the lookup failed, nothing to look up. It says when they are looked up, by default together in the evening. Anybody who may change things sees **Look them up now** while lookups are on and ideas are waiting. Below the counts are the next five ideas due, and **Messages that did not go through**: the five most recent messages that failed, with the error and either "will try again" or "given up on". A message stays listed until a retry answers it. Retries are set under "When a message cannot be answered" on the [Messages](/wiki/controls/settings/messages#when-a-message-cannot-be-answered) page.

**Worth a look** lists, over the last 30 days, up to six calls that ended oddly, and up to six lookups that failed.

| Item | What it means | What to do |
|---|---|---|
| A call ended with **max_tokens** | The answer was cut short at the output limit. | Raise "Longest answer, in tokens" on [Spending](/wiki/controls/settings/spending#what-one-message-may-use). |
| A call ended with **refusal** | The model declined to answer. | Open the message's history (below) to see what it was asked. |
| A **lookup that failed** | The lookup gave up. The note says why. | Open the idea and press **Look it up again**. |

## Recent activity

This is for admins only, because it holds the words of every chat. It lists the last 25 things the models were asked in the last 7 days, newest first: a message and who sent it, the weekend ideas, or a lookup. Each line shows when, what for, how many calls, how many tokens, searches and the estimated cost. A line opens that item's history at `/status/activity/<key>`. For an admin, an idea's page links to how it was looked up in the same way.

A history page has, top to bottom:

- **What was asked**, and the reply that was kept for it, or the reason none was.
- **Model calls**: a table with when, what for, the model and its company, how the call ended, tokens sent, cached, written and sent back, searches, estimated dollars and milliseconds. "Sent" is what was not in the cache.
- **Tools used**: each tool call, folded, with what it was given and what it answered. A failed one is tagged. Long text is cut at 4000 characters; the log keeps it whole.
- **What the lookup found**, for a lookup: the place saved or the reason nothing was, and the pages it read.

## Models and prices

This is the daily check's report. It runs at 05:17 family time, calls no model, and sends nothing about the family. It asks each company with a key which models the key may use, and reads two public price lists, LiteLLM's and OpenRouter's. It takes a price when the two lists are within 5% of each other.

- **Top rows** show each source: when it was read and how many models, or why it could not be.
- **Changed in the last 30 days** is a table of when, company, model and what: new, no longer offered to the key, offered again, a price moved, or a retirement date.
- **Judgments**, when a stronger model has weighed a change, lists each question with its answer, outcome and reason. These need **Ask a stronger model when a change needs judgement** on ([AI model settings](/wiki/controls/settings/ai-model#asking-a-stronger-model-to-weigh-a-change)); it is off by default.

An admin gets two buttons on a judgment, each saving the settings it names:

| Button | Shown when | What it does |
|---|---|---|
| **Put these in** | A model was suggested and is not in force yet. | Saves the suggested models. Under "within cost", a model more than about 10% dearer than the one it replaces waits for this press; under "suggest", every one does. |
| **Put back** | A judgment put a model in and it is still in force. | Restores what was there before. |

With the check switched off, the page says prices are the ones this version was released with and nobody is told when a model goes. Before its first run it says nothing has been read yet. A model in use that is gone is answered by the nearest model costing no more than twice as much until you choose another.

## When something is wrong

1. Read the banner heading. "Can't answer yet" means setup is not finished.
2. Read **Needs a look**. Each row says what to do, and the table above says when it clears.
3. Read **How each part is doing** for anything amber or red.
4. For one message that went wrong, find it under Recent activity and open it.
5. For a message that never got a reply, check **Messages that did not go through**.

What is sent without being asked, with its cost and when it last went, is on the [Messages settings](/wiki/controls/settings/messages) page, not here.

Developer docs: `src/familydb/web/status.py` (`pill`, `health`, `verdict`, `attention`, `light`), `web/activity.py`, `familydb/alerts.py`, `familydb/model_watch.py` and `familydb/judgement.py` (module notes), and `docs/DESIGN.md`, "Keeping up with models and prices" and "Judgment on changes in the models".
