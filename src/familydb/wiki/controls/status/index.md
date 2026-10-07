# Status

Status tells a parent or an admin whether the assistant can answer, what it has cost, and what an admin has to fix. Open it first when something seems wrong. It calls no model and makes no network call, and nothing on it updates by itself, so press **Check again** to read it afresh.

Two more pages belong to it: [Models and prices](/wiki/controls/status/models-and-prices), the daily check of what each model company offers and charges, and [Recent activity](/wiki/controls/status/activity), the full history of one message or lookup, for admins.

## Who sees what

With people signed in as themselves, a kid is refused the page. A parent sees all of it except Recent activity and the buttons and links that change a setting; the **Look them up now** button is theirs too. An admin sees everything. Under a shared password, or none, nobody is told apart and everyone who gets in sees everything. The table is in [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions).

## The pill and the verdict

The pill is the small state in the sidebar and the phone's top bar for parents and admins, and it links here. The banner at the top of Status is worked out from the same signals. The first row that is true wins.

| Pill | When |
|---|---|
| **Can't answer yet** | A step the assistant cannot work without is not done: an admin on the family list, or a model with a key. |
| **Resting** | The daily limit is set and today's estimated spend has reached it. It lasts until midnight in the family's time zone. |
| **Can't answer** | A stopping trouble is listed under Needs a look: a model company out of credit, a model company refusing its key, or a day's limit row still listed. |
| **Writing back** | A reply is being written in your own chat. |
| **Ready** | None of the above. |

The banner says "can't answer right now" for both kinds of Can't answer, "is resting until midnight" for Resting, and "is ready" otherwise; it never says Writing back. A line under it gives what was spent today, what the last 30 days cost, which parts need a look and which are not connected yet. Not connected is a choice, not a fault.

The pill goes by the Needs a look list, not by whether anything is answering: a model company out of credit makes the pill read Can't answer even while the second company is answering. The day's limit row stays listed after midnight, so the pill can keep reading Can't answer ([known limits](/wiki/reference/known-limits#the-days-limit-keeps-the-pill-red-after-midnight)).

## Needs a look

This lists what only an admin can fix, while it lasts. Each row says since when, how often, and whether admins were told on Telegram. If **Tell admins on Telegram** is on and an admin has a Telegram id, FamilyDB tells them within a minute, and again after 12 hours at the soonest while the trouble goes on. A row leaves when the thing works again, or after seven days without being seen again. Three rows stop answers:

| Row | It means | Goes away when | Do this |
|---|---|---|---|
| A company is **out of credit** | The model company said the account has no credit. | The company answers a call. | Add credit with the company. |
| A company **refused its key** | The key is wrong, revoked or expired. | The company answers a call. | Paste a good key under [Keys](/wiki/controls/settings/ai-model#keys). |
| The day's **spending limit was used up** | A call was refused for the limit. | A call is let through on the same day, for example after you raise the limit. | Raise the limit on [Spending](/wiki/controls/settings/spending#the-daily-limit). |

The other rows (Google Calendar, a model company refusing part of a request or refusing requests, models and prices) are listed with what each means on [Messages](/wiki/controls/settings/messages#when-something-needs-fixing). The model and price rows are explained on [Models and prices](/wiki/controls/status/models-and-prices#needs-a-look-rows-about-models).

## The cost figures

Every figure is **an estimate worked out from each call's size and a price table, not your bill.** Set a spending limit with the model company as well. How the estimate is made, and what to turn down, is on [Cost](/wiki/operations/cost).

- **Spent today** is what recorded calls have cost since midnight in the family's time zone, against the daily limit, with a line for a usual day. Admins get **Change the limit**.
- **Last 30 days** shows the cost, the usual day (the average over the days in those 30 that had any calls) and "Questions answered".
- **Where the money went** gives calls and dollars by kind of call, and how much of what was sent came back from the [prompt cache](/wiki/reference/glossary#prompt-cache), which costs less.

## How each part is doing

Every row has a tag in words, never color alone, and an admin gets a button beside a row that needs something.

| Row | Looks wrong when | Do this |
|---|---|---|
| **The assistant** (by its name) | **Can't answer** names the needed steps not done, or says something only an admin can fix is stopping it. **Resting** says the limit is spent. | **Open setup**, or read Needs a look. See [Setup](/wiki/controls/setup). |
| **Spending** | **Near the limit** from 75% of it, **Limit reached** at 100%, **No limit** when it is 0, which means nothing stops a runaway day. | **Set a limit**, or raise it on [Spending](/wiki/controls/settings/spending). |
| **Sign-in** | **Needs a look** while everybody still shares one password or it is still the one FamilyDB started with. It is fine once an admin signs in as themselves, or when no password is set at all. | The Password step of [Setup](/wiki/controls/setup). |
| **Backup** | **Optional** when no second company with a key can answer. It costs money only when used. | **Add a backup key** on [AI model](/wiki/controls/settings/ai-model#a-second-company). |
| **Telegram** | **Needs a look** when a token is saved but Telegram refused it, it is still connecting, or nobody is linked. **Not connected** with no token. | The Telegram step of Setup. Reminders still appear in the chat without it. |
| **Google Calendar** | **Needs a look** when a calendar is named but its key file is missing. **Not connected**: plans stay inside FamilyDB. | The Calendar step of Setup. |
| **Looking things up** | **Off**: new ideas get no hours, prices or drive times. | **Turn it on** on [Lookups](/wiki/controls/settings/lookups). |

The **Backup** row (the second company, not your database backup) is what [A second company](/wiki/controls/settings/ai-model#a-second-company) sets up. **Connected to** repeats the facts behind these rows: the calendar and its address, the home position, whether lookups can run, where the weekend ideas go, and how the web page is protected.

## Waiting and Worth a look

**Waiting** counts ideas by lookup state and says when they are looked up, by default together in the evening. Below that are the next five ideas due and **Messages that did not go through**: the five most recent messages that failed, with their text, the error, and either "given up on" or "N tries, will try again". A message stays listed until a retry answers it. Parents see that text, from any chat; Recent activity is admin-only. Status can say "will try again" after the last try ([known limits](/wiki/reference/known-limits#status-says-will-try-again-after-the-last-try)); the retry numbers are on [Messages](/wiki/controls/settings/messages#when-a-message-cannot-be-answered).

**Worth a look** lists the six most recent calls in the last 30 days that ended oddly, and the six most recent lookups that failed.

| Item | It means | Do this |
|---|---|---|
| A call ended with **max_tokens** | The answer was cut short at the output limit. | Raise **Longest answer (tokens)** on [Spending](/wiki/controls/settings/spending#what-one-message-may-use). |
| A call ended with **refusal** | The model declined to answer. | Find that time under Recent activity and open it. |
| A **lookup that failed** | The lookup was given up on. The note says why. | Open the idea and press **Look it up again**. |

## When something is wrong

Read the pill and the banner, then **Needs a look**, then any amber or red row under **How each part is doing**. For one message that went wrong, open it under Recent activity. For a message that never got a reply, see [Troubleshooting](/wiki/operations/troubleshooting#a-message-got-no-reply). What FamilyDB sends without being asked is listed on [Messages](/wiki/controls/settings/messages), not here.
