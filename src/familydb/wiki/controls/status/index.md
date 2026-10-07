# Status

Status tells a parent or an admin whether the assistant can answer, what it has cost, and what an admin has to fix. Open it first when something seems wrong. It calls no model and makes no network call, and nothing on it updates by itself, so press **Check again** to read it afresh.

Two more pages belong to it: [Models and prices](/wiki/controls/status/models-and-prices), the daily check of what each model company offers and charges, and [Recent activity](/wiki/controls/status/activity), the full history of one message or lookup, for admins.

## Who sees what

With people signed in as themselves, a kid is refused the page. A parent sees all of it except Recent activity and the buttons and links that change a setting. One button, **Look them up now**, is theirs too. An admin sees everything. Under a shared password, or none, nobody is told apart, and everyone who gets in sees everything. [Who may do what](/wiki/security#who-may-do-what) has the table.

## The pill and the verdict

The pill is the small state in the sidebar and the phone's top bar for parents and admins, and it links here. The banner at the top of Status is worked out from the same signals. The first of these that is true wins.

| Pill | When |
|---|---|
| **Can't answer yet** | A step the assistant cannot work without is not done: an admin on the family list, or a model with a key. |
| **Resting** | The daily limit is set and today's estimated spend has reached it. This lasts until midnight in the family's time zone. |
| **Can't answer** | A stopping trouble is listed under Needs a look: a company out of credit, a company refusing its key, or a day's limit row that is still listed (see below). |
| **Writing back** | A reply is being written in your own chat. |
| **Ready** | None of the above. |

The banner says "can't answer right now" for both kinds of Can't answer, "is resting until midnight" for Resting, and "is ready" otherwise. It never says Writing back, but the sidebar pill, on any page including this one, does. A line under the heading gives what was spent today, what the last 30 days cost, which parts need a look and which are not connected yet. A part "needs a look" when its row is amber or red. "Not connected" is a choice and is not counted as a fault.

**The pill goes by the list, not by whether anything is answering.** A company out of credit makes the pill read "Can't answer" even when the backup company is answering.

## Needs a look

This lists what only an admin can fix, while it lasts. Each row says since when, how often, and whether admins were told on Telegram: within a minute, and again after 12 hours at the soonest while it goes on, if **Tell admins on Telegram** is on and an admin has a Telegram id. A row leaves when the thing works again, or when seven days pass without it being seen again, which this guide calls "ages out". Three rows stop answers:

| Row | What it means | Goes away when | What to do |
|---|---|---|---|
| A company is **out of credit** | The company said the account has no credit. | The company answers a call. | Add credit with the company. |
| A company **refused its key** | The key is wrong, revoked or expired. | The company answers a call. | Paste a good key under Keys on the [AI model](/wiki/controls/settings/ai-model#keys) page. |
| The day's **spending limit was used up** | A call was refused for the limit. | A call is let through on the same day, for example after you raise the limit. | Raise the limit on [Spending](/wiki/controls/settings/spending), or ignore the row once the day has turned. |

**The limit row does not clear at midnight.** It is kept under that day's date, and only a call let through on the same day clears it. After midnight it stays listed until seven days have passed since the last refused call. Until then the pill can read "Can't answer", and the assistant's row can say something only an admin can fix is stopping it, although answers have resumed. A new day's refusal adds a second row. Admins are not told again.

The other rows, about Google Calendar, a company refusing part of a request or refusing requests, and models and prices, are listed on [Messages settings](/wiki/controls/settings/messages#when-something-needs-fixing). The model and price rows are explained on [Models and prices](/wiki/controls/status/models-and-prices#needs-a-look-rows-about-models).

## The cost figures

Every figure is **an estimate worked out from each call's size and a price table, not your bill**. Also set a spending limit with the model company. A call to a model with no known price is counted at more than any listed one.

- **Spent today** is what recorded calls have cost since midnight in the family's time zone, against the daily limit, with an upright line for a usual day. A usual day is the average over the days in the last 30 that had any calls, counted by UTC date. The limit check also counts calls still on the network, so it can stop a call slightly before this bar looks full. Admins get **Change the limit**.
- **Last 30 days** shows the cost, the usual day, and "Questions answered", which is the number of calls made for answering the family. A question that uses a tool takes more than one call.
- **Where the money went** gives calls and dollars by kind of call, and the share of what was sent that came back from the prompt cache, which costs less. A footnote says when a model with no listed price was counted high; the by-model table under Technical details marks those with an asterisk.

## How each part is doing

Every row has a tag in words, never colour alone, and an admin gets a button beside a row that needs something.

| Row | Looks wrong when | What to do |
|---|---|---|
| **The assistant** (by its name) | **Can't answer** names the needed steps not done, or says something only an admin can fix is stopping it. **Resting** says the limit is spent. | **Open setup**, or read Needs a look. See [Setup](/wiki/controls/setup). |
| **Spending** | **Near the limit** from 75% of it, **Limit reached** at 100%, **No limit** when it is 0, which means nothing stops a runaway day. | **Set a limit**, or raise it on [Spending](/wiki/controls/settings/spending). |
| **Sign-in** | **Needs a look** while everybody still shares one password or it is still the one FamilyDB started with. It is fine once an admin signs in as themselves, or when no password is set at all. | The Password step of [Setup](/wiki/controls/setup). |
| **Backup** | **Optional** when no second company with a key can answer, or the fallback is off. It only costs when used. | **Add a backup key** on the AI model page. |
| **Telegram** | **Needs a look** when a token is saved but Telegram refused it, it is still connecting, or nobody is linked. **Not connected** with no token. | The Telegram step of Setup. Reminders still appear in the chat without it. |
| **Google Calendar** | **Needs a look** when a calendar is named but its key file is missing. **Not connected**: plans stay inside FamilyDB. | The Calendar step of Setup. |
| **Looking things up** | **Off**: new ideas get no hours, prices or drive times. | **Turn it on** on [Lookups](/wiki/controls/settings/lookups). |

**Connected to** repeats the facts behind these rows: the calendar and the address it is reached as, the home position, whether lookups can run, where the weekend digest goes, and how the page is protected.

## Waiting and Worth a look

**Waiting** counts ideas by lookup state and says when they are looked up, by default together in the evening. Below that are the next five ideas due and **Messages that did not go through**: the five most recent messages that failed, with their text, the error, and either "given up on" or "N tries, will try again". The second shows until the give-up flag is set, even after the retries are used up, so compare the count with the limit set on Messages. **Parents see that text; Recent activity is admin-only.** A message stays listed until a retry answers it. Retries are set under "When a message cannot be answered" on the [Messages](/wiki/controls/settings/messages#when-a-message-cannot-be-answered) page.

**Worth a look** lists the six most recent calls in the last 30 days that ended oddly, and the six most recent lookups that gave up.

| Item | What it means | What to do |
|---|---|---|
| A call ended with **max_tokens** | The answer was cut short at the output limit. | Raise "Longest answer (tokens)" on [Spending](/wiki/controls/settings/spending#what-one-message-may-use). |
| A call ended with **refusal** | The model declined to answer. | An admin can find that time under Recent activity and open it. |
| A **lookup that failed** | The lookup gave up. The note says why. | Open the idea and press **Look it up again**. |

## When something is wrong

1. Read the pill and the banner. A pill reading "Can't answer yet" means setup is not finished; the assistant's row names the missing steps.
2. Read **Needs a look**, then any amber or red row under **How each part is doing**.
3. For one message that went wrong, an admin opens it under [Recent activity](/wiki/controls/status/activity).
4. For a message that never got a reply, check **Messages that did not go through**.

What is sent without being asked is on [Messages settings](/wiki/controls/settings/messages), not here.

Developer docs: `familydb/web/status.py` (`pill`, `health`, `verdict`, `attention`, `light`), `familydb/alerts.py` (module notes), and `docs/DESIGN.md`, "Cost".
